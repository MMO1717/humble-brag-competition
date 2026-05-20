from __future__ import annotations

import re
from typing import Any

from .contract import normalize_output_row


ACHIEVEMENT_WORDS = {
    "accepted",
    "award",
    "beat",
    "finished",
    "first",
    "got",
    "landed",
    "promotion",
    "published",
    "rank",
    "score",
    "selected",
    "top",
    "won",
}

COMPLAINT_WORDS = {"tired", "exhausted", "annoying", "stressful", "rough", "hard", "busy", "can't believe"}
SELF_AWARE_WORDS = {"not to brag", "humblebrag", "flex", "brag", "i know this sounds"}
SCARCITY_WORDS = {"rare", "exclusive", "sold out", "waitlist", "hard to get", "only one", "limited"}
COMPARISON_WORDS = {"better than", "more than", "faster than", "slower than", "ahead of", "top", "ranked", "first"}
MODESTY_WORDS = {"just", "somehow", "apparently", "i guess", "small", "little", "only", "not much"}


def contains_any(text: str, needles: set[str]) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def has_number_signal(text: str) -> bool:
    return bool(re.search(r"\b\d+([.,]\d+)?\b|[+]\d+", text))


def classify_mechanism(post: str) -> str:
    lowered = post.lower()
    has_achievement = contains_any(lowered, ACHIEVEMENT_WORDS) or has_number_signal(lowered)

    if contains_any(lowered, SELF_AWARE_WORDS):
        return "self_aware_brag"
    if contains_any(lowered, COMPLAINT_WORDS) and has_achievement:
        return "humble_complaint"
    if contains_any(lowered, COMPARISON_WORDS):
        return "comparison_superiority"
    if contains_any(lowered, SCARCITY_WORDS):
        return "scarcity_flex"
    if contains_any(lowered, MODESTY_WORDS) and has_achievement:
        return "faux_modesty"
    if has_achievement:
        return "achievement_drop"
    return "understated_flex"


def choose_strategy(row: dict[str, Any], mechanism: str) -> str:
    goal = row.get("interaction_goal", "")
    relationship = row.get("relationship", "")
    platform = row.get("platform", "")
    post = row.get("speaker_post", "").lower()

    if "professional" in goal or platform in {"workplace_channel", "academic_forum"}:
        return "neutral_observation"
    if goal == "stay_neutral":
        return "neutral_observation"
    if goal == "avoid_sycophancy":
        if relationship in {"acquaintance", "classmate"}:
            return "ask_followup"
        return "neutral_observation"
    if goal == "deescalate_awkwardness":
        if relationship in {"close_friend", "online_peer"}:
            return "humor_tease"
        return "redirect"
    if goal == "respond_without_moralizing":
        return "light_acknowledgment"
    if relationship == "close_friend" and mechanism in {"self_aware_brag", "comparison_superiority"}:
        return "humor_tease"
    if relationship == "classmate" or "?" in post:
        return "ask_followup"
    if "supportive" in goal:
        return "light_acknowledgment"
    if "politely" in goal:
        return "light_acknowledgment"
    return "neutral_observation"


def infer_intention(mechanism: str) -> str:
    templates = {
        "humble_complaint": "The speaker is presenting a burden or inconvenience while still implying a positive achievement or status signal.",
        "faux_modesty": "The speaker is downplaying the achievement while still drawing attention to it.",
        "achievement_drop": "The speaker is sharing an accomplishment and likely wants it to be noticed.",
        "comparison_superiority": "The speaker is framing their result as stronger by comparing it with others or with a harder condition.",
        "scarcity_flex": "The speaker is signaling access to something rare, selective, or hard to obtain.",
        "understated_flex": "The speaker is indirectly signaling a positive outcome without making a direct boast.",
        "self_aware_brag": "The speaker is openly acknowledging the boast while trying to keep it playful.",
        "other": "The speaker is sharing a potentially status-related detail that may invite recognition.",
    }
    return templates.get(mechanism, templates["understated_flex"])


def infer_feedback(strategy: str) -> str:
    if strategy == "ask_followup":
        return "They likely want engaged curiosity without excessive praise or unsupported assumptions."
    if strategy == "humor_tease":
        return "They likely want amused recognition that keeps the exchange light."
    if strategy == "neutral_observation":
        return "They likely want the context acknowledged without turning the reply into flattery."
    if strategy == "redirect":
        return "They likely want a response that keeps the conversation moving without escalating the brag."
    return "They likely want brief recognition without excessive praise."


def infer_risk(strategy: str, row: dict[str, Any]) -> str:
    risks = ["misrecognition", "context insensitivity"]
    goal = row.get("interaction_goal", "")
    if "avoid_sycophancy" in goal or "overpraising" in goal:
        risks.insert(0, "sycophancy")
    if "moralizing" in goal:
        risks.append("preachiness")
    if strategy in {"redirect", "no_response"}:
        risks.append("over-coldness")
    if strategy in {"ask_followup", "humor_tease"}:
        risks.append("strategy inconsistency")
    return "Potential risks include " + ", ".join(dict.fromkeys(risks)) + "; keep the reply grounded in the audience and setting."


def generate_response(strategy: str, row: dict[str, Any]) -> str:
    platform = row.get("platform", "")
    relationship = row.get("relationship", "")

    if strategy == "ask_followup":
        return "Interesting context. What part of that felt most meaningful to you?"
    if strategy == "humor_tease":
        return "That is a very efficient way to make a casual update sound like a win."
    if strategy == "redirect":
        return "Fair enough. Anyway, what are you working on next?"
    if strategy == "validate":
        return "That sounds like a solid result, and the context helps explain why it matters."
    if strategy == "set_boundary":
        return "I hear the point, but I would keep the focus on the shared situation."
    if strategy == "no_response":
        return ""
    if strategy == "neutral_observation" or platform in {"academic_forum", "workplace_channel"}:
        return "That context does make the result easier to understand without overstating it."
    if relationship == "close_friend":
        return "Nice, that is worth a small victory lap."
    return "That sounds meaningful without needing to make too much of it."


def generate_baseline_row(row: dict[str, Any]) -> dict[str, str]:
    post = str(row.get("speaker_post", ""))
    mechanism = classify_mechanism(post)
    strategy = choose_strategy(row, mechanism)
    output = {
        "episode_id": row.get("episode_id", ""),
        "bragging_mechanism": mechanism,
        "speaker_intention": infer_intention(mechanism),
        "desired_feedback": infer_feedback(strategy),
        "risk_assessment": infer_risk(strategy, row),
        "response_strategy": strategy,
        "response_text": generate_response(strategy, row),
    }
    return normalize_output_row(output)

