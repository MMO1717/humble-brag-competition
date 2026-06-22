from __future__ import annotations

from typing import Any

from ..output_builder import build_output_row
from ..schemas import DEFAULT_RESPONSE_BY_STRATEGY, DEFAULT_STRATEGY
from .base import Skill


class RewriterSkill(Skill):
    name = "RewriterSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        strategy = state.get("response_strategy", DEFAULT_STRATEGY)
        if strategy not in DEFAULT_RESPONSE_BY_STRATEGY:
            strategy = DEFAULT_STRATEGY
            state["response_strategy"] = strategy

        if not state.get("response_text") or state.get("validation_errors"):
            state["response_text"] = DEFAULT_RESPONSE_BY_STRATEGY[strategy]

        state["final_output"] = build_output_row(state["input_row"], state)
        return state
