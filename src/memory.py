from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .io_utils import load_jsonl, write_jsonl
from .schemas import RISK_LABELS, VALID_BRAGGING_MECHANISMS, VALID_RESPONSE_STRATEGIES


MEMORY_TYPES = {
    "mechanism_rule",
    "confusion_rule",
    "strategy_policy",
    "scenario_policy",
    "risk_pattern",
    "response_style_card",
    "anti_pattern",
}
MEMORY_FIELDS = (
    "memory_id",
    "status",
    "memory_type",
    "target_skills",
    "target_labels",
    "content",
    "conditions",
    "negative_conditions",
    "confidence",
    "priority",
    "source",
)
TOKEN_RE = re.compile(r"[a-z0-9_]+")
ACTIVE_MEMORY_STATUSES = {"active", "approved"}
MEMORY_ROUTER_MODES = {"baseline", "function", "llm_rerank"}

SKILL_MEMORY_TYPES = {
    "MechanismSkill": {"mechanism_rule", "confusion_rule"},
    "UnderstandingSkill": {"scenario_policy"},
    "StrategySkill": {"strategy_policy", "scenario_policy", "confusion_rule"},
    "RiskSkill": {"risk_pattern", "anti_pattern"},
    "ResponseSkill": {
        "response_style_card",
        "scenario_policy",
        "strategy_policy",
        "anti_pattern",
    },
}

QUERY_CONDITION_KEYS = {
    "platform",
    "relationship",
    "agent_role",
    "interaction_goal",
    "interaction_goal_pattern",
    "bragging_mechanism",
    "mechanism",
    "response_strategy",
    "strategy",
    "speaker_post_keywords",
    "post_keywords",
    "speaker_post_cues",
    "positive_cues",
    "risk_label",
    "risk_labels",
}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _tokens(value: Any) -> set[str]:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return set(TOKEN_RE.findall(str(value or "").lower()))


