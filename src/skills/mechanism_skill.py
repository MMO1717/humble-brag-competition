from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..postprocess import (
    assess_mechanism_rules,
    calibrate_mechanism_with_evidence,
    mechanism_review_reason,
    normalize_mechanism_post,
    parse_mechanism_classification,
    parse_mechanism_review,
)
from ..prompts import build_mechanism_prompt, build_mechanism_review_prompt
from ..schemas import DEFAULT_MECHANISM, VALID_BRAGGING_MECHANISMS
from .base import Skill


class MechanismSkill(Skill):
    name = "MechanismSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        row = state["input_row"]
        llm_client = context["llm_client"]
        cfg = context.get("cfg")
        knowledge = context.get("mechanism_knowledge", [])
        knowledge_ids = [
            str(item.get("memory_id"))
            for item in knowledge
            if item.get("memory_id")
        ]
        cache = context.setdefault("mechanism_cache", {})
        cache_key = normalize_mechanism_post(row.get("speaker_post", ""))

        if cache_key in cache:
            cached = deepcopy(cache[cache_key])
            cached["mechanism_calibration"]["cache_hit"] = True
            state["raw_outputs"].update(cached["raw_outputs"])
            state["bragging_mechanism"] = cached["bragging_mechanism"]
            state["mechanism_calibration"] = cached["mechanism_calibration"]
            return state

        allow_rf = getattr(cfg, "ALLOW_REASONING_FALLBACK", False) if cfg else False
        thinking_model = getattr(cfg, "THINKING_MODEL", False) if cfg else False
        token_multiplier = getattr(cfg, "THINKING_MODEL_MAX_TOKENS_MULTIPLIER", 1) if cfg else 1
        base_max_tokens = 96
        max_tokens = base_max_tokens * (token_multiplier if thinking_model else 1)
        try:
            messages = build_mechanism_prompt(row, knowledge, thinking_model=thinking_model)
            logger = context.get("debug_logger")
            if logger:
                raw, _source = logger.timed_llm_call(
                    episode_id=state["episode_id"],
                    skill=self.name,
                    llm_client=llm_client,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=max_tokens,
                    allow_reasoning_fallback=allow_rf,
                )
            else:
                raw, _source = llm_client.call_chat(
                    messages,
                    temperature=0.0,
                    max_tokens=max_tokens,
                    allow_reasoning_fallback=allow_rf,
                )
            state["raw_outputs"]["mechanism"] = raw
            initial = parse_mechanism_classification(raw)
            predicted = initial["label"]
            rule = assess_mechanism_rules(row, predicted)
            review_reasons = mechanism_review_reason(initial, rule)

            review: dict[str, Any] | None = None
            review_raw = ""
            review_label: str | None = None
            review_error: str | None = None
            candidate_b = (
                rule["suggested_label"]
                if rule["conflict"] and rule["override_allowed"]
                else initial["runner_up"]
            )
            if candidate_b == predicted or candidate_b not in VALID_BRAGGING_MECHANISMS:
                candidate_b = (
                    "understated_flex"
                    if predicted != "understated_flex"
                    else "achievement_drop"
                )

            use_calibration = getattr(
                cfg,
                "USE_MECHANISM_CALIBRATION",
                True,
            )
            if use_calibration and review_reasons:
                review_messages = build_mechanism_review_prompt(
                    row,
                    predicted,
                    candidate_b,
                    rule["evidence"],
                    thinking_model=thinking_model,
                )
                try:
                    review_max_tokens = 80 * (token_multiplier if thinking_model else 1)
                    if logger:
                        review_raw, _review_source = logger.timed_llm_call(
                            episode_id=state["episode_id"],
                            skill="MechanismReviewSkill",
                            llm_client=llm_client,
                            messages=review_messages,
                            temperature=0.0,
                            max_tokens=review_max_tokens,
                            allow_reasoning_fallback=allow_rf,
                        )
                    else:
                        review_raw, _review_source = llm_client.call_chat(
                            review_messages,
                            temperature=0.0,
                            max_tokens=review_max_tokens,
                            allow_reasoning_fallback=allow_rf,
                        )
                    state["raw_outputs"]["mechanism_review"] = review_raw
                    review = parse_mechanism_review(
                        review_raw,
                        predicted,
                        candidate_b,
                    )
                    if (
                        review["structured"]
                        and review["label"] in {predicted, candidate_b}
                    ):
                        review_label = review["label"]
                except Exception as exc:
                    review_error = str(exc)
                    print(
                        f"[WARN] {state['episode_id']} 机制复核失败，"
                        f"将使用初始分类与规则结果：{exc}",
                        flush=True,
                    )

            if use_calibration:
                result = calibrate_mechanism_with_evidence(
                    row,
                    predicted,
                    runner_up=initial["runner_up"],
                    model_confidence=initial["confidence"],
                    review_label=review_label,
                    review_confidence=(
                        review.get("confidence") if review else None
                    ),
                    review_reason=review_reasons,
                )
            else:
                result = {
                    "label": predicted,
                    "initial_label": predicted,
                    "runner_up": initial["runner_up"],
                    "model_confidence": initial["confidence"],
                    "changed": False,
                    "decision": "calibration_disabled",
                    "evidence": ["机制校准已关闭"],
                    "memory_evidence": [],
                }
            result.update(
                {
                    "cache_hit": False,
                    "cache_key": cache_key,
                    "initial_classification": initial,
                    "review_classification": review,
                    "review_candidate": candidate_b,
                    "review_error": review_error,
                    "mechanism_knowledge_ids": knowledge_ids,
                }
            )
            state["bragging_mechanism"] = result["label"]
            state["mechanism_calibration"] = result
            cache[cache_key] = deepcopy(
                {
                    "bragging_mechanism": state["bragging_mechanism"],
                    "mechanism_calibration": result,
                    "raw_outputs": {
                        "mechanism": raw,
                        **(
                            {"mechanism_review": review_raw}
                            if review_raw
                            else {}
                        ),
                    },
                }
            )
        except Exception as exc:
            state["skill_errors"].append({"skill": self.name, "error": str(exc)})
            state["bragging_mechanism"] = DEFAULT_MECHANISM
            print(
                f"[WARN] {state['episode_id']} 机制分类失败，"
                f"已使用默认机制 {DEFAULT_MECHANISM}：{exc}",
                flush=True,
            )
        return state
