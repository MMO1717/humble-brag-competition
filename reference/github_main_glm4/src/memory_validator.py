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
    """返回 (是否可进入候选池, errors, warnings)。"""
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


import json

def review_candidates(
    candidates: list[MemoryItem],
    active_items: list[MemoryItem],
    llm_client: Any = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in candidates:
        ok, errors, warnings = validate_candidate_memory(item, active_items)
        row = item.to_dict()
        recommended_action = "keep_candidate" if ok else "reject"
        judge_result = {}

        if ok and llm_client is not None:
            try:
                active_context = "\n".join([
                    f"- ID: {act.memory_id}, Type: {act.memory_type}, Content: {act.content_en}"
                    for act in active_items[:15]
                ])

                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are an offline memory quality judge for a BRAG-Agent system.\n"
                            "Your task is to evaluate whether a candidate memory rule should be approved for activation (accept), "
                            "requires revision (revise), or should be discarded (reject).\n"
                            "You must return ONLY a raw JSON block, with no Markdown wrapping or other text."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            "Evaluate this candidate memory based on:\n"
                            "1. Generality: Is it reusable across multiple cases? (Score 1-5)\n"
                            "2. Correctness: Is it consistent with the label schema and task goal? (Score 1-5)\n"
                            "3. Overfit risk: Does it look like it just memorizes a specific dev example? (Score 1-5)\n"
                            "4. Usefulness: Can it improve mechanism classification, risk assessment, strategy selection, or response generation? (Score 1-5)\n"
                            "5. Conflict risk: Does it conflict with existing active memories? (Score 1-5)\n\n"
                            f"Existing active memories:\n{active_context}\n\n"
                            f"Candidate memory to evaluate:\n"
                            f"Type: {item.memory_type}\n"
                            f"Content (EN): {item.content_en}\n"
                            f"Content (ZH): {item.content_zh}\n"
                            f"Conditions: {item.conditions}\n"
                            f"Negative Conditions: {item.negative_conditions}\n\n"
                            "Return JSON format:\n"
                            "{\n"
                            '  "decision": "accept" | "revise" | "reject",\n'
                            '  "generality": 1-5,\n'
                            '  "correctness": 1-5,\n'
                            '  "overfit_risk": 1-5,\n'
                            '  "usefulness": 1-5,\n'
                            '  "conflict_risk": 1-5,\n'
                            '  "reason": "your explanation",\n'
                            '  "revised_memory_en": "more generalized version in English",\n'
                            '  "revised_memory_zh": "more generalized version in Chinese"\n'
                            "}"
                        )
                    }
                ]

                raw_response = llm_client.call_chat(
                    messages,
                    temperature=0.1,
                    max_tokens=600,
                )

                cleaned = raw_response.strip()
                start = cleaned.find("{")
                end = cleaned.rfind("}")
                if start != -1 and end != -1 and end > start:
                    cleaned = cleaned[start:end+1]

                res = json.loads(cleaned)
                judge_result = res

                decision = res.get("decision", "reject")
                generality = int(res.get("generality", 0))
                correctness = int(res.get("correctness", 0))
                usefulness = int(res.get("usefulness", 0))
                overfit_risk = int(res.get("overfit_risk", 5))
                conflict_risk = int(res.get("conflict_risk", 5))

                if (
                    decision in ["accept", "revise"]
                    and generality >= 4
                    and correctness >= 4
                    and usefulness >= 3
                    and overfit_risk <= 2
                    and conflict_risk <= 2
                ):
                    recommended_action = "accept"
                    if decision == "revise":
                        rev_en = res.get("revised_memory_en")
                        rev_zh = res.get("revised_memory_zh")
                        if rev_en and rev_zh:
                            row["content_en"] = rev_en
                            row["content_zh"] = rev_zh
                            warnings.append("memory was revised by local llm judge")
                else:
                    recommended_action = "reject"
                    warnings.append(f"local llm judge rejected the memory (decision={decision}, generality={generality}, correctness={correctness})")
            except Exception as e:
                warnings.append(f"local llm judge failed: {str(e)}")
                recommended_action = "keep_candidate"

        row["review"] = {
            "schema_ok": ok,
            "errors": errors,
            "warnings": warnings,
            "recommended_action": recommended_action,
            "local_judge": judge_result
        }
        rows.append(row)
    return rows
