from __future__ import annotations

from typing import Any

from .postprocess import has_suspicious_text, word_count
from .schemas import (
    INPUT_FIELDS,
    MAX_WORDS,
    OUTPUT_FIELDS,
    VALID_BRAGGING_MECHANISMS,
    VALID_RESPONSE_STRATEGIES,
)


def validate_input_row(row: dict[str, Any], line_number: int | None = None) -> None:
    missing = [field for field in INPUT_FIELDS if field not in row]
    if missing:
        prefix = f"line {line_number}: " if line_number is not None else ""
        raise ValueError(f"{prefix}input row missing fields: {missing}")
    if not isinstance(row.get("episode_id"), str) or not row["episode_id"].strip():
        prefix = f"line {line_number}: " if line_number is not None else ""
        raise ValueError(f"{prefix}input row has invalid episode_id")


def validate_output(output_row: dict[str, Any], input_row: dict[str, Any]) -> None:
    fields = set(output_row)
    expected = set(OUTPUT_FIELDS)
    if fields != expected:
        extra = sorted(fields - expected)
        missing = sorted(expected - fields)
        raise ValueError(f"output field mismatch; missing={missing}, extra={extra}")
    if output_row["episode_id"] != input_row["episode_id"]:
        raise ValueError("episode_id must be copied from input")
    if output_row["bragging_mechanism"] not in VALID_BRAGGING_MECHANISMS:
        raise ValueError("invalid bragging_mechanism")
    if output_row["response_strategy"] not in VALID_RESPONSE_STRATEGIES:
        raise ValueError("invalid response_strategy")
    for field in ("speaker_intention", "desired_feedback", "risk_assessment"):
        value = output_row[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        if word_count(value) > MAX_WORDS[field]:
            raise ValueError(f"{field} exceeds {MAX_WORDS[field]} words")
        if has_suspicious_text(value):
            raise ValueError(f"{field} contains suspicious text")
    response_text = output_row["response_text"]
    if not isinstance(response_text, str):
        raise ValueError("response_text must be a string")
    if output_row["response_strategy"] != "no_response" and not response_text.strip():
        raise ValueError("response_text must be non-empty unless strategy is no_response")
    if word_count(response_text) > MAX_WORDS["response_text"]:
        raise ValueError("response_text exceeds word limit")
    if has_suspicious_text(response_text):
        raise ValueError("response_text contains suspicious text")
