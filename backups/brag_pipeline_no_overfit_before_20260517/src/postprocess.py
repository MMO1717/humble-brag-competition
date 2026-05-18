from __future__ import annotations

import json
import re
from typing import Any

from .schemas import (
    DEFAULT_DESIRED_FEEDBACK,
    DEFAULT_MECHANISM,
    DEFAULT_RESPONSE_BY_STRATEGY,
    DEFAULT_RISK_ASSESSMENT,
    DEFAULT_SPEAKER_INTENTION,
    DEFAULT_STRATEGY,
    MAX_WORDS,
    OVERPRAISE_TERMS,
    RISK_LABELS,
)


SUSPICIOUS_PATTERNS = [
    re.compile(r"<think>|</think>", re.IGNORECASE),
    re.compile(r"\bchain of thought\b", re.IGNORECASE),
    re.compile(r"\bstep by step\b", re.IGNORECASE),
    re.compile(r"\b(reasoning|analysis|scratchpad)\s*:", re.IGNORECASE),
    re.compile(r"^(system|assistant|user)\s*:", re.IGNORECASE),
    re.compile(r"\b(option|candidate)\s*[12]\b", re.IGNORECASE),
]

CODE_FENCE_RE = re.compile(r"```(?:json|text|markdown)?\s*|\s*```", re.IGNORECASE)
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
PREFIX_RE = re.compile(r"^\s*(assistant|response|answer|analysis|reasoning)\s*:\s*", re.IGNORECASE)
WORD_RE = re.compile(r"\b[\w'-]+\b")


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def truncate_words(text: str, max_words: int) -> str:
    words = WORD_RE.findall(text)
    if len(words) <= max_words:
        return text
    kept = words[:max_words]
    return " ".join(kept).rstrip(" ,;:") + "."


def compact_text(text: Any) -> str:
    if isinstance(text, list):
        text = "; ".join(str(item) for item in text if item is not None)
    elif text is None:
        text = ""
    else:
        text = str(text)
    text = THINK_BLOCK_RE.sub("", text)
    text = CODE_FENCE_RE.sub("", text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = PREFIX_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip("`\"' ")


def parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = compact_text(text)
    candidates = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def normalize_label(text: Any, valid_labels: set[str], default: str) -> str:
    raw = compact_text(text).lower()
    raw = raw.replace("-", "_").replace(" ", "_")
    raw = re.sub(r"[^a-z0-9_]", "", raw)
    if raw in valid_labels:
        return raw
    for label in valid_labels:
        if label in raw:
            return label
        if re.search(rf"\b{re.escape(label)}\b", raw):
            return label
    return default


def has_suspicious_text(text: str) -> bool:
    return any(pattern.search(text) for pattern in SUSPICIOUS_PATTERNS)


def clean_field_text(value: Any, fallback: str, max_words: int) -> str:
    cleaned = compact_text(value)
    if not cleaned or has_suspicious_text(cleaned):
        cleaned = fallback
    return truncate_words(cleaned, max_words)


def _extract_response_from_json(text: str) -> str:
    parsed = parse_json_object(text)
    if not parsed:
        return text
    for key in ("response_text", "response", "reply", "text"):
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def contains_overpraise(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in OVERPRAISE_TERMS)


def _extract_risk_keywords(text: str) -> set[str]:
    lowered = text.lower()
    labels = {label for label in RISK_LABELS if label in lowered}
    phrase_map = {
        "context_insensitivity": (
            "context insensitivity",
            "context insensitive",
            "audience",
            "setting",
        ),
        "strategy_inconsistency": (
            "strategy inconsistency",
            "inconsistent strategy",
            "mismatch",
        ),
        "over_coldness": (
            "over-coldness",
            "over coldness",
            "too cold",
            "coldness",
            "dismissive",
        ),
    }
    for label, phrases in phrase_map.items():
        if any(phrase in lowered for phrase in phrases):
            labels.add(label)
    return labels


def clean_response_text(value: Any, strategy: str) -> str:
    raw = compact_text(_extract_response_from_json(str(value or "")))
    cleaned = raw
    if (
        not cleaned
        or has_suspicious_text(cleaned)
        or "{" in cleaned
        or "}" in cleaned
        or "<think" in cleaned.lower()
    ):
        cleaned = DEFAULT_RESPONSE_BY_STRATEGY.get(strategy, DEFAULT_RESPONSE_BY_STRATEGY[DEFAULT_STRATEGY])
    if strategy in {"light_acknowledgment", "neutral_observation"} and contains_overpraise(cleaned):
        cleaned = DEFAULT_RESPONSE_BY_STRATEGY[strategy]
    return truncate_words(cleaned, MAX_WORDS["response_text"])


def clean_understanding(parsed: dict[str, Any] | None) -> dict[str, str]:
    parsed = parsed or {}
    speaker_intention = clean_field_text(
        parsed.get("speaker_intention"),
        DEFAULT_SPEAKER_INTENTION,
        MAX_WORDS["speaker_intention"],
    )
    desired_feedback = clean_field_text(
        parsed.get("desired_feedback"),
        DEFAULT_DESIRED_FEEDBACK,
        MAX_WORDS["desired_feedback"],
    )
    risk_assessment = ensure_risk_assessment(parsed.get("risk_assessment"))
    return {
        "speaker_intention": speaker_intention,
        "desired_feedback": desired_feedback,
        "risk_assessment": risk_assessment,
    }


def ensure_risk_assessment(value: Any) -> str:
    text = clean_field_text(value, DEFAULT_RISK_ASSESSMENT, MAX_WORDS["risk_assessment"])
    risk_keywords = _extract_risk_keywords(text)
    if not risk_keywords or len(risk_keywords) > 3:
        text = DEFAULT_RISK_ASSESSMENT
    return truncate_words(text, MAX_WORDS["risk_assessment"])


def safe_mechanism(text: Any, valid_labels: set[str]) -> str:
    return normalize_label(text, valid_labels, DEFAULT_MECHANISM)


def safe_strategy(text: Any, valid_labels: set[str]) -> str:
    return normalize_label(text, valid_labels, DEFAULT_STRATEGY)
