from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .io_utils import load_jsonl, write_jsonl
from .memory_loader import load_memory_store
from .memory_schemas import MemoryItem
from .memory_validator import review_candidates


def _safe_id_part(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:32] or "memory"


def _new_memory_id(run_id: str, index: int) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"mem_{timestamp}_{_safe_id_part(run_id)}_{index:03d}"


def _candidate_prompt(cases: list[dict[str, Any]], max_items: int) -> list[dict[str, str]]:
    compact_cases = []
    for case in cases:
        compact_cases.append(
            {
                "scores": case["scores"],
                "speaker_post": case["input"].get("speaker_post", ""),
                "context": {
                    "platform": case["input"].get("platform", ""),
                    "relationship": case["input"].get("relationship", ""),
                    "agent_role": case["input"].get("agent_role", ""),
                    "interaction_goal": case["input"].get("interaction_goal", ""),
                },
                "prediction": {
                    "bragging_mechanism": case["prediction"].get("bragging_mechanism"),
                    "response_strategy": case["prediction"].get("response_strategy"),
                    "risk_assessment": case["prediction"].get("risk_assessment"),
                    "response_text": case["prediction"].get("response_text"),
                },
                "gold": {
                    "bragging_mechanism": case["gold"].get("gold_bragging_mechanism"),
                    "risk_labels": case["gold"].get("gold_risk_labels", []),
                    "preferred_strategy": case["gold"].get("preferred_strategy"),
                    "acceptable_strategies": case["gold"].get("acceptable_strategies", []),
                    "reference_response": case["gold"].get("reference_response"),
                },
            }
        )

    return [
        {
            "role": "system",
            "content": (
                "You propose generalized BRAG-Agent memory candidates. "
                "Do not memorize individual examples or exact gold answers. "
                "Return only a JSON array."
            ),
        },
        {
            "role": "user",
            "content": (
                "Create up to "
                f"{max_items} candidate memories from these error cases. "
                "Each memory must be an abstract rule, not a dev example answer. "
                "Allowed memory_type values: label_confusion_memory, implicit_intent_memory, "
                "desired_feedback_memory, risk_pattern_memory, strategy_policy_memory, "
                "style_adaptation_memory, response_template_memory, negative_memory, "
                "evaluator_preference_memory. "
                "Allowed target_skills: MechanismSkill, UnderstandingSkill, RiskSkill, "
                "StrategySkill, ResponseSkill. "
                "Return fields: memory_type, target_skills, content_en, content_zh, "
                "conditions, negative_conditions, confidence, notes.\n\n"
                f"{json.dumps(compact_cases, ensure_ascii=False)}"
            ),
        },
    ]


def _parse_candidates(text: str) -> list[dict[str, Any]]:
    cleaned = text.strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _fallback_candidates(cases: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    mechanism_errors = [case for case in cases if case["scores"].get("mechanism") == 0.0]
    strategy_errors = [case for case in cases if case["scores"].get("strategy", 1.0) < 1.0]

    if mechanism_errors:
        candidates.append(
            {
                "memory_type": "label_confusion_memory",
                "target_skills": ["MechanismSkill"],
                "content_en": (
                    "When a post casually downplays or embeds a positive outcome without directly ranking the speaker above others, "
                    "consider understated_flex before achievement_drop or comparison_superiority."
                ),
                "content_zh": "当发言只是轻描淡写嵌入正面结果，而不是直接和他人比较时，优先考虑 understated_flex。",
                "conditions": {},
                "negative_conditions": {},
                "confidence": 0.55,
                "notes": "Rule-generated from mechanism errors; needs human review.",
            }
        )

    if strategy_errors:
        candidates.append(
            {
                "memory_type": "strategy_policy_memory",
                "target_skills": ["StrategySkill", "ResponseSkill"],
                "content_en": (
                    "If the speaker seems to invite conversation or playful recognition, light_acknowledgment may be too flat; "
                    "consider ask_followup or humor_tease when the context supports it."
                ),
                "content_zh": "如果发言者像是在邀请继续聊或期待轻松回应，light_acknowledgment 可能太平，应考虑追问或轻微调侃。",
                "conditions": {},
                "negative_conditions": {"speaker_post_keywords": ["workplace", "professional"]},
                "confidence": 0.5,
                "notes": "Rule-generated from strategy errors; needs human review.",
            }
        )

    return candidates[:max_items]


def generate_candidate_memories(
    *,
    cfg: Any,
    llm_client: Any,
    run_id: str,
    cases: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not getattr(cfg, "GENERATE_CANDIDATE_MEMORY", False):
        return None

    max_cases = int(getattr(cfg, "CANDIDATE_MEMORY_TOP_K_CASES", 10))
    max_items = int(getattr(cfg, "CANDIDATE_MEMORY_MAX_ITEMS", 10))
    selected_cases = cases[:max_cases]
    raw_candidates: list[dict[str, Any]] = []
    llm_error: str | None = None

    if selected_cases:
        try:
            raw = llm_client.call_chat(
                _candidate_prompt(selected_cases, max_items),
                temperature=0.2,
                max_tokens=1600,
            )
            raw_candidates = _parse_candidates(raw)
        except Exception as exc:
            llm_error = str(exc)

    if not raw_candidates:
        raw_candidates = _fallback_candidates(selected_cases, max_items)

    now = datetime.now().strftime("%Y-%m-%d")
    candidate_items: list[MemoryItem] = []
    source_episode_ids = [case["episode_id"] for case in selected_cases]
    for index, data in enumerate(raw_candidates[:max_items], start=1):
        item = MemoryItem.from_dict(
            {
                **data,
                "memory_id": _new_memory_id(run_id, index),
                "status": "candidate",
                "source": {
                    "kind": "error_analysis",
                    "run_id": run_id,
                    "episode_ids": source_episode_ids,
                },
                "created_at": now,
                "version": 1,
            }
        )
        candidate_items.append(item)

    memory_dir = Path(getattr(cfg, "MEMORY_DIR"))
    store = load_memory_store(cfg)
    review_rows = review_candidates(candidate_items, store.active_items, llm_client=llm_client)

    candidate_path = memory_dir / "candidate" / "memory_candidates.jsonl"
    review_path = memory_dir / "candidate" / "candidate_review.md"
    existing_rows = load_jsonl(candidate_path) if candidate_path.exists() else []
    all_rows = existing_rows + review_rows
    write_jsonl(candidate_path, all_rows)
    _write_candidate_review(review_path, all_rows, llm_error)

    return {
        "candidate_memory_path": str(candidate_path),
        "candidate_review_path": str(review_path),
        "candidate_count": len(review_rows),
        "llm_error": llm_error,
    }


def _write_candidate_review(path: Path, rows: list[dict[str, Any]], llm_error: str | None) -> None:
    lines = ["# 候选 Memory 审核", ""]
    if llm_error:
        lines.extend(["## LLM 生成异常", "", llm_error, ""])
    for row in rows:
        review = row.get("review", {})
        lines.extend(
            [
                f"## {row.get('memory_id')}",
                "",
                f"- status：`{row.get('status')}`",
                f"- type：`{row.get('memory_type')}`",
                f"- target_skills：`{row.get('target_skills')}`",
                f"- confidence：`{row.get('confidence')}`",
                f"- recommended_action：`{review.get('recommended_action')}`",
                f"- errors：`{review.get('errors', [])}`",
                f"- warnings：`{review.get('warnings', [])}`",
                "",
                row.get("content_en", ""),
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
