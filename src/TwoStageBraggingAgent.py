"""
TwoStageBraggingAgent.py
Two-stage pipeline: Understander -> Responder.
Stage 1: Understand the bragging mechanism, speaker intent, desired feedback, and risk.
Stage 2: Given understanding + context, select strategy and generate response.
Falls back to BraggingResponseAgent if two-stage pipeline fails.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import Any, Optional

from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

from .BraggingResponseAgent import (
    BraggingResponseAgent, AgentInput, AgentOutput,
    _extract_json,
)
from .official_validator import (
    validate_official_row, auto_fix,
    ALLOWED_MECHANISMS, ALLOWED_STRATEGIES, RISK_KEYWORDS,
)

load_dotenv()

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class UnderstandingOutput:
    bragging_mechanism: str
    speaker_intention: str
    desired_feedback: str
    risk_assessment: str


@dataclass
class ResponsePlanOutput:
    response_strategy: str
    response_text: str


# ── Understander prompt ──────────────────────────────────────────────────────

UNDERSTANDER_SYSTEM_PROMPT = """\
You are an expert at analyzing social media posts with bragging undertones.
Your job: understand HOW the speaker is bragging and WHAT they want.

Output ONLY a JSON with exactly 4 keys:
  bragging_mechanism, speaker_intention, desired_feedback, risk_assessment

Rules:
- bragging_mechanism must be exactly one of these 8 identifiers (lowercase):
  humble_complaint, faux_modesty, achievement_drop, comparison_superiority,
  scarcity_flex, understated_flex, self_aware_brag, other
- speaker_intention: one English sentence explaining what the speaker is really trying to show off.
- desired_feedback: what kind of response the speaker hopes for, in English.
- risk_assessment: describe the main risk. MUST include at least one official risk label keyword:
  misrecognition, context_insensitivity, sycophancy, preachiness, over_coldness, strategy_inconsistency
- All text fields MUST be in English.
- Keep each text field under 80 words.

Mechanism guide:
- humble_complaint: surface complaint about something GOOD (e.g., "Ugh, Paris AGAIN for work")
- faux_modesty: self-deprecation masking achievement (e.g., "I'm so bad, only got 98%")
- achievement_drop: directly stating a concrete result (e.g., "Got promoted today")
- comparison_superiority: positioning self as better than others (e.g., "Unlike most people...")
- scarcity_flex: flaunting rare/exclusive access (e.g., "Got tickets to the sold-out show")
- understated_flex: casually mentioning high-value fact as ordinary (e.g., "That project hit 10k stars")
- self_aware_brag: openly acknowledging bragging (e.g., "Not to brag but...")
- other: edge cases

Risk label priority: misrecognition > context_insensitivity > sycophancy > others.
Default to misrecognition when uncertain (~80% of cases).

Output ONLY the JSON, no explanation."""


UNDERSTANDER_USER_TEMPLATE = """\
Analyze this post's bragging mechanism, speaker intent, desired feedback, and risk.

<input>
  <platform>{platform}</platform>
  <relationship>{relationship}</relationship>
  <agent_role>{agent_role}</agent_role>
  <interaction_goal>{interaction_goal}</interaction_goal>
  <statement>{speaker_post}</statement>
</input>

Output the JSON:"""


# ── Responder prompt ─────────────────────────────────────────────────────────

RESPONDER_SYSTEM_PROMPT = """\
You are a high-EQ social response expert.
You receive a BRAGGING ANALYSIS (mechanism, intent, risk) and CONTEXT (platform, relationship, role, goal).
Your job: choose the best response strategy and write a SHORT natural English reply.

Output ONLY a JSON with exactly 2 keys:
  response_strategy, response_text

Response strategy must be exactly one of these 8 (lowercase):
  validate, light_acknowledgment, ask_followup, humor_tease,
  redirect, neutral_observation, set_boundary, no_response

Strategy selection matrix (MUST follow):
- avoid_sycophancy / stay_neutral -> neutral_observation / redirect (NEVER validate)
- be_supportive_without_overpraising -> light_acknowledgment / validate
- stay_professional_and_avoid_sycophancy -> neutral_observation / redirect
- respond_without_moralizing -> light_acknowledgment / humor_tease
- respond_politely_without_overpraising -> light_acknowledgment / neutral_observation
- close_friend + playful context -> humor_tease / light_acknowledgment
- academic_forum / workplace_channel -> neutral_observation / ask_followup
- pressure for praise / comparison -> set_boundary / redirect

Rules:
- response_text: 15-30 words, natural colloquial English, like a real person texting.
- [NEVER] Be preachy, condescending, or moralizing.
- [AVOID] Excessive flattery or overpraising (no "amazing", "incredible", "legendary", "genius", "perfect", "iconic", "unbelievable").
- [NEVER] Be sarcastic or passive-aggressive.
- response_text MUST match the chosen strategy's definition.
- light_acknowledgment and set_boundary responses MUST NOT contain overpraise words.
- All text MUST be in English.

