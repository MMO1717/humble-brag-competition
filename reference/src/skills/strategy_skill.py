from __future__ import annotations

from typing import Any

from ..postprocess import safe_strategy
from ..schemas import VALID_RESPONSE_STRATEGIES
from ..strategy_rules import choose_strategy
from .base import Skill


class StrategySkill(Skill):
    name = "StrategySkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        try:
            strategy = choose_strategy(
                state["input_row"],
                state.get("bragging_mechanism", "other"),
                {
                    "speaker_intention": state.get("speaker_intention", ""),
                    "desired_feedback": state.get("desired_feedback", ""),
                    "risk_assessment": state.get("risk_assessment", ""),
                },
            )
        except Exception as exc:
            state["skill_errors"].append({"skill": self.name, "error": str(exc)})
            strategy = "light_acknowledgment"
        state["response_strategy"] = safe_strategy(strategy, VALID_RESPONSE_STRATEGIES)
        return state
