from __future__ import annotations
import re
from typing import Any

from ..judges.local_official_like import judge_output_row
from ..memory_router import rerank_memory_snippets_with_llm
from ..postprocess import (
    abstract_response_fallback,
    clean_response_text,
)
from ..prompts import build_response_prompt
from ..schemas import DEFAULT_RESPONSE_BY_STRATEGY, DEFAULT_STRATEGY
from ..social_rubric import judge_row
from ..understanding_templates import repair_understanding_fields
from .base import Skill


PUBLIC_OR_CONSTRAINED_PLATFORMS = {
    "public_social_media",
    "community_forum",
    "academic_forum",
    "workplace_channel",
}


def _is_usable_concrete_detail(detail: str) -> bool:
    lowered = detail.lower().strip()
    if len(lowered.split()) < 2:
        return False
    if re.search(r"\b(i|i'm|i’d|i've|i think|we|my)\b", lowered):
        return False
    if re.search(r"\b(bragging|brag|flex|uhh|umm|haha|lol)\b", lowered):
        return False
    if lowered.count(" ") > 7:
        return False
    return True


def _extract_concrete_detail(input_row: dict[str, Any]) -> str:
    """从原帖提取可用于兜底回复的具体细节。"""
    post = str(input_row.get("speaker_post", ""))
    # 优先提取 about 后的主题、引号内容或量化信息。
    about_match = re.search(r"\babout\s+([\w\s'-]{3,30})", post, re.I)
    if about_match:
        detail = about_match.group(1).strip()
        return detail if _is_usable_concrete_detail(detail) else ""
    quoted_match = re.search(r'"([^"]{3,40})"', post)
    if quoted_match:
        detail = quoted_match.group(1).strip()
        return detail if _is_usable_concrete_detail(detail) else ""
    metric_match = re.search(
        r"\b(\d+(?:\.\d+)?%?[ -](?:point|seat|award|score|rank|promotion|"
        r"preview|beta|publication|project|client|mission|game|presentation)s?)\b",
        post,
        re.I,
    )
    if metric_match:
        detail = metric_match.group(1).strip()
        return detail if _is_usable_concrete_detail(detail) else ""
    # 没有明显主题时使用首个短分句。
    cleaned = re.sub(r"^(Quick brag:|haha |lol |ok so |so basically )", "", post, flags=re.I)
    clause = re.split(r"[.!?;]", cleaned, maxsplit=1)[0].strip()
    words = clause.split()
    if len(words) >= 3:
        detail = " ".join(words[:7])[:64].rstrip(".,;: ")
        return detail if _is_usable_concrete_detail(detail) else ""
    detail = cleaned[:50].strip()
    return detail if _is_usable_concrete_detail(detail) else ""


def _make_concrete_fallback(strategy: str, input_row: dict[str, Any], concrete: str) -> str:
    bank: dict[str, list[str]] = {
        "ask_followup": [
            f"What stood out about the {concrete} part?",
            f"Was there a specific moment around {concrete}?",
            f"How did the {concrete} come about?",
        ],
        "neutral_observation": [
            f"Sounds like {concrete} gave you some perspective.",
            f"That's an interesting context around {concrete}.",
            f"The {concrete} detail adds useful background.",
        ],
        "light_acknowledgment": [
            f"Fair point about {concrete}.",
            f"I can see why {concrete} felt worth sharing.",
            f"{concrete.capitalize()} sounds like it's been on your mind.",
        ],
        "redirect": [
            f"I get the point around {concrete} - how has the rest been going?",
            f"That puts {concrete} in context. What's next?",
            f"Noted on {concrete}. Anything else worth mentioning?",
        ],
        "humor_tease": [
            f"Subtle flex about {concrete}, I see you.",
            f"{concrete.capitalize()} - we get it, you're doing the thing.",
            f"I see the casual {concrete} drop. Point taken.",
        ],
        "validate": [
            f"That {concrete} context sounds genuinely meaningful.",
            f"I can see why {concrete} would feel significant.",
            f"You make a fair point with the {concrete} context.",
        ],
        "set_boundary": [
            f"I hear you on {concrete}, but I'll keep the focus elsewhere.",
            f"I'll let the {concrete} detail stand on its own.",
            f"Noted on {concrete}. Let's keep the focus on the bigger picture.",
        ],
        "no_response": [
            "",
            "Noted.",
            "Got it.",
        ],
    }
    options = bank.get(strategy, bank["neutral_observation"])
    import hashlib
    idx = int(hashlib.md5(concrete.encode()).hexdigest(), 16) % len(options)
    return options[idx]


def _candidate_score(candidate: dict[str, Any]) -> float:
    bloom_penalty = sum(candidate["judgment"]["bloom"].values()) / 6
    issue_penalty = 0.01 * len(candidate["judgment"]["issues"])
    source_bonus = 0.03 if candidate["source"] == "llm" else 0.0
    return round(
        candidate["judgment"]["overall_score"] - bloom_penalty * 0.2 - issue_penalty + source_bonus,
        4,
    )


