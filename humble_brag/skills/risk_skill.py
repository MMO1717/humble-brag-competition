from __future__ import annotations

from typing import Any

from ..postprocess import infer_contextual_risk_labels, normalize_risk_assessment
from .base import Skill


class RiskSkill(Skill):
    name = "RiskSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        row = state["input_row"]
        strategy = state.get("response_strategy")
        labels = sorted(infer_contextual_risk_labels(row, strategy))
        assessment = normalize_risk_assessment("", input_row=row, strategy=strategy)
        state["raw_outputs"]["risk"] = "rule_based"
        state["risk_labels"] = labels
        state["risk_assessment"] = assessment
        return state
