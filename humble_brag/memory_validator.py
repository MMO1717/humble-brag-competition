from __future__ import annotations

from typing import Any

from .memory_schemas import MemoryItem, validate_memory_item
from .memory_retriever import _tokens


def _jaccard_text(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def has_dev_leakage(item: MemoryItem) -> bool:
    text = f"{item.content_en} {item.content_zh}".lower()
    if "dev_seed_" in text or "train_seed_" in text:
        return True
    source_ids = item.source.get("episode_ids", []) if isinstance(item.source, dict) else []
    return any(str(episode_id) in text for episode_id in source_ids)


def validate_candidate_memory(
    item: MemoryItem,
    active_items: list[MemoryItem],
) -> tuple[bool, list[str], list[str]]:
    errors = validate_memory_item(item)
    warnings: list[str] = []

    if item.status != "candidate":
        errors.append("candidate memory must use status=candidate")
    if has_dev_leakage(item):
        errors.append("candidate appears to contain concrete dev/train episode leakage")

    for active in active_items:
        similarity = _jaccard_text(item.content_en, active.content_en)
        if similarity >= 0.75:
            warnings.append(f"possible duplicate with {active.memory_id}, similarity={similarity:.2f}")

    if item.memory_type == "evaluator_preference_memory":
        warnings.append("evaluator_preference_memory requires human approval before activation")

    return not errors, errors, warnings


def review_candidates(
    candidates: list[MemoryItem],
    active_items: list[MemoryItem],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in candidates:
        ok, errors, warnings = validate_candidate_memory(item, active_items)
        row = item.to_dict()
        row["review"] = {
            "schema_ok": ok,
            "errors": errors,
            "warnings": warnings,
            "recommended_action": "keep_candidate" if ok else "reject",
        }
        rows.append(row)
    return rows