def _response_candidates(
    *,
    row: dict[str, Any],
    state: dict[str, Any],
    strategy: str,
    cleaned: str,
    max_candidates: int,
) -> list[dict[str, Any]]:
    mechanism = str(state.get("bragging_mechanism", "other"))
    concrete = _extract_concrete_detail(row)
    raw_candidates: list[tuple[str, str]] = [("llm", cleaned)]
    if concrete and not (
        strategy == "humor_tease"
        and str(row.get("platform", "")) in PUBLIC_OR_CONSTRAINED_PLATFORMS
    ):
        raw_candidates.append(("concrete_fallback", _make_concrete_fallback(strategy, row, concrete)))
    raw_candidates.extend(
        [
            ("abstract_fallback", abstract_response_fallback(strategy, mechanism, row)),
            (
                "strategy_default",
                DEFAULT_RESPONSE_BY_STRATEGY.get(
                    strategy,
                    DEFAULT_RESPONSE_BY_STRATEGY[DEFAULT_STRATEGY],
                ),
            ),
        ]
    )

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source, text in raw_candidates:
        response_text = clean_response_text(text, strategy)
        key = response_text.lower()
        if key in seen:
            continue
        seen.add(key)
        output_row = {
            "episode_id": row.get("episode_id"),
            "bragging_mechanism": mechanism,
            "speaker_intention": state.get("speaker_intention", ""),
            "desired_feedback": state.get("desired_feedback", ""),
            "risk_assessment": state.get("risk_assessment", ""),
            "response_strategy": strategy,
            "response_text": response_text,
        }
        judgment = judge_output_row(row, output_row)
        candidate = {
            "source": source,
            "response_text": response_text,
            "judgment": judgment,
        }
        candidate["score"] = _candidate_score(candidate)
        candidates.append(candidate)
        if len(candidates) >= max_candidates:
            break
    return candidates


def _select_response_candidate(
    candidates: list[dict[str, Any]],
    min_delta: float,
) -> dict[str, Any] | None:
    if not candidates:
        return None
    current = candidates[0]
    best = max(candidates, key=lambda candidate: candidate["score"])
    current_has_hard_issue = any(
        issue.startswith("social_hard:") or issue.startswith("core:")
        for issue in current["judgment"]["issues"]
    )
    if best["source"] == current["source"]:
        return current
    if current_has_hard_issue or best["score"] >= current["score"] + min_delta:
        return best
    return current


