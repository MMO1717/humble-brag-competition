from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .memory_schemas import MemoryItem, validate_memory_item


STATIC_MEMORY_FILES = {
    "label_schema": "label_schema.md",
    "bragging_mechanism_guide": "bragging_mechanism_guide.md",
    "response_strategy_guide": "response_strategy_guide.md",
    "risk_policy": "risk_policy.md",
    "platform_relationship_style": "platform_relationship_style.md",
}

ENGLISH_SECTION_TITLE = "## English Prompt Notes"


def _extract_english_prompt_notes(text: str) -> str:
    """只抽取静态知识中可注入英文 prompt 的段落。"""
    start = text.find(ENGLISH_SECTION_TITLE)
    if start == -1:
        return ""
    body = text[start + len(ENGLISH_SECTION_TITLE) :]
    next_heading = body.find("\n## ")
    if next_heading != -1:
        body = body[:next_heading]
    return body.strip()


def load_static_memory_notes(static_dir: Path, enabled: bool = True) -> dict[str, str]:
    notes = {key: "" for key in STATIC_MEMORY_FILES}
    if not enabled:
        return notes

    for key, filename in STATIC_MEMORY_FILES.items():
        path = static_dir / filename
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"静态 Memory 文件不存在，跳过: {path}")
            continue
        except OSError as exc:
            print(f"静态 Memory 文件读取失败，跳过: {path} ({exc})")
            continue
        notes[key] = _extract_english_prompt_notes(text)
    return notes


def _load_memory_jsonl(path: Path, expected_status: str) -> list[MemoryItem]:
    if not path.exists():
        return []

    items: list[MemoryItem] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"Memory 解析失败，跳过: {path}:{line_number} ({exc})")
            continue
        if not isinstance(data, dict):
            print(f"Memory 行不是 JSON object，跳过: {path}:{line_number}")
            continue
        review = data.get("review")
        if expected_status == "candidate" and isinstance(review, dict) and review.get("schema_ok") is False:
            print(f"Candidate memory 未通过 review，跳过注入: {path}:{line_number}")
            continue
        item = MemoryItem.from_dict(data)
        if not item.status:
            item.status = expected_status
        errors = validate_memory_item(item)
        if errors:
            print(f"Memory schema 不合法，跳过: {item.memory_id or path.name}:{errors}")
            continue
        items.append(item)
    return items


def _static_notes_as_memory(static_notes: dict[str, str]) -> list[MemoryItem]:
    items: list[MemoryItem] = []
    mapping = {
        "bragging_mechanism_guide": ("static_bragging_mechanism_guide", "label_confusion_memory", ["MechanismSkill"]),
        "response_strategy_guide": ("static_response_strategy_guide", "strategy_policy_memory", ["StrategySkill", "ResponseSkill"]),
        "risk_policy": ("static_risk_policy", "risk_pattern_memory", ["RiskSkill", "ResponseSkill"]),
        "platform_relationship_style": ("static_platform_relationship_style", "style_adaptation_memory", ["StrategySkill", "ResponseSkill"]),
        "label_schema": ("static_label_schema", "negative_memory", ["MechanismSkill", "ResponseSkill"]),
    }
    for key, (memory_id, memory_type, target_skills) in mapping.items():
        content = static_notes.get(key, "").strip()
        if not content:
            continue
        items.append(
            MemoryItem(
                memory_id=memory_id,
                status="static",
                memory_type=memory_type,
                target_skills=target_skills,
                content_en=content,
                source={"kind": "static_memory", "key": key},
                confidence=0.6,
                version=1,
                notes="Loaded from static memory English Prompt Notes.",
            )
        )
    return items


class MemoryStore:
    def __init__(
        self,
        static_notes: dict[str, str],
        static_items: list[MemoryItem],
        active_items: list[MemoryItem],
        candidate_items: list[MemoryItem],
    ) -> None:
        self.static_wiki = static_notes
        self.static_notes = static_notes
        self.static_items = static_items
        self.active_items = active_items
        self.candidate_items = candidate_items

    def items_for_mode(self, mode: str) -> list[MemoryItem]:
        if mode == "no_memory":
            return []
        if mode == "static_only":
            return self.static_items
        if mode == "active_plus_candidate":
            return self.active_items + self.candidate_items
        return self.active_items


def load_memory_store(cfg: Any) -> MemoryStore:
    memory_dir = Path(getattr(cfg, "MEMORY_DIR"))
    static_dir = memory_dir / "static"
    static_enabled = getattr(cfg, "USE_STATIC_MEMORY", True)

    static_notes = load_static_memory_notes(static_dir, enabled=static_enabled)

    static_items = _static_notes_as_memory(static_notes)
    active_items = _load_memory_jsonl(memory_dir / "active" / "memory.jsonl", "active")
    candidate_items = _load_memory_jsonl(memory_dir / "candidate" / "memory_candidates.jsonl", "candidate")

    return MemoryStore(
        static_notes=static_notes,
        static_items=static_items,
        active_items=active_items,
        candidate_items=candidate_items,
    )
