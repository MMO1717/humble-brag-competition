from __future__ import annotations

from typing import Any

from .output_builder import build_fallback_row
from .skills import (
    MechanismSkill,
    ResponseRiskReviewSkill,
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

    def __init__(self, cfg: Any | None = None) -> None:
        self.skills: list[Skill] = [
            MechanismSkill(),
            UnderstandingSkill(),
            StrategySkill(),
            RiskSkill(),
            ResponseSkill(),
        ]
        if cfg is None or getattr(cfg, "USE_RESPONSE_RISK_REVIEW", True):
            self.skills.append(ResponseRiskReviewSkill())
        self.skills.append(ValidatorSkill())
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
            "risk_labels_before_response": [],
            "risk_labels_after_response": [],
            "risk_assessment": None,
            "response_strategy": None,
            "response_text": None,
            "raw_outputs": {},
            "fewshot_examples": {},
            "memory_used": {},
            "skill_trace": [],
            "skill_errors": [],
            "validation_errors": [],
            "is_valid": False,
            "final_output": None,
            # 供结果统计和调试使用的轨迹字段。
            "mechanism_calibration": None,
            "strategy_trace": None,
            "llm_response_accepted": False,
            "fallback_used": False,
            "fallback_reason": "",
            "response_risk_review_added": [],
            "response_risk_review_warnings": [],
            "response_risk_review_rewritten": False,
        }

    def run_row(self, input_row: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        state = self.initial_state(input_row)
        for skill in self.skills:
            state = self._run_skill(skill, state, context)

        if not state.get("is_valid"):
            print(
                f"[WARN] {input_row['episode_id']} 首次校验未通过，正在执行 Rewriter。",
                flush=True,
            )
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
            print(
                f"[WARN] {input_row['episode_id']} 重写后仍未通过校验，已使用整行兜底输出。",
                flush=True,
            )

        if getattr(context["cfg"], "DEBUG_SKILL_TRACE", False):
            episode_id = input_row["episode_id"]
            trace = " -> ".join(state.get("skill_trace", []))
            risks = ",".join(state.get("risk_labels", []))
            error_count = len(state.get("skill_errors", []))
            print(f"[TRACE] {episode_id}: {trace}")
            print(f"[TRACE]   risks=[{risks}] errors={error_count}")

        return state

    def _run_skill(self, skill: Skill, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        state["skill_trace"].append(skill.name)
        try:
            state = skill.run(state, context)
        except Exception as exc:
            state["skill_errors"].append({"skill": skill.name, "error": str(exc)})
            print(
                f"[WARN] {state.get('episode_id', 'unknown')} 的 "
                f"{skill.name} 执行异常，流程将继续：{exc}",
                flush=True,
            )
        return state