class ResponseSkill(Skill):
    name = "ResponseSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        row = state["input_row"]
        llm_client = context["llm_client"]
        cfg = context.get("cfg")
        if getattr(cfg, "USE_UNDERSTANDING_TEMPLATE_REPAIR", False):
            fields = set(
                getattr(
                    cfg,
                    "UNDERSTANDING_TEMPLATE_REPAIR_FIELDS",
                    ("desired_feedback",),
                )
            )
            repair_understanding_fields(state, row, fields)
        retriever = context.get("fewshot_retriever")
        fewshot_examples = retriever.get_examples(row, "response", state) if retriever else []
        if fewshot_examples:
            state.setdefault("fewshot_examples", {})["response"] = fewshot_examples
        memory_retriever = context.get("memory_retriever")
        router_mode = getattr(cfg, "MEMORY_ROUTER_MODE", "function") if cfg else "function"
        if memory_retriever and router_mode == "llm_rerank":
            memory_snippets = memory_retriever.retrieve(
                row,
                self.name,
                state,
                candidate_limit=getattr(cfg, "MEMORY_LLM_ROUTER_CANDIDATE_K", 8),
                max_chars_override=getattr(
                    cfg,
                    "MEMORY_LLM_ROUTER_MAX_CANDIDATE_CHARS",
                    6000,
                ),
            )
            memory_snippets = rerank_memory_snippets_with_llm(
                row=row,
                state=state,
                candidates=memory_snippets,
                llm_client=llm_client,
                cfg=cfg,
                logger=context.get("debug_logger"),
                skill_name=self.name,
            )
        else:
            memory_snippets = (
                memory_retriever.retrieve(row, self.name, state)
                if memory_retriever
                else []
            )
        if memory_snippets:
            state.setdefault("memory_used", {})[self.name] = memory_snippets
        strategy = state.get("response_strategy", DEFAULT_STRATEGY)

        allow_rf = getattr(cfg, "ALLOW_REASONING_FALLBACK", False) if cfg else False
        thinking_model = getattr(cfg, "THINKING_MODEL", False) if cfg else False
        llm_response_accepted = False
        fallback_used = False
        fallback_reason = ""

        try:
            messages = build_response_prompt(
                row, state, fewshot_examples, memory_snippets,
                thinking_model=thinking_model,
            )
            logger = context.get("debug_logger")
            if logger:
                raw, _source = logger.timed_llm_call(
                    episode_id=state["episode_id"], skill=self.name,
                    llm_client=llm_client, messages=messages,
                    temperature=cfg.TEMPERATURE if cfg else 0.3,
                    max_tokens=cfg.MAX_TOKENS if cfg else 256,
                    allow_reasoning_fallback=allow_rf,
                )
            else:
                raw, _source = llm_client.call_chat(
                    messages,
                    temperature=cfg.TEMPERATURE if cfg else 0.3,
                    max_tokens=cfg.MAX_TOKENS if cfg else 256,
                    allow_reasoning_fallback=allow_rf,
                )
            state["raw_outputs"]["response"] = raw
            llm_response_accepted = True
        except Exception as exc:
            state["skill_errors"].append({"skill": self.name, "error": str(exc)})
            concrete = _extract_concrete_detail(row)
            use_concrete = getattr(cfg, "USE_CONCRETE_FALLBACK", True) if cfg else True
            raw = (
                _make_concrete_fallback(strategy, row, concrete)
                if use_concrete and concrete
                else abstract_response_fallback(
                    strategy,
                    state.get("bragging_mechanism", "other"),
                    row,
                )
            )
            fallback_used = True
            fallback_reason = f"llm_error: {exc}"

        cleaned = clean_response_text(raw, strategy)
        output_candidate = {"response_strategy": strategy, "response_text": cleaned}
        judgment = judge_row(input_row=row, output_row=output_candidate)

        # 出现硬性问题时，依次尝试具体兜底和通用模板。
        hard_issues = judgment.get("hard_issues", [])
        soft_score = judgment.get("social_score", 2)

        if hard_issues:
            llm_response_accepted = False
            concrete = _extract_concrete_detail(row)
            use_concrete = getattr(cfg, "USE_CONCRETE_FALLBACK", True) if cfg else True

            if use_concrete and concrete:
                concrete_text = _make_concrete_fallback(strategy, row, concrete)
                if concrete_text:
                    cleaned = clean_response_text(concrete_text, strategy)
                    fallback_used = True
                    fallback_reason = f"concrete_fallback: {', '.join(hard_issues)}"
                else:
                    cleaned = clean_response_text(
                        abstract_response_fallback(
                            strategy,
                            state.get("bragging_mechanism", "other"),
                            row,
                        ),
                        strategy,
                    )
                    fallback_used = True
                    fallback_reason = f"abstract_fallback: {', '.join(hard_issues)}"
            else:
                cleaned = clean_response_text(
                    abstract_response_fallback(
                        strategy,
                        state.get("bragging_mechanism", "other"),
                        row,
                    ),
                    strategy,
                )
                fallback_used = True
                fallback_reason = f"abstract_fallback: {', '.join(hard_issues)}"

        if fallback_used:
            fallback_judgment = judge_row(
                input_row=row,
                output_row={"response_strategy": strategy, "response_text": cleaned},
            )
            state["response_fallback_judgment"] = fallback_judgment
            if fallback_judgment.get("hard_issues"):
                cleaned = clean_response_text(
                    abstract_response_fallback(
                        strategy,
                        state.get("bragging_mechanism", "other"),
                        row,
                    ),
                    strategy,
                )
                second_judgment = judge_row(
                    input_row=row,
                    output_row={"response_strategy": strategy, "response_text": cleaned},
                )
                state["response_fallback_judgment"] = second_judgment
                if second_judgment.get("hard_issues"):
                    cleaned = clean_response_text(
                        DEFAULT_RESPONSE_BY_STRATEGY.get(
                            strategy,
                            DEFAULT_RESPONSE_BY_STRATEGY[DEFAULT_STRATEGY],
                        ),
                        strategy,
                    )
                    fallback_reason += "; template_fallback"

        rerank_enabled = (
            getattr(cfg, "USE_RESPONSE_CANDIDATE_RERANK", False) if cfg else False
        )
        if rerank_enabled:
            max_candidates = max(1, int(getattr(cfg, "RESPONSE_CANDIDATE_K", 5)))
            min_delta = float(getattr(cfg, "RESPONSE_CANDIDATE_MIN_DELTA", 0.08))
            candidates = _response_candidates(
                row=row,
                state=state,
                strategy=strategy,
                cleaned=cleaned,
                max_candidates=max_candidates,
            )
            selected = _select_response_candidate(candidates, min_delta)
            if selected:
                state["response_candidate_rerank"] = {
                    "enabled": True,
                    "selected_source": selected["source"],
                    "selected_score": selected["score"],
                    "candidate_count": len(candidates),
                    "candidates": [
                        {
                            "source": candidate["source"],
                            "score": candidate["score"],
                            "overall_score": candidate["judgment"]["overall_score"],
                            "issues": candidate["judgment"]["issues"],
                            "bloom": candidate["judgment"]["bloom"],
                        }
                        for candidate in candidates
                    ],
                }
                cleaned = selected["response_text"]
        else:
            state["response_candidate_rerank"] = {"enabled": False}

        state["response_text"] = cleaned
        state["llm_response_accepted"] = llm_response_accepted
        state["fallback_used"] = fallback_used
        state["fallback_reason"] = fallback_reason
        state["response_judgment"] = judgment
        if fallback_used:
            print(
                f"[WARN] {state['episode_id']} 回复已使用兜底：{fallback_reason}",
                flush=True,
            )
        return state
