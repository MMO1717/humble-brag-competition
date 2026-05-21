from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import load_jsonl, write_jsonl


def _active_memory_ids(rows: list[dict[str, Any]]) -> set[str]:
    return {str(row.get("memory_id", "")).strip() for row in rows if row.get("memory_id")}


def promote_memory_ids(memory_dir: Path, memory_ids: list[str]) -> dict[str, int]:
    candidate_path = memory_dir / "candidate" / "memory_candidates.jsonl"
    active_path = memory_dir / "active" / "memory.jsonl"
    if not memory_ids or not candidate_path.exists():
        return {"promoted": 0, "remaining_candidates": 0}

    wanted = set(memory_ids)
    candidates = load_jsonl(candidate_path)
    active = load_jsonl(active_path) if active_path.exists() else []
    remaining = []
    promoted = 0

    for row in candidates:
        if row.get("memory_id") in wanted and row.get("review", {}).get("schema_ok"):
            promoted_row = {key: value for key, value in row.items() if key != "review"}
            promoted_row["status"] = "active"
            active.append(promoted_row)
            promoted += 1
        else:
            remaining.append(row)

    write_jsonl(active_path, active)
    write_jsonl(candidate_path, remaining)
    return {"promoted": promoted, "remaining_candidates": len(remaining)}


def auto_promote_candidate_memories(
    *,
    memory_dir: Path,
    allowed_memory_types: list[str],
    min_confidence: float,
    require_no_warnings: bool,
    require_conditions: bool,
) -> dict[str, Any]:
    candidate_path = memory_dir / "candidate" / "memory_candidates.jsonl"
    active_path = memory_dir / "active" / "memory.jsonl"
    if not candidate_path.exists():
        return {"promoted": 0, "remaining_candidates": 0, "skipped": []}

    allowed_types = set(allowed_memory_types)
    candidates = load_jsonl(candidate_path)
    active = load_jsonl(active_path) if active_path.exists() else []
    existing_ids = _active_memory_ids(active)

    remaining: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    promoted = 0

    for row in candidates:
        memory_id = str(row.get("memory_id", "")).strip()
        review = row.get("review") if isinstance(row.get("review"), dict) else {}
        warnings = review.get("warnings", []) if isinstance(review.get("warnings"), list) else []
        confidence = float(row.get("confidence", 0.0) or 0.0)
        memory_type = str(row.get("memory_type", "")).strip()
        conditions = row.get("conditions") if isinstance(row.get("conditions"), dict) else {}

        reason = ""
        if not memory_id:
            reason = "missing_memory_id"
        elif memory_id in existing_ids:
            reason = "already_active"
        elif review.get("schema_ok") is not True:
            reason = "schema_not_ok"
        elif allowed_types and memory_type not in allowed_types:
            reason = "memory_type_not_allowed"
        elif confidence < min_confidence:
            reason = "confidence_too_low"
        elif require_no_warnings and warnings:
            reason = "has_review_warnings"
        elif require_conditions and not conditions:
            reason = "missing_conditions"

        if reason:
            remaining.append(row)
            skipped.append({"memory_id": memory_id, "reason": reason})
            continue

        promoted_row = {key: value for key, value in row.items() if key != "review"}
        promoted_row["status"] = "active"
        active.append(promoted_row)
        existing_ids.add(memory_id)
        promoted += 1

    write_jsonl(active_path, active)
    write_jsonl(candidate_path, remaining)
    return {
        "promoted": promoted,
        "remaining_candidates": len(remaining),
        "skipped": skipped,
        "active_path": str(active_path),
        "candidate_path": str(candidate_path),
    }
