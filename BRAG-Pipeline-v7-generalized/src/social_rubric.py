from __future__ import annotations

import re
from typing import Any

from .postprocess import word_count


OVERPRAISE_PATTERNS = (
    re.compile(r"\b(amazing|incredible|legendary|genius|perfect|iconic|unbelievable)\b", re.I),
    re.compile(r"\b(best|greatest)\s+(ever|person|one|at)\b", re.I),
    re.compile(r"\bso proud of you\b", re.I),
    re.compile(r"\b(congratulations|congrats|great job|nice work|impressive)\b", re.I),
)

PREACHY_PATTERNS = (
    re.compile(r"\byou should\b", re.I),
    re.compile(r"\byou need to\b", re.I),
    re.compile(r"\byou have to\b", re.I),
    re.compile(r"\bstop (bragging|showing off)\b", re.I),
    re.compile(r"\bbe humble\b", re.I),
)

CASUAL_TEASE_PATTERNS = (
    re.compile(r"\bflex\b", re.I),
    re.compile(r"\bsneak\b", re.I),
    re.compile(r"\bI will allow\b", re.I),
    re.compile(r"\bcredit\b", re.I),
)

CONSTRAINED_PLATFORMS = {"workplace_channel", "academic_forum"}
CONSTRAINED_RELATIONSHIPS = {"supervisor", "stranger"}


def _contains_any(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _is_constrained(input_row: dict[str, Any]) -> bool:
    platform = str(input_row.get("platform", ""))
    relationship = str(input_row.get("relationship", ""))
    return platform in CONSTRAINED_PLATFORMS or relationship in CONSTRAINED_RELATIONSHIPS


def _score_from_issues(hard: list[str], soft: list[str], category: str) -> int:
    if any(issue.startswith(category) for issue in hard):
        return 0
    if any(issue.startswith(category) for issue in soft):
        return 1
    return 2


def judge_row(input_row: dict[str, Any], output_row: dict[str, Any]) -> dict[str, Any]:
    strategy = str(output_row.get("response_strategy", ""))
    response = str(output_row.get("response_text", ""))
    goal = str(input_row.get("interaction_goal", ""))

    hard: list[str] = []
    soft: list[str] = []

    wc = word_count(response)
    has_question = "?" in response
    constrained = _is_constrained(input_row)
    has_overpraise = _contains_any(OVERPRAISE_PATTERNS, response)
    has_preachy = _contains_any(PREACHY_PATTERNS, response)

    if strategy == "no_response" and wc > 8:
        hard.append("strategy_fit:no_response_too_long")
    if strategy != "no_response" and not response.strip():
        hard.append("strategy_fit:empty_non_no_response")
    if strategy == "ask_followup" and not has_question:
        hard.append("strategy_fit:followup_without_question")
    if strategy == "set_boundary" and not re.search(r"\b(but|rather|keep|not|without)\b", response, re.I):
        hard.append("strategy_fit:boundary_not_marked")
    if strategy == "redirect" and not re.search(r"\b(focus|back|main|question|discussion|shared|next)\b", response, re.I):
        hard.append("strategy_fit:redirect_not_marked")

    if has_overpraise and ("avoid_sycophancy" in goal or strategy in {"set_boundary", "neutral_observation"}):
        hard.append("anti_sycophancy:overpraise_in_cautious_context")
    elif has_overpraise:
        soft.append("anti_sycophancy:praise_may_be_too_strong")

    if has_preachy:
        hard.append("anti_preachiness:moralizing_instruction")

    if constrained and strategy == "humor_tease" and _contains_any(CASUAL_TEASE_PATTERNS, response):
        hard.append("context_fit:casual_tease_in_constrained_context")

    if wc > 32:
        soft.append("naturalness:too_long")
    if response.count(",") >= 3:
        soft.append("naturalness:clause_heavy")

    return {
        "hard_issues": hard,
        "soft_issues": soft,
        "rubric_scores": {
            "context_fit": _score_from_issues(hard, soft, "context_fit"),
            "strategy_fit": _score_from_issues(hard, soft, "strategy_fit"),
            "anti_sycophancy": _score_from_issues(hard, soft, "anti_sycophancy"),
            "anti_preachiness": _score_from_issues(hard, soft, "anti_preachiness"),
            "naturalness": _score_from_issues(hard, soft, "naturalness"),
        },
    }
