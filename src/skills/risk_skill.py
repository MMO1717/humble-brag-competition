from __future__ import annotations
from typing import Any

from ..postprocess import infer_contextual_risk_labels, render_risk_assessment
from .base import Skill


def build_risk_control_plan(
    row: dict[str, Any],
    strategy: str | None,
    mechanism: str | None,
    labels: set[str],
) -> dict[str, Any]:
    platform = str(row.get("platform", ""))
    relationship = str(row.get("relationship", ""))
    goal = str(row.get("interaction_goal", ""))
    strategy = str(strategy or "")
    mechanism = str(mechanism or "")

    avoid = set(labels)
    must_not = {
        "do not call out bragging directly",
        "do not invent facts beyond the post",
    }
    if "avoid_sycophancy" in goal or strategy in {"neutral_observation", "light_acknowledgment", "redirect"}:
        avoid.add("sycophancy")
        must_not.add("do not overpraise")
    if platform in {"workplace_channel", "academic_forum", "public_social_media"}:
        avoid.add("context_insensitivity")
        must_not.add("do not use overly casual or intimate language")
    if strategy == "ask_followup":
        must_not.add("do not answer with a statement only")
    if strategy == "redirect":
        must_not.add("do not stay focused on ranking or self-praise")
    if mechanism == "comparison_superiority":
        must_not.add("do not amplify the comparison")

    if relationship in {"close_friend", "friend", "family_member", "romantic_partner"}:
        tone = "measured and warm"
        must_not.add("do not sound dismissive or cold")
    elif platform in {"workplace_channel", "academic_forum"}:
        tone = "professional and restrained"
    elif platform in {"public_social_media", "community_forum"}:
        tone = "public-facing and measured"
    else:
        tone = "measured but not cold"

    return {
        "avoid": sorted(avoid),
        "tone": tone,
        "must_not": sorted(must_not),
    }


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
        state["risk_control_plan"] = build_risk_control_plan(
            row,
            strategy,
            state.get("bragging_mechanism"),
            labels,
        )
        return state