@dataclass(frozen=True)
class MemoryItem:
    """统一的结构化记忆。"""

    memory_id: str
    status: str
    memory_type: str
    target_skills: list[str]
    target_labels: list[str]
    content: str
    conditions: dict[str, Any]
    negative_conditions: dict[str, Any]
    confidence: float
    priority: float
    source: str

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "MemoryItem":
        missing = [field for field in MEMORY_FIELDS if field not in row]
        if missing:
            raise ValueError(f"memory 缺少字段：{missing}")
        memory_type = str(row["memory_type"])
        if memory_type not in MEMORY_TYPES:
            raise ValueError(f"不支持的 memory_type：{memory_type}")
        return cls(
            memory_id=str(row["memory_id"]).strip(),
            status=str(row["status"]).strip(),
            memory_type=memory_type,
            target_skills=_string_list(row["target_skills"]),
            target_labels=_string_list(row["target_labels"]),
            content=str(row["content"]).strip(),
            conditions=dict(row["conditions"] or {}),
            negative_conditions=dict(row["negative_conditions"] or {}),
            confidence=max(0.0, min(1.0, float(row["confidence"]))),
            priority=float(row["priority"]),
            source=str(row["source"]).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_memories(
    memory_path: Path,
    generated_path: Path | None = None,
    use_generated: bool = False,
) -> list[MemoryItem]:
    """加载内置记忆，并按需加载生成记忆。"""
    paths = [memory_path]
    if use_generated and generated_path and generated_path.exists():
        paths.append(generated_path)
    items: list[MemoryItem] = []
    seen: set[str] = set()
    for path in paths:
        if not path.exists():
            print(
                f"[WARN] memory 文件不存在，已跳过：{path}",
                flush=True,
            )
            continue
        for row in load_jsonl(path):
            item = MemoryItem.from_dict(row)
            if item.memory_id and item.memory_id not in seen:
                items.append(item)
                seen.add(item.memory_id)
    return items


def _condition_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        result: list[str] = []
        for nested in value.values():
            result.extend(_condition_values(nested))
        return result
    if isinstance(value, list):
        return [str(item).lower() for item in value]
    if value is None:
        return []
    return [str(value).lower()]


def _row_value(
    key: str,
    row: dict[str, Any],
    state: dict[str, Any],
) -> Any:
    aliases = {
        "mechanism": "bragging_mechanism",
        "strategy": "response_strategy",
        "post": "speaker_post",
        "risk_label": "risk_labels",
    }
    actual = aliases.get(key, key)
    return state.get(actual, row.get(actual))


def _condition_match(
    conditions: dict[str, Any],
    row: dict[str, Any],
    state: dict[str, Any],
) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    recognized = 0
    post = str(row.get("speaker_post", "")).lower()
    for key, expected in conditions.items():
        if key not in QUERY_CONDITION_KEYS:
            continue
        recognized += 1
        values = _condition_values(expected)
        if not values:
            continue
        if key in {
            "speaker_post_keywords",
            "post_keywords",
            "speaker_post_cues",
            "positive_cues",
        }:
            if not any(value in post for value in values):
                return False, evidence
            evidence.append("post_cue")
            continue
        if key == "interaction_goal_pattern":
            actual_text = str(row.get("interaction_goal", "")).lower()
            if not any(value in actual_text for value in values):
                return False, evidence
            evidence.append("interaction_goal_pattern")
            continue
        else:
            actual = _row_value(key, row, state)
        actual_values = {
            str(item).lower()
            for item in (actual if isinstance(actual, list) else [actual])
            if item is not None
        }
        if actual_values and actual_values.intersection(values):
            evidence.append(f"{key}={next(iter(actual_values.intersection(values)))}")
        else:
            return False, evidence
    if not conditions:
        return True, evidence
    return recognized > 0 and bool(evidence), evidence


def _negative_match(
    conditions: dict[str, Any],
    row: dict[str, Any],
    state: dict[str, Any],
) -> bool:
    post = str(row.get("speaker_post", "")).lower()
    results: list[bool] = []
    for key, expected in conditions.items():
        values = _condition_values(expected)
        if not values:
            continue
        if key in {
            "speaker_post_keywords",
            "negative_speaker_post_keywords",
            "negative_cues",
        }:
            results.append(any(value in post for value in values))
            continue
        actual = _row_value(key, row, state)
        if actual is None:
            continue
        actual_values = {
            str(item).lower()
            for item in (actual if isinstance(actual, list) else [actual])
        }
        results.append(bool(actual_values.intersection(values)))
    return bool(results) and all(results)


class MemoryRetriever:
    """按 Skill、条件和文本相关性检索统一记忆。"""

    def __init__(
        self,
        items: Iterable[MemoryItem],
        top_k_by_skill: dict[str, int],
        max_chars_by_skill: dict[str, int],
        min_score_by_skill: dict[str, float],
        router_mode: str = "function",
    ) -> None:
        self.items = list(items)
        self.top_k_by_skill = top_k_by_skill
        self.max_chars_by_skill = max_chars_by_skill
        self.min_score_by_skill = min_score_by_skill
        if router_mode not in MEMORY_ROUTER_MODES:
            raise ValueError(
                "MEMORY_ROUTER_MODE must be one of "
                f"{', '.join(sorted(MEMORY_ROUTER_MODES))}"
            )
        self.router_mode = router_mode

    def get_mechanism_knowledge(self) -> list[dict[str, Any]]:
        """返回分类前固定可见的机制规则和机制混淆规则。"""
        result: list[dict[str, Any]] = []
        for item in self.items:
            if "MechanismSkill" not in item.target_skills:
                continue
            if item.memory_type not in {"mechanism_rule", "confusion_rule"}:
                continue
            if not self._labels_compatible(item, "MechanismSkill"):
                continue
            result.append(item.to_dict())
        result.sort(
            key=lambda item: (
                item["memory_type"] != "mechanism_rule",
                -float(item["priority"]),
                item["memory_id"],
            )
        )
        return result

    def retrieve(
        self,
        row: dict[str, Any],
        skill_name: str,
        state: dict[str, Any] | None = None,
        *,
        candidate_limit: int | None = None,
        max_chars_override: int | None = None,
    ) -> list[dict[str, Any]]:
        current_state = state or {}
        query_tokens = _tokens(
            {
                "row": row,
                "mechanism": current_state.get("bragging_mechanism"),
                "strategy": current_state.get("response_strategy"),
            }
        )
        scored: list[tuple[float, MemoryItem, list[str]]] = []
        for item in self.items:
            if not self._status_allowed(item):
                continue
            if skill_name not in item.target_skills:
                continue
            if item.memory_type not in SKILL_MEMORY_TYPES.get(skill_name, set()):
                continue
            if not self._labels_compatible(item, skill_name):
                continue
            if _negative_match(item.negative_conditions, row, current_state):
                continue
            conditions_match, evidence = _condition_match(
                item.conditions, row, current_state
            )
            if item.conditions and not conditions_match:
                continue
            if not self._route_allowed(
                item,
                skill_name,
                current_state,
                evidence,
            ):
                continue
            memory_tokens = _tokens(
                {
                    "labels": item.target_labels,
                    "content": item.content,
                    "conditions": item.conditions,
                }
            )
            lexical = (
                len(query_tokens & memory_tokens) / len(query_tokens | memory_tokens)
                if query_tokens and memory_tokens
                else 0.0
            )
            condition_bonus = min(0.45, 0.12 * len(evidence))
            score = (
                0.35 * item.confidence
                + 0.04 * max(0.0, min(item.priority, 10.0))
                + lexical
                + condition_bonus
            )
            minimum = float(self.min_score_by_skill.get(skill_name, 0.2))
            if score >= minimum and (evidence or lexical >= 0.03 or not item.conditions):
                scored.append((score, item, evidence))
        scored.sort(key=lambda value: value[0], reverse=True)

        limit = (
            int(candidate_limit)
            if candidate_limit is not None
            else int(self.top_k_by_skill.get(skill_name, 3))
        )
        max_chars = (
            int(max_chars_override)
            if max_chars_override is not None
            else int(self.max_chars_by_skill.get(skill_name, 1800))
        )
        result: list[dict[str, Any]] = []
        used_chars = 0
        for score, item, evidence in scored[:limit]:
            payload = item.to_dict()
            payload["score"] = round(score, 4)
            payload["match_evidence"] = evidence
            serialized_size = len(json.dumps(payload, ensure_ascii=False))
            if result and used_chars + serialized_size > max_chars:
                break
            result.append(payload)
            used_chars += serialized_size
        return result

    def _status_allowed(self, item: MemoryItem) -> bool:
        if self.router_mode == "baseline":
            return True
        return item.status.strip().lower() in ACTIVE_MEMORY_STATUSES

    def _route_allowed(
        self,
        item: MemoryItem,
        skill_name: str,
        state: dict[str, Any],
        evidence: list[str],
    ) -> bool:
        if self.router_mode == "baseline":
            return self._baseline_route_allowed(item, skill_name, state)
        if self.router_mode == "llm_rerank":
            # Reserved for A/B experiments. Until an ID-only LLM reranker is
            # wired in, use the deterministic route so no extra calls are added.
            return self._function_route_allowed(item, skill_name, state, evidence)
        return self._function_route_allowed(item, skill_name, state, evidence)

    @staticmethod
    def _baseline_route_allowed(
        item: MemoryItem,
        skill_name: str,
        state: dict[str, Any],
    ) -> bool:
        return not (
            skill_name == "ResponseSkill"
            and item.memory_type == "strategy_policy"
            and state.get("response_strategy") not in item.target_labels
        )

    def _function_route_allowed(
        self,
        item: MemoryItem,
        skill_name: str,
        state: dict[str, Any],
        evidence: list[str],
    ) -> bool:
        if skill_name != "ResponseSkill":
            return self._baseline_route_allowed(item, skill_name, state)

        strategy = str(state.get("response_strategy") or "").strip()
        if item.memory_type in {
            "strategy_policy",
            "scenario_policy",
            "response_style_card",
        }:
            return self._strategy_label_matches(item, strategy)

        if item.memory_type == "anti_pattern":
            return self._anti_pattern_matches_context(item, state, evidence)

        return True

    @staticmethod
    def _strategy_label_matches(item: MemoryItem, strategy: str) -> bool:
        if not strategy:
            return False
        labels = set(item.target_labels)
        if not labels:
            return False
        return strategy in labels

    @staticmethod
    def _anti_pattern_matches_context(
        item: MemoryItem,
        state: dict[str, Any],
        evidence: list[str],
    ) -> bool:
        if not item.conditions:
            return False
        risk_labels = {
            str(label).lower()
            for label in state.get("risk_labels", [])
            if str(label).strip()
        }
        if risk_labels and risk_labels.intersection(
            str(label).lower() for label in item.target_labels
        ):
            return True
        route_evidence_prefixes = (
            "response_strategy=",
            "strategy=",
            "bragging_mechanism=",
            "mechanism=",
            "relationship=",
            "platform=",
            "agent_role=",
            "interaction_goal_pattern",
            "risk_label=",
            "risk_labels=",
        )
        return any(clue.startswith(route_evidence_prefixes) for clue in evidence)

    @staticmethod
    def _labels_compatible(item: MemoryItem, skill_name: str) -> bool:
        labels = set(item.target_labels)
        if item.memory_type == "mechanism_rule":
            return bool(labels) and labels <= VALID_BRAGGING_MECHANISMS
        if item.memory_type == "confusion_rule":
            if skill_name == "MechanismSkill":
                return bool(labels) and labels <= VALID_BRAGGING_MECHANISMS
            if skill_name == "StrategySkill":
                return bool(labels) and labels <= VALID_RESPONSE_STRATEGIES
        if item.memory_type == "strategy_policy":
            return bool(labels) and labels <= VALID_RESPONSE_STRATEGIES
        if item.memory_type == "risk_pattern":
            return bool(labels) and labels <= set(RISK_LABELS)
        return True


def format_memory_snippets(
    memories: list[dict[str, Any]],
    max_chars: int = 2400,
) -> str:
    """将检索结果压缩为可注入提示词的文本。"""
    lines: list[str] = []
    for memory in memories:
        labels = ", ".join(memory.get("target_labels", [])) or "通用"
        line = (
            f"- [{memory.get('memory_type')}] {memory.get('content')} "
            f"(labels: {labels}; score: {memory.get('score', 0)})"
        )
        if lines and len("\n".join(lines + [line])) > max_chars:
            break
        lines.append(line)
    return "\n".join(lines)


def save_generated_memories(
    path: Path,
    items: list[dict[str, Any]],
) -> int:
    """校验后追加生成记忆，并按 memory_id 去重。"""
    existing = load_jsonl(path) if path.exists() else []
    by_id = {
        str(row.get("memory_id")): MemoryItem.from_dict(row).to_dict()
        for row in existing
    }
    for row in items:
        item = MemoryItem.from_dict(row)
        by_id[item.memory_id] = item.to_dict()
    write_jsonl(path, list(by_id.values()))
    return len(items)
