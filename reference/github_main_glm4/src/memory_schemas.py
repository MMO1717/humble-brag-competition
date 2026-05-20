from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_MEMORY_STATUS = {"static", "candidate", "active", "deprecated"}

VALID_MEMORY_TYPES = {
    "label_confusion_memory",
    "implicit_intent_memory",
    "desired_feedback_memory",
    "risk_pattern_memory",
    "strategy_policy_memory",
    "style_adaptation_memory",
    "response_template_memory",
    "negative_memory",
    "evaluator_preference_memory",
}

VALID_TARGET_SKILLS = {
    "MechanismSkill",
    "UnderstandingSkill",
    "RiskSkill",
    "StrategySkill",
    "ResponseSkill",
}

SKILL_MEMORY_TYPES = {
    "MechanismSkill": {
        "label_confusion_memory",
        "implicit_intent_memory",
        "negative_memory",
        "evaluator_preference_memory",
    },
    "UnderstandingSkill": {
        "implicit_intent_memory",
        "desired_feedback_memory",
    },
    "RiskSkill": {
        "risk_pattern_memory",
        "negative_memory",
    },
    "StrategySkill": {
        "strategy_policy_memory",
        "risk_pattern_memory",
        "evaluator_preference_memory",
    },
    "ResponseSkill": {
        "style_adaptation_memory",
        "response_template_memory",
        "negative_memory",
        "evaluator_preference_memory",
    },
}


@dataclass
class MemoryItem:
    memory_id: str
    status: str
    memory_type: str
    target_skills: list[str]
    content_en: str
    content_zh: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)
    negative_conditions: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    version: int = 1
    created_at: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryItem":
        return cls(
            memory_id=str(data.get("memory_id", "")).strip(),
            status=str(data.get("status", "")).strip(),
            memory_type=str(data.get("memory_type", "")).strip(),
            target_skills=[str(item) for item in data.get("target_skills", [])],
            content_en=str(data.get("content_en", "")).strip(),
            content_zh=str(data.get("content_zh", "")).strip(),
            conditions=data.get("conditions") if isinstance(data.get("conditions"), dict) else {},
            negative_conditions=data.get("negative_conditions")
            if isinstance(data.get("negative_conditions"), dict)
            else {},
            source=data.get("source") if isinstance(data.get("source"), dict) else {},
            confidence=float(data.get("confidence", 0.5) or 0.5),
            version=int(data.get("version", 1) or 1),
            created_at=str(data.get("created_at", "")).strip(),
            notes=str(data.get("notes", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "status": self.status,
            "memory_type": self.memory_type,
            "target_skills": self.target_skills,
            "content_en": self.content_en,
            "content_zh": self.content_zh,
            "conditions": self.conditions,
            "negative_conditions": self.negative_conditions,
            "source": self.source,
            "confidence": self.confidence,
            "version": self.version,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def validate_memory_item(item: MemoryItem) -> list[str]:
    errors: list[str] = []
    if not item.memory_id:
        errors.append("memory_id is required")
    if item.status not in VALID_MEMORY_STATUS:
        errors.append(f"invalid status: {item.status}")
    if item.memory_type not in VALID_MEMORY_TYPES:
        errors.append(f"invalid memory_type: {item.memory_type}")
    if not item.target_skills:
        errors.append("target_skills is required")
    invalid_skills = [skill for skill in item.target_skills if skill not in VALID_TARGET_SKILLS]
    if invalid_skills:
        errors.append(f"invalid target_skills: {invalid_skills}")
    if not item.content_en:
        errors.append("content_en is required")
    if not isinstance(item.source, dict):
        errors.append("source must be an object")
    if "episode_id" in item.content_en.lower():
        errors.append("content_en should not mention episode_id")
    return errors
