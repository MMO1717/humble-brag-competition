from __future__ import annotations

from typing import Any

from .output_builder import build_fallback_row
from .skills import (
    MechanismSkill,
    ResponseSkill,
    RewriterSkill,
    RiskSkill,
    Skill,
    StrategySkill,
    UnderstandingSkill,
    ValidatorSkill,
)
from .validators import validate_output


class SkillFlow:
    """固定顺序的受控流程，不做自由规划 Agent。"""

    def __init__(self) -> None:
        self.skills: list[Skill] = [
            MechanismSkill(),
            UnderstandingSkill(),
            RiskSkill(),
            StrategySkill(),
            ResponseSkill(),
            ValidatorSkill(),
        ]
        self.rewriter = RewriterSkill()
        self.validator = ValidatorSkill()

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
        for skill in self.skills:
            state = self._run_skill(skill, state, context)

        if not state.get("is_valid"):
            state = self._run_skill(self.rewriter, state, context)
            state = self._run_skill(self.validator, state, context)

        if not state.get("is_valid"):
            fallback = build_fallback_row(input_row)
            validate_output(fallback, input_row)
            state["final_output"] = fallback
            state["is_valid"] = True
            state["skill_errors"].append(
                {"skill": "SkillFlow", "error": "使用整行兜底输出"}
            )

        if getattr(context["cfg"], "DEBUG_SKILL_TRACE", False):
            episode_id = input_row["episode_id"]
            trace = " -> ".join(state.get("skill_trace", []))
            risks = ",".join(state.get("risk_labels", []))
            error_count = len(state.get("skill_errors", [])) + len(state.get("validation_errors", []))
            print(
                f"  Skill trace {episode_id}: {trace} | "
                f"mechanism={state.get('bragging_mechanism')} | "
                f"strategy={state.get('response_strategy')} | "
                f"risks={risks} | errors={error_count}"
            )

        return state

    def _run_skill(
        self,
        skill: Skill,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            state = skill.run(state, context)
            state["skill_trace"].append(skill.name)
        except Exception as exc:
            state["skill_errors"].append({"skill": skill.name, "error": str(exc)})
            state["skill_trace"].append(f"{skill.name}:failed")
        return state
