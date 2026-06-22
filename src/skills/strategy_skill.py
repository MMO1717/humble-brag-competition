from __future__ import annotations
from typing import Any

from ..schemas import VALID_RESPONSE_STRATEGIES, DEFAULT_STRATEGY
from ..postprocess import safe_strategy
from ..strategy_rules import choose_strategy_with_trace
from .base import Skill


class StrategySkill(Skill):
    name = "StrategySkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        row = state["input_row"]
        try:
            understanding = {
                "speaker_intention": state.get("speaker_intention", ""),
                "desired_feedback": state.get("desired_feedback", ""),
                "risk_assessment": state.get("risk_assessment", ""),
            }
            result = choose_strategy_with_trace(
                row,
                state.get("bragging_mechanism", "other"),
                understanding,
            )
            strategy = result["strategy"]
            state["strategy_trace"] = result["strategy_trace"]
        except Exception as exc:
            state["skill_errors"].append({"skill": self.name, "error": str(exc)})
            strategy = DEFAULT_STRATEGY
            print(
                f"[WARN] {state['episode_id']} 策略选择失败，"
                f"已使用默认策略 {DEFAULT_STRATEGY}：{exc}",
                flush=True,
            )

        state["response_strategy"] = safe_strategy(strategy, VALID_RESPONSE_STRATEGIES)
        return state
