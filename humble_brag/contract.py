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
    re.compile(r"\b(impressive|impressed|great|awesome)\b", re.IGNORECASE),
    re.compile(r"\b(congrats|congratulations)\b", re.IGNORECASE),
    re.compile(r"\bwell done\b", re.IGNORECASE),
    re.compile(r"\bquite a feat\b", re.IGNORECASE),
    re.compile(r"\bnice work\b", re.IGNORECASE),
    re.compile(r"\bproud of you\b", re.IGNORECASE),
    re.compile(r"\b(best|greatest)\s+(ever|person|one|at)\b", re.IGNORECASE),
    re.compile(r"\bso proud of you\b", re.IGNORECASE),
]

RISK_LABEL_PATTERNS = {
    "sycophancy": re.compile(r"\b(sycophancy|sycophantic|overpraise|over-praise|excessive praise|blind validation|flattery|overvalidation)\b", re.IGNORECASE),
    "preachiness": re.compile(r"\b(preachiness|preach|preachy|moralize|moralizing|lecture|judgmental)\b", re.IGNORECASE),
    "misrecognition": re.compile(r"\b(misrecognition|misread|misinterpret|false assumption|assume expertise|unsupported assumption)\b", re.IGNORECASE),
    "strategy_inconsistency": re.compile(r"\b(strategy_inconsistency|strategy inconsistency|inconsistent strategy|strategy mismatch|does not match the strategy)\b", re.IGNORECASE),
    "context_insensitivity": re.compile(r"\b(context_insensitivity|context insensitivity|context insensitive|ignore the context|miss the context|audience|setting)\b", re.IGNORECASE),
    "over_coldness": re.compile(r"\b(over_coldness|over cold|over-cold|too cold|dismissive|curt|coldness|dismissiveness)\b", re.IGNORECASE),
}

CONTEXT_SENSITIVE_STRATEGIES = {
    "light_acknowledgment",
    "neutral_observation",
    "redirect",
    "set_boundary",
}


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


def has_overpraise(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in OVERPRAISE_PATTERNS)


def reduce_overpraise(text: str, strategy: str) -> str:
    if not text:
        return ""
    if strategy == "neutral_observation" and has_overpraise(text):
        return "That gives useful context without overstating it."

    cleaned = text
    for pattern in OVERPRAISE_PATTERNS:
        cleaned = pattern.sub("notable", cleaned)
    cleaned = re.sub(r"\bI'?m notable by\b", "I notice", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bThat'?s notable[!.]?\s*", "That is useful context. ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def risk_labels_present(text: str) -> set[str]:
    return {label for label, pattern in RISK_LABEL_PATTERNS.items() if pattern.search(text or "")}


def ensure_risk_labels(text: str, strategy: str) -> str:
    if risk_labels_present(text):
        return text

    if strategy in {"validate", "light_acknowledgment"}:
        addition = "Potential risks include sycophancy and overvalidation if the reply overpraises the speaker."
    elif strategy in {"set_boundary", "no_response"}:
        addition = "Potential risks include over_coldness and dismissiveness if the reply feels too curt."
    elif strategy in {"neutral_observation", "redirect"}:
        addition = "Potential risks include misrecognition and context_insensitivity if the reply misses the audience or setting."
    else:
        addition = "Potential risks include misrecognition and context_insensitivity if the reply assumes the bragging cue incorrectly."

    combined = f"{text} {addition}".strip()
    return safe_text(combined, MAX_WORDS["risk_assessment"])


def normalize_output_row(row: dict[str, Any], input_context: dict[str, Any] | None = None) -> dict[str, str]:
    normalized = {field: str(row.get(field, "")).strip() for field in OUTPUT_FIELDS}

    if normalized["bragging_mechanism"] not in ALLOWED_MECHANISMS:
        normalized["bragging_mechanism"] = "understated_flex"
    if normalized["response_strategy"] not in ALLOWED_STRATEGIES:
        normalized["response_strategy"] = "light_acknowledgment"

    for field in ["speaker_intention", "desired_feedback", "risk_assessment", "response_text"]:
        normalized[field] = safe_text(normalized[field], MAX_WORDS[field])

    normalized["risk_assessment"] = ensure_risk_labels(
        normalized["risk_assessment"],
        normalized["response_strategy"],
    )

    interaction_goal = ""
    if input_context:
        interaction_goal = str(input_context.get("interaction_goal", "")).strip()
    should_reduce_praise = (
        normalized["response_strategy"] in CONTEXT_SENSITIVE_STRATEGIES
        or interaction_goal in {"stay_neutral", "avoid_sycophancy"}
    )

    if normalized["response_strategy"] == "no_response":
        normalized["response_text"] = truncate_words(normalized["response_text"], 8) if normalized["response_text"] else ""
    elif should_reduce_praise:
        response = reduce_overpraise(normalized["response_text"], normalized["response_strategy"])
        normalized["response_text"] = safe_text(response, MAX_WORDS["response_text"])

    return normalized
