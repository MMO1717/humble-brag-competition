from __future__ import annotations

import re
from typing import Any


REQUIRED_INPUT_FIELDS = {
    "episode_id",
    "speaker_post",
    "platform",
    "relationship",
    "agent_role",
    "interaction_goal",
}

OUTPUT_FIELDS = [
    "episode_id",
    "bragging_mechanism",
    "speaker_intention",
    "desired_feedback",
    "risk_assessment",
    "response_strategy",
    "response_text",
]

REQUIRED_OUTPUT_FIELDS = set(OUTPUT_FIELDS)

ALLOWED_MECHANISMS = {
    "humble_complaint",
    "faux_modesty",
    "achievement_drop",
    "comparison_superiority",
    "scarcity_flex",
    "understated_flex",
    "self_aware_brag",
    "other",
}

ALLOWED_STRATEGIES = {
    "validate",
    "light_acknowledgment",
    "ask_followup",
    "humor_tease",
    "redirect",
    "neutral_observation",
    "set_boundary",
    "no_response",
}

MAX_WORDS = {
    "speaker_intention": 80,
    "desired_feedback": 80,
    "risk_assessment": 100,
    "response_text": 60,
}

SUSPICIOUS_PATTERNS = [
    re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL),
    re.compile(r"</?think>", re.IGNORECASE),
    re.compile(r"\bchain of thought\b", re.IGNORECASE),
    re.compile(r"\bstep by step\b", re.IGNORECASE),
    re.compile(r"\b(reasoning|analysis|scratchpad)\s*:", re.IGNORECASE),
    re.compile(r"\b(option|candidate)\s*[12]\b", re.IGNORECASE),
    re.compile(r"^(system|assistant|user)\s*:", re.IGNORECASE),
]

OVERPRAISE_PATTERNS = [
    re.compile(r"\b(amazing|incredible|legendary|genius|perfect|iconic|unbelievable)\b", re.IGNORECASE),
    re.compile(r"\b(best|greatest)\s+(ever|person|one|at)\b", re.IGNORECASE),
    re.compile(r"\bso proud of you\b", re.IGNORECASE),
]


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def strip_suspicious_text(text: str) -> str:
    cleaned = text or ""
    for pattern in SUSPICIOUS_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def truncate_words(text: str, max_words: int) -> str:
    words = re.findall(r"\b[\w'-]+\b|[^\w\s]", text)
    count = 0
    kept: list[str] = []
    for token in words:
        if re.match(r"\b[\w'-]+\b", token):
            count += 1
        if count > max_words:
            break
        kept.append(token)
    result = " ".join(kept)
    result = re.sub(r"\s+([,.;:!?])", r"\1", result).strip()
    if result and result[-1] not in ".!?":
        result += "."
    return result


def safe_text(text: str, max_words: int) -> str:
    cleaned = strip_suspicious_text(text)
    if word_count(cleaned) > max_words:
        cleaned = truncate_words(cleaned, max_words)
    return cleaned


def normalize_output_row(row: dict[str, Any]) -> dict[str, str]:
    normalized = {field: str(row.get(field, "")).strip() for field in OUTPUT_FIELDS}

    if normalized["bragging_mechanism"] not in ALLOWED_MECHANISMS:
        normalized["bragging_mechanism"] = "understated_flex"
    if normalized["response_strategy"] not in ALLOWED_STRATEGIES:
        normalized["response_strategy"] = "light_acknowledgment"

    for field in ["speaker_intention", "desired_feedback", "risk_assessment", "response_text"]:
        normalized[field] = safe_text(normalized[field], MAX_WORDS[field])

    if normalized["response_strategy"] == "no_response":
        normalized["response_text"] = truncate_words(normalized["response_text"], 8) if normalized["response_text"] else ""
    elif normalized["response_strategy"] in {"set_boundary", "light_acknowledgment"}:
        response = normalized["response_text"]
        for pattern in OVERPRAISE_PATTERNS:
            response = pattern.sub("notable", response)
        normalized["response_text"] = safe_text(response, MAX_WORDS["response_text"])

    return normalized
