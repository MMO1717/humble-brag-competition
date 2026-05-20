from __future__ import annotations

import re
from typing import Any

from .memory_loader import MemoryStore
from .memory_schemas import MemoryItem, SKILL_MEMORY_TYPES


TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: Any) -> set[str]:
    return set(TOKEN_RE.findall(str(text or "").lower()))


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


class MemoryRetriever:
    """按 skill 和当前样本检索少量相关 memory，避免把所有记忆塞进 prompt。"""

    def __init__(
        self,
        store: MemoryStore,
        mode: str,
        top_k_per_skill: int,
        max_chars_per_skill: int,
        target_skills: list[str],
    ) -> None:
        self.store = store
        self.mode = mode
        self.top_k_per_skill = max(0, int(top_k_per_skill))
        self.max_chars_per_skill = max(0, int(max_chars_per_skill))
        self.target_skills = set(target_skills)

    def retrieve(
        self,
        row: dict[str, Any],
        skill_name: str,
        state: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if self.mode == "no_memory" or self.top_k_per_skill <= 0:
            return []
        if self.target_skills and skill_name not in self.target_skills:
            return []

        candidates = self.store.items_for_mode(self.mode)
        scored: list[tuple[float, MemoryItem]] = []
        for item in candidates:
            if skill_name not in item.target_skills:
                continue
            if item.memory_type not in SKILL_MEMORY_TYPES.get(skill_name, set()):
                continue
            if self._blocked(row, item):
                continue
            score = self._score(row, item)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        selected: list[dict[str, Any]] = []
        used_chars = 0
        for score, item in scored:
            if len(selected) >= self.top_k_per_skill:
                break
            content = item.content_en.strip()
            if not content:
                continue
            next_chars = used_chars + len(content)
            if self.max_chars_per_skill and next_chars > self.max_chars_per_skill:
                continue
            used_chars = next_chars
            selected.append(
                {
                    "memory_id": item.memory_id,
                    "memory_type": item.memory_type,
                    "status": item.status,
                    "target_skills": item.target_skills,
                    "content_en": item.content_en,
                    "confidence": item.confidence,
                    "score": round(score, 4),
                    "source": item.source,
                }
            )
        return selected

    def _blocked(self, row: dict[str, Any], item: MemoryItem) -> bool:
        post = str(row.get("speaker_post", ""))
        negative = item.negative_conditions or {}
        if _contains_any(post, _as_list(negative.get("speaker_post_keywords"))):
            return True
        return False

    def _score(self, row: dict[str, Any], item: MemoryItem) -> float:
        conditions = item.conditions or {}
        score = 0.1 + float(item.confidence)

        platform_conditions = _as_list(conditions.get("platform"))
        if platform_conditions:
            if row.get("platform") not in platform_conditions:
                return 0.0
            score += 0.5

        relationship_conditions = _as_list(conditions.get("relationship"))
        if relationship_conditions:
            if row.get("relationship") not in relationship_conditions:
                return 0.0
            score += 0.3

        goal_conditions = _as_list(conditions.get("interaction_goal_contains"))
        goal = str(row.get("interaction_goal", ""))
        if goal_conditions:
            if not _contains_any(goal, goal_conditions):
                return 0.0
            score += 0.3

        keyword_conditions = _as_list(conditions.get("speaker_post_keywords"))
        post = str(row.get("speaker_post", ""))
        if keyword_conditions:
            if not _contains_any(post, keyword_conditions):
                return 0.0
            score += 0.8
        else:
            overlap = _tokens(post) & _tokens(item.content_en)
            score += min(len(overlap) * 0.03, 0.3)

        if item.status == "active":
            score += 0.2
        elif item.status == "candidate":
            score -= 0.2
        return score


def format_memory_snippets(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return ""
    lines: list[str] = []
    for index, item in enumerate(memories, start=1):
        lines.append(
            f"{index}. [{item.get('memory_type')}; {item.get('memory_id')}] "
            f"{item.get('content_en')}"
        )
    return "\n".join(lines)
