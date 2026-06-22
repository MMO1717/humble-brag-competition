from __future__ import annotations
from typing import Any

from ..postprocess import infer_contextual_risk_labels, render_risk_assessment
from .base import Skill


class RiskSkill(Skill):
    name = "RiskSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        row = state["input_row"]
        strategy = state.get("response_strategy")
        labels = infer_contextual_risk_labels(
            row,
            strategy,
            state.get("bragging_mechanism"),
        )

        assessment = render_risk_assessment(labels)
        state["raw_outputs"]["risk"] = "rule_based"
        state["risk_labels"] = sorted(labels)
        state["risk_labels_before_response"] = sorted(labels)
        state["risk_assessment"] = assessment
        return state