Output ONLY the JSON, no explanation."""


RESPONDER_USER_TEMPLATE = """\
Given this bragging analysis and context, choose the best strategy and write a response.

Bragging Analysis:
  mechanism: {bragging_mechanism}
  speaker_intention: {speaker_intention}
  desired_feedback: {desired_feedback}
  risk_assessment: {risk_assessment}

Context:
  platform: {platform}
  relationship: {relationship}
  agent_role: {agent_role}
  interaction_goal: {interaction_goal}
  statement: {speaker_post}

Output the JSON:"""


# ── Rewriter prompt (reused from MultiAgentBraggingAgent) ────────────────────

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
        f"- [{i['severity']}] {i['code']}: {i['message']} -> {i['suggestion']}"
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


# ── Understanding Validator ──────────────────────────────────────────────────

_NON_ASCII_RE = re.compile(r"[^\x00-\x7f]")

def _looks_chinese(text: str) -> bool:
    if not text:
        return False
    non_ascii = len(_NON_ASCII_RE.findall(text))
    return non_ascii / max(len(text), 1) > 0.3


def _has_risk_label(text: str) -> bool:
    lowered = text.lower()
    for keywords in RISK_KEYWORDS.values():
        if any(kw in lowered for kw in keywords):
            return True
    return False


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def validate_understanding(data: dict) -> list[str]:
    """Validate understanding output. Returns list of error messages (empty = valid)."""
    errors = []

    required = ["bragging_mechanism", "speaker_intention", "desired_feedback", "risk_assessment"]
    for f in required:
        if f not in data or not str(data[f]).strip():
            errors.append(f"Missing field: {f}")

    if errors:
        return errors

    mech = data.get("bragging_mechanism", "")
    if mech not in ALLOWED_MECHANISMS:
        errors.append(f"Invalid mechanism: '{mech}'. Must be one of {sorted(ALLOWED_MECHANISMS)}")

    risk = data.get("risk_assessment", "")
    if risk and not _has_risk_label(risk):
        errors.append("risk_assessment missing official risk label keyword")

    for field in ["speaker_intention", "desired_feedback", "risk_assessment"]:
        val = data.get(field, "")
        if val and _looks_chinese(val):
            errors.append(f"{field} appears to be in Chinese")

    for field, limit in [("speaker_intention", 80), ("desired_feedback", 80), ("risk_assessment", 100)]:
        val = data.get(field, "")
        if val and _word_count(val) > limit:
            errors.append(f"{field} exceeds {limit}-word limit ({_word_count(val)} words)")

    return errors


def validate_response_plan(data: dict) -> list[str]:
    """Validate response plan output. Returns list of error messages (empty = valid)."""
    errors = []

    for f in ["response_strategy", "response_text"]:
        if f not in data or not str(data[f]).strip():
            errors.append(f"Missing field: {f}")

    if errors:
        return errors

    strat = data.get("response_strategy", "")
    norm_strat = strat.lower().replace("-", "_").replace(" ", "_").strip()
    if norm_strat in ALLOWED_STRATEGIES:
        data["response_strategy"] = norm_strat
    else:
        errors.append(f"Invalid strategy: '{strat}'. Must be one of {sorted(ALLOWED_STRATEGIES)}")

    resp_text = data.get("response_text", "")
    strat_val = data.get("response_strategy", norm_strat)

    if strat_val == "no_response" and resp_text and _word_count(resp_text) > 3:
        errors.append("no_response strategy but response_text is substantial")

    if strat_val != "no_response" and (not resp_text or not resp_text.strip()):
        errors.append("Empty response_text for non-no_response strategy")

    if resp_text and _looks_chinese(resp_text):
        errors.append("response_text appears to be in Chinese")

    if resp_text and _word_count(resp_text) > 60:
        errors.append(f"response_text exceeds 60-word limit ({_word_count(resp_text)} words)")

    # Check overpraise in light_acknowledgment / set_boundary
    overpraise_re = re.compile(
        r"\b(amazing|incredible|legendary|genius|perfect|iconic|unbelievable)\b", re.IGNORECASE
    )
    if strat_val in ("light_acknowledgment", "set_boundary") and resp_text:
        if overpraise_re.search(resp_text):
            errors.append(f"response_text contains overpraise word, inconsistent with {strat_val}")

    return errors


# ── TwoStageBraggingAgent ────────────────────────────────────────────────────

class TwoStageBraggingAgent:
    """
    Pipeline: Understander -> (retry if needed) -> Responder -> (retry if needed)
              -> Merge -> Final Validator -> (optional) Rewriter -> Fallback.
    """

    MAX_UNDERSTAND_RETRIES = 1
    MAX_RESPONSE_RETRIES = 1

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        base_url = base_url or os.getenv(
            "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = model or os.getenv("QWEN_MODEL", "qwen-turbo")
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # Fallback agent (single-stage)
        self._fallback_agent = BraggingResponseAgent(
            api_key=api_key, base_url=base_url, model=model,
        )

        # Stats
        self.stats = {
            "total": 0,
            "two_stage_ok": 0,
            "understand_retry": 0,
            "response_retry": 0,
            "rewrite_triggered": 0,
            "rewrite_success": 0,
            "rewrite_failed": 0,
            "fallback_used": 0,
            "issue_codes": {},
        }

    async def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.5) -> str:
        response = await self._async_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=384,
        )
        return response.choices[0].message.content or ""

    async def _run_understander(self, inp: AgentInput) -> UnderstandingOutput:
        """Stage 1: Understand the bragging post."""
        user_prompt = UNDERSTANDER_USER_TEMPLATE.format(
            platform=inp.platform,
            relationship=inp.relationship,
            agent_role=inp.agent_role,
            interaction_goal=inp.interaction_goal,
            speaker_post=inp.speaker_post,
        )

        last_error = None
        for attempt in range(1 + self.MAX_UNDERSTAND_RETRIES):
            if attempt > 0:
                self.stats["understand_retry"] += 1
                # Add error context for retry
                user_prompt_retry = (
                    f"{user_prompt}\n\nYour previous output had errors: {last_error}\n"
                    f"Please fix and output the corrected JSON."
                )
                raw = await self._call_llm(UNDERSTANDER_SYSTEM_PROMPT, user_prompt_retry)
            else:
                raw = await self._call_llm(UNDERSTANDER_SYSTEM_PROMPT, user_prompt)

            try:
                data = _extract_json(raw)
            except ValueError as e:
                last_error = str(e)
                continue

            errors = validate_understanding(data)
            if not errors:
                return UnderstandingOutput(
                    bragging_mechanism=data["bragging_mechanism"],
                    speaker_intention=data["speaker_intention"],
                    desired_feedback=data["desired_feedback"],
                    risk_assessment=data["risk_assessment"],
                )
            last_error = "; ".join(errors)

        raise RuntimeError(f"Understander failed after retries: {last_error}")

    async def _run_responder(self, inp: AgentInput, understanding: UnderstandingOutput) -> ResponsePlanOutput:
        """Stage 2: Generate response given the understanding."""
        user_prompt = RESPONDER_USER_TEMPLATE.format(
            bragging_mechanism=understanding.bragging_mechanism,
            speaker_intention=understanding.speaker_intention,
            desired_feedback=understanding.desired_feedback,
            risk_assessment=understanding.risk_assessment,
            platform=inp.platform,
            relationship=inp.relationship,
            agent_role=inp.agent_role,
            interaction_goal=inp.interaction_goal,
            speaker_post=inp.speaker_post,
        )

        last_error = None
        for attempt in range(1 + self.MAX_RESPONSE_RETRIES):
            if attempt > 0:
                self.stats["response_retry"] += 1
                user_prompt_retry = (
                    f"{user_prompt}\n\nYour previous output had errors: {last_error}\n"
                    f"Please fix and output the corrected JSON."
                )
                raw = await self._call_llm(RESPONDER_SYSTEM_PROMPT, user_prompt_retry, temperature=0.4)
            else:
                raw = await self._call_llm(RESPONDER_SYSTEM_PROMPT, user_prompt)

            try:
                data = _extract_json(raw)
            except ValueError as e:
                last_error = str(e)
                continue

            errors = validate_response_plan(data)
            if not errors:
                return ResponsePlanOutput(
                    response_strategy=data["response_strategy"],
                    response_text=data["response_text"],
                )
            last_error = "; ".join(errors)

        raise RuntimeError(f"Responder failed after retries: {last_error}")

    async def _attempt_rewrite(
        self, inp: AgentInput, draft: dict, issues: list[dict],
    ) -> tuple[dict | None, str]:
        """Attempt LLM rewrite. Returns (fixed_dict or None, status_string)."""
        try:
            rewriter_input = _build_rewriter_user_prompt(inp, draft, issues)
            raw = await self._call_llm(REWRITER_SYSTEM_PROMPT, rewriter_input, temperature=0.3)
            fixed_data = _extract_json(raw)

            # Validate the rewrite
            fixed_validation = validate_official_row(fixed_data)
            if fixed_validation.valid:
                return fixed_data, "success"
            else:
                logger.warning(
                    f"[{inp.episode_id}] Rewrite still has issues: "
                    f"{[i.code for i in fixed_validation.issues]}"
                )
                return None, "still_invalid"
        except Exception as e:
            logger.warning(f"[{inp.episode_id}] Rewrite failed: {e}")
            return None, "error"

    async def arun(self, inp: AgentInput) -> tuple[AgentOutput, dict]:
        """Run the full two-stage pipeline."""
        self.stats["total"] += 1
        meta: dict[str, Any] = {"episode_id": inp.episode_id, "pipeline": "two_stage"}

        # ── Stage 1: Understander ──
        try:
            understanding = await self._run_understander(inp)
            meta["understander_status"] = "ok"
            meta["understanding"] = asdict(understanding)
        except Exception as e:
            logger.warning(f"[{inp.episode_id}] Understander failed: {e}, falling back to single-agent")
            meta["understander_status"] = "error"
            meta["understander_error"] = str(e)
            return await self._fallback_single_agent(inp, meta)

        # ── Stage 2: Responder ──
        try:
            response_plan = await self._run_responder(inp, understanding)
            meta["responder_status"] = "ok"
            meta["response_plan"] = asdict(response_plan)
        except Exception as e:
            logger.warning(f"[{inp.episode_id}] Responder failed: {e}, falling back to single-agent")
            meta["responder_status"] = "error"
            meta["responder_error"] = str(e)
            return await self._fallback_single_agent(inp, meta)

        # ── Merge ──
        merged = {
            "episode_id": inp.episode_id,
            "bragging_mechanism": understanding.bragging_mechanism,
            "speaker_intention": understanding.speaker_intention,
            "desired_feedback": understanding.desired_feedback,
            "risk_assessment": understanding.risk_assessment,
            "response_strategy": response_plan.response_strategy,
            "response_text": response_plan.response_text,
        }

        # ── Final Validation ──
        validation = validate_official_row(merged)
        meta["validation"] = validation.to_dict()

        if validation.valid:
            self.stats["two_stage_ok"] += 1
            meta["rewrite_attempted"] = False
            return self._to_agent_output(merged), meta

        # ── Record issues ──
        for issue in validation.issues:
            self.stats["issue_codes"][issue.code] = (
                self.stats["issue_codes"].get(issue.code, 0) + 1
            )

        # ── Attempt rewrite ──
        self.stats["rewrite_triggered"] += 1
        meta["rewrite_attempted"] = True

        fixed, status = await self._attempt_rewrite(
            inp, merged, validation.to_dict()["issues"]
        )
        meta["rewrite_status"] = status

        if fixed is not None:
            self.stats["rewrite_success"] += 1
            return self._to_agent_output(fixed), meta

        # ── Rewrite failed: try auto_fix ──
        self.stats["rewrite_failed"] += 1
        fixed_dict = auto_fix(merged)
        autofix_validation = validate_official_row(fixed_dict)
        meta["autofix_validation"] = autofix_validation.to_dict()
        meta["fallback"] = "auto_fix"

        # If auto_fix made it worse, keep original
        if not autofix_validation.valid and validation.valid:
            fixed_dict = merged

        return self._to_agent_output(fixed_dict), meta

    async def _fallback_single_agent(self, inp: AgentInput, meta: dict) -> tuple[AgentOutput, dict]:
        """Fallback to single-agent BraggingResponseAgent."""
        self.stats["fallback_used"] += 1
        meta["fallback"] = "single_agent"

        try:
            gen_out = await self._fallback_agent.arun(inp)
            gen_dict = asdict(gen_out)

            validation = validate_official_row(gen_dict)
            meta["fallback_validation"] = validation.to_dict()

            if validation.valid:
                return gen_out, meta

            # Try rewrite on fallback result
            for issue in validation.issues:
                self.stats["issue_codes"][issue.code] = (
                    self.stats["issue_codes"].get(issue.code, 0) + 1
                )

            self.stats["rewrite_triggered"] += 1
            meta["rewrite_attempted"] = True

            fixed, status = await self._attempt_rewrite(
                inp, gen_dict, validation.to_dict()["issues"]
            )
            meta["rewrite_status"] = status

            if fixed is not None:
                self.stats["rewrite_success"] += 1
                return self._to_agent_output(fixed), meta

            # Last resort: auto_fix
            self.stats["rewrite_failed"] += 1
            fixed_dict = auto_fix(gen_dict)
            return self._to_agent_output(fixed_dict), meta

        except Exception as e:
            logger.error(f"[{inp.episode_id}] Fallback also failed: {e}")
            raise

    @staticmethod
    def _to_agent_output(data: dict) -> AgentOutput:
        return AgentOutput(
            episode_id=data["episode_id"],
            bragging_mechanism=data["bragging_mechanism"],
            speaker_intention=data["speaker_intention"],
            desired_feedback=data["desired_feedback"],
            risk_assessment=data["risk_assessment"],
            response_strategy=data["response_strategy"],
            response_text=data["response_text"],
        )
