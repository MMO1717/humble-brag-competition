from __future__ import annotations

from typing import Any

from ..postprocess import ensure_risk_assessment
from ..schemas import DEFAULT_RISK_ASSESSMENT
from .base import Skill


def _rule_labels(row: dict[str, Any]) -> list[str]:
    platform = str(row.get("platform", ""))
    relationship = str(row.get("relationship", ""))
    goal = str(row.get("interaction_goal", ""))

    labels = ["misrecognition"]
    if (
        platform in {"academic_forum", "public_social_media", "community_forum"}
        or relationship in {"online_peer", "stranger"}
        or goal in {"stay_neutral", "respond_politely_without_overpraising"}
        or "professional" in goal
        or (platform == "group_chat" and relationship != "classmate")
    ):
        labels.append("context_insensitivity")
    return labels[:2]


def _assessment_from_labels(labels: list[str]) -> str:
    if not labels:
        return DEFAULT_RISK_ASSESSMENT
    phrase_by_label = {
        "sycophancy": "sycophancy",
        "preachiness": "preachiness",
        "misrecognition": "misrecognition",
        "context_insensitivity": "context insensitivity",
        "strategy_inconsistency": "strategy inconsistency",
        "over_coldness": "over-coldness",
    }
    joined = " and ".join(phrase_by_label.get(label, label) for label in labels)
    return f"The reply should avoid {joined} while staying brief and context-aware."


class RiskSkill(Skill):
    name = "RiskSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        row = state["input_row"]
        labels = _rule_labels(row)
        assessment = _assessment_from_labels(labels)
        state["raw_outputs"]["risk"] = "rule_based"
        state["risk_labels"] = labels
        state["risk_assessment"] = ensure_risk_assessment(assessment)
        return state
