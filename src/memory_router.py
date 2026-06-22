from __future__ import annotations

import json
from typing import Any

from .postprocess import parse_json_object


def _candidate_payload(memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for memory in memories:
        payload.append(
            {
                "memory_id": memory.get("memory_id"),
                "memory_type": memory.get("memory_type"),
                "target_labels": memory.get("target_labels", []),
                "conditions": memory.get("conditions", {}),
                "match_evidence": memory.get("match_evidence", []),
                "score": memory.get("score", 0),
                "content": str(memory.get("content", ""))[:360],
            }
        )
    return payload


def build_memory_router_prompt(
    row: dict[str, Any],
    state: dict[str, Any],
    candidates: list[dict[str, Any]],
    max_selected: int,
) -> list[dict[str, str]]:
    payload = {
        "input": {
            "speaker_post": row.get("speaker_post", ""),
            "platform": row.get("platform", ""),
            "relationship": row.get("relationship", ""),
            "agent_role": row.get("agent_role", ""),
            "interaction_goal": row.get("interaction_goal", ""),
        },
        "confirmed": {
            "bragging_mechanism": state.get("bragging_mechanism", ""),
            "response_strategy": state.get("response_strategy", ""),
            "risk_labels": state.get("risk_labels", []),
        },
        "max_selected": max_selected,
        "candidate_memories": _candidate_payload(candidates),
    }
    user_content = (
        "Select the memory IDs that are useful for writing the final short reply. "
        "Use only the confirmed mechanism, response strategy, risk labels, and row "
        "context. Prefer strategy-compatible style cards and directly relevant "
        "anti-patterns. Drop off-strategy, redundant, or generic memories. "
        "Return only compact JSON with this exact shape: "
        '{"selected_memory_ids":["id"],"reason_codes":["short_code"]}\n\n'
        f"Input:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    return [
        {
            "role": "system",
            "content": (
                "You are an ID-only memory router. Select existing memory IDs only. "
                "Do not write or rewrite any memory content."
            ),
        },
        {"role": "user", "content": user_content},
    ]


def rerank_memory_snippets_with_llm(
    *,
    row: dict[str, Any],
    state: dict[str, Any],
    candidates: list[dict[str, Any]],
    llm_client: Any,
    cfg: Any,
    logger: Any = None,
    skill_name: str = "ResponseSkill",
) -> list[dict[str, Any]]:
    max_selected = int(getattr(cfg, "MEMORY_LLM_ROUTER_TOP_K", 3))
    max_selected = max(0, min(max_selected, len(candidates)))
    trace = {
        "mode": "llm_rerank",
        "skill": skill_name,
        "candidate_ids": [item.get("memory_id") for item in candidates],
        "selected_ids": [],
        "fallback_used": False,
        "error": "",
        "raw": "",
    }
    state.setdefault("memory_router_trace", {})[skill_name] = trace
    if not candidates or max_selected == 0:
        return []

    messages = build_memory_router_prompt(row, state, candidates, max_selected)
    try:
        if logger:
            raw, _source = logger.timed_llm_call(
                episode_id=state["episode_id"],
                skill=f"MemoryRouter:{skill_name}",
                llm_client=llm_client,
                messages=messages,
                temperature=0.0,
                max_tokens=int(getattr(cfg, "MEMORY_LLM_ROUTER_MAX_TOKENS", 128)),
                allow_reasoning_fallback=getattr(
                    cfg,
                    "ALLOW_REASONING_FALLBACK",
                    False,
                ),
            )
        else:
            raw, _source = llm_client.call_chat(
                messages,
                temperature=0.0,
                max_tokens=int(getattr(cfg, "MEMORY_LLM_ROUTER_MAX_TOKENS", 128)),
                allow_reasoning_fallback=getattr(
                    cfg,
                    "ALLOW_REASONING_FALLBACK",
                    False,
                ),
            )
        trace["raw"] = raw
        parsed = parse_json_object(raw) or {}
        selected_ids = parsed.get("selected_memory_ids")
        if not isinstance(selected_ids, list):
            raise ValueError("missing selected_memory_ids")
    except Exception as exc:
        trace["fallback_used"] = True
        trace["error"] = str(exc)
        return candidates[:max_selected]

    by_id = {str(item.get("memory_id")): item for item in candidates}
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for memory_id in selected_ids:
        key = str(memory_id)
        if key in by_id and key not in seen:
            selected.append(by_id[key])
            seen.add(key)
        if len(selected) >= max_selected:
            break
    trace["selected_ids"] = [item.get("memory_id") for item in selected]
    return selected
