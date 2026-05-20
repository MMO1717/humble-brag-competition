from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def mechanism_examples(train_path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = load_jsonl(train_path)
    if limit is not None:
        rows = rows[:limit]
    return [
        {
            "speaker_post": row.get("speaker_post", ""),
            "platform": row.get("platform", ""),
            "relationship": row.get("relationship", ""),
            "agent_role": row.get("agent_role", ""),
            "interaction_goal": row.get("interaction_goal", ""),
            "bragging_mechanism": row.get("bragging_mechanism", ""),
        }
        for row in rows
    ]


def strategy_examples(train_path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = load_jsonl(train_path)
    if limit is not None:
        rows = rows[:limit]
    return [
        {
            "speaker_post": row.get("speaker_post", ""),
            "platform": row.get("platform", ""),
            "relationship": row.get("relationship", ""),
            "agent_role": row.get("agent_role", ""),
            "interaction_goal": row.get("interaction_goal", ""),
            "bragging_mechanism": row.get("bragging_mechanism", ""),
            "speaker_intention": row.get("speaker_intention", ""),
            "desired_feedback": row.get("desired_feedback", ""),
            "response_strategy": row.get("response_strategy", ""),
        }
        for row in rows
    ]
