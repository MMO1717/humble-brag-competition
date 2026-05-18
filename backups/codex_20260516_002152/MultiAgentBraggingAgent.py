"""
MultiAgentBraggingAgent.py
Lightweight multi-agent pipeline: Generator -> Validator -> Critic/Rewriter.
Reuses BraggingResponseAgent as the generator; adds rule-based validation
and a single LLM rewrite pass for rows that fail validation.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict
from typing import Any, Optional

from openai import AsyncOpenAI
from dotenv import load_dotenv

from .BraggingResponseAgent import (
    BraggingResponseAgent, AgentInput, AgentOutput,
    _extract_json, _validate_output,
)
from .official_validator import validate_official_row, auto_fix, ValidationResult

load_dotenv()

logger = logging.getLogger(__name__)

# ── Critic/Rewriter prompt ──────────────────────────────────────────────────

REWRITER_SYSTEM_PROMPT = """\
You are a precise JSON editor for a bragging-response system.
You will receive:
1. The original input context.
2. A JSON draft that has specific issues.
3. A list of issues to fix.

Your job: output a CORRECTED JSON with exactly these 7 keys and nothing else:
  episode_id, bragging_mechanism, speaker_intention, desired_feedback,
  risk_assessment, response_strategy, response_text

Rules:
- Keep episode_id unchanged.
- Only change fields that need fixing.
- All text fields must be in English.
- response_text must be SHORT (15-30 words).
- bragging_mechanism must be one of: humble_complaint, faux_modesty, achievement_drop, comparison_superiority, scarcity_flex, understated_flex, self_aware_brag, other
- response_strategy must be one of: validate, light_acknowledgment, ask_followup, humor_tease, redirect, neutral_observation, set_boundary, no_response
- risk_assessment must contain at least one official risk label keyword: sycophancy, preachiness, misrecognition, strategy_inconsistency, context_insensitivity, over_coldness
- Do NOT use overpraise words (amazing, incredible, legendary, genius, perfect, iconic, unbelievable) in light_acknowledgment or set_boundary responses.
- Output ONLY the JSON object, no explanation."""


def _build_rewriter_user_prompt(
    inp: AgentInput,
    draft: dict,
    issues: list[dict],
) -> str:
    issue_lines = "\n".join(
        f"- [{i['severity']}] {i['code']}: {i['message']} → {i['suggestion']}"
        for i in issues
    )
    return f"""Original input:
  platform: {inp.platform}
  relationship: {inp.relationship}
  agent_role: {inp.agent_role}
  interaction_goal: {inp.interaction_goal}
  statement: {inp.speaker_post}

Current draft JSON:
{json.dumps(draft, ensure_ascii=False, indent=2)}

Issues to fix:
{issue_lines}

Output the corrected JSON:"""


# ── MultiAgentBraggingAgent ─────────────────────────────────────────────────

class MultiAgentBraggingAgent:
    """
    Pipeline: Generator -> Validator -> (optional) Critic/Rewriter -> Final Validator.
    Max 1 rewrite attempt. Falls back to auto_fix if rewrite fails.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.generator = BraggingResponseAgent(
            api_key=api_key, base_url=base_url, model=model,
        )
        self.model = self.generator.model

        api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        base_url = base_url or os.getenv(
            "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # Stats
        self.stats = {
            "total": 0,
            "generator_ok": 0,
            "rewrite_triggered": 0,
            "rewrite_success": 0,
            "rewrite_failed": 0,
            "autofix_used": 0,
            "issue_codes": {},  # code -> count
        }

    async def arun(self, inp: AgentInput) -> tuple[AgentOutput, dict]:
        """
        Run the full pipeline. Returns (output, metadata).
        metadata includes: generator_result, validation, rewrite_attempted, etc.
        """
        self.stats["total"] += 1
        meta: dict[str, Any] = {"episode_id": inp.episode_id}

        # Step 1: Generator
        try:
            gen_out = await self.generator.arun(inp)
            gen_dict = asdict(gen_out)
            meta["generator_status"] = "ok"
        except Exception as e:
            logger.error(f"[{inp.episode_id}] Generator failed: {e}")
            meta["generator_status"] = "error"
            meta["generator_error"] = str(e)
            raise

        # Step 2: Validate
        validation = validate_official_row(gen_dict)
        meta["validation"] = validation.to_dict()

        if validation.valid:
            self.stats["generator_ok"] += 1
            meta["rewrite_attempted"] = False
            return gen_out, meta

        # Step 3: Record issues
        for issue in validation.issues:
            self.stats["issue_codes"][issue.code] = (
                self.stats["issue_codes"].get(issue.code, 0) + 1
            )

        # Step 4: Attempt rewrite via LLM
        self.stats["rewrite_triggered"] += 1
        meta["rewrite_attempted"] = True

        try:
            rewriter_input = _build_rewriter_user_prompt(
                inp, gen_dict, validation.to_dict()["issues"]
            )
            response = await self._async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": REWRITER_SYSTEM_PROMPT},
                    {"role": "user", "content": rewriter_input},
                ],
                temperature=0.3,
                max_tokens=384,
            )
            raw = response.choices[0].message.content or ""
            fixed_data = _extract_json(raw)
            _validate_output(fixed_data)

            # Re-validate
            fixed_validation = validate_official_row(fixed_data)
            meta["rewrite_validation"] = fixed_validation.to_dict()

            if fixed_validation.valid:
                self.stats["rewrite_success"] += 1
                out = AgentOutput(
                    episode_id=inp.episode_id,
                    bragging_mechanism=fixed_data["bragging_mechanism"],
                    speaker_intention=fixed_data["speaker_intention"],
                    desired_feedback=fixed_data["desired_feedback"],
                    risk_assessment=fixed_data["risk_assessment"],
                    response_strategy=fixed_data["response_strategy"],
                    response_text=fixed_data["response_text"],
                )
                meta["rewrite_status"] = "success"
                return out, meta
            else:
                meta["rewrite_status"] = "still_invalid"
                logger.warning(
                    f"[{inp.episode_id}] Rewrite still has issues: "
                    f"{[i.code for i in fixed_validation.issues]}"
                )
        except Exception as e:
            meta["rewrite_status"] = "error"
            meta["rewrite_error"] = str(e)
            logger.warning(f"[{inp.episode_id}] Rewrite failed: {e}")

        # Step 5: Fallback to auto_fix
        self.stats["rewrite_failed"] += 1
        self.stats["autofix_used"] += 1
        fixed_dict = auto_fix(gen_dict)
        # Re-validate after autofix
        autofix_validation = validate_official_row(fixed_dict)
        meta["autofix_validation"] = autofix_validation.to_dict()
        meta["fallback"] = "auto_fix"

        out = AgentOutput(
            episode_id=inp.episode_id,
            bragging_mechanism=fixed_dict.get("bragging_mechanism", gen_dict["bragging_mechanism"]),
            speaker_intention=fixed_dict.get("speaker_intention", gen_dict["speaker_intention"]),
            desired_feedback=fixed_dict.get("desired_feedback", gen_dict["desired_feedback"]),
            risk_assessment=fixed_dict.get("risk_assessment", gen_dict["risk_assessment"]),
            response_strategy=fixed_dict.get("response_strategy", gen_dict["response_strategy"]),
            response_text=fixed_dict.get("response_text", gen_dict["response_text"]),
        )
        return out, meta
