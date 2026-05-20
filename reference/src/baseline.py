from __future__ import annotations

from typing import Any

from .output_builder import build_fallback_row, build_output_row
from .postprocess import parse_json_object
from .prompts import build_baseline_prompt
from .validators import validate_output


class BaselineFlow:
    """Minimal single-call baseline used before SkillFlow experiments."""

    def initial_state(self, input_row: dict[str, Any]) -> dict[str, Any]:
        return {
            "input_row": input_row,
            "episode_id": input_row["episode_id"],
            "bragging_mechanism": None,
            "speaker_intention": None,
            "desired_feedback": None,
            "risk_labels": [],
            "risk_assessment": None,
            "response_strategy": None,
            "response_text": None,
            "raw_outputs": {},
            "fewshot_examples": {},
            "skill_trace": [],
            "skill_errors": [],
            "validation_errors": [],
            "is_valid": False,
            "final_output": None,
        }

    def run_row(self, input_row: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        state = self.initial_state(input_row)
        llm_client = context["llm_client"]
        cfg = context["cfg"]
        messages = build_baseline_prompt(input_row)

        try:
            logger = context.get("debug_logger")
            if logger:
                raw = logger.timed_llm_call(
                    episode_id=state["episode_id"],
                    skill="BaselineGeneration",
                    llm_client=llm_client,
                    messages=messages,
                    temperature=cfg.TEMPERATURE,
                    max_tokens=cfg.MAX_TOKENS,
                )
            else:
                raw = llm_client.call_chat(
                    messages,
                    temperature=cfg.TEMPERATURE,
                    max_tokens=cfg.MAX_TOKENS,
                )
            state["raw_outputs"]["baseline"] = raw
            parsed = parse_json_object(raw) or {}
            for key in (
                "bragging_mechanism",
                "speaker_intention",
                "desired_feedback",
                "risk_assessment",
                "response_strategy",
                "response_text",
            ):
                state[key] = parsed.get(key)
            state["skill_trace"].append("BaselineGeneration")
        except Exception as exc:
            state["skill_errors"].append({"skill": "BaselineGeneration", "error": str(exc)})
            state["skill_trace"].append("BaselineGeneration:failed")

        state["final_output"] = build_output_row(input_row, state)
        try:
            validate_output(state["final_output"], input_row)
            state["is_valid"] = True
            state["skill_trace"].append("Validator")
        except Exception as exc:
            state["validation_errors"].append(str(exc))
            state["final_output"] = build_fallback_row(input_row)
            validate_output(state["final_output"], input_row)
            state["is_valid"] = True
            state["skill_errors"].append(
                {"skill": "BaselineFlow", "error": "使用整行兜底输出"}
            )
            state["skill_trace"].append("Validator:failed")
            state["skill_trace"].append("Fallback")

        return state
