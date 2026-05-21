from __future__ import annotations

from typing import Any

from ..postprocess import abstract_response_fallback, clean_response_text
from ..prompts_skillflow import build_response_prompt
from ..schemas import DEFAULT_RESPONSE_BY_STRATEGY, DEFAULT_STRATEGY
from ..social_rubric import judge_row
from .base import Skill


class ResponseSkill(Skill):
    name = "ResponseSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        row = state["input_row"]
        llm_client = context["llm_client"]
        retriever = context.get("fewshot_retriever")
        fewshot_examples = retriever.get_examples(row, "response") if retriever else []
        if fewshot_examples:
            state.setdefault("fewshot_examples", {})["response"] = fewshot_examples
        memory_retriever = context.get("memory_retriever")
        memory_snippets = (
            memory_retriever.retrieve(row, self.name, state) if memory_retriever else []
        )
        if memory_snippets:
            state.setdefault("memory_used", {})[self.name] = memory_snippets
        strategy = state.get("response_strategy", DEFAULT_STRATEGY)

        try:
            messages = build_response_prompt(
                row,
                state,
                context.get("wiki", {}),
                fewshot_examples,
                memory_snippets,
            )
            logger = context.get("debug_logger")
            if logger:
                raw = logger.timed_llm_call(
                    episode_id=state["episode_id"],
                    skill=self.name,
                    llm_client=llm_client,
                    messages=messages,
                    temperature=context.get("temperature", 0.3),
                    max_tokens=context.get("max_tokens", 256),
                )
            else:
                raw = llm_client.call_chat(
                    messages,
                    temperature=context.get("temperature", 0.3),
                    max_tokens=context.get("max_tokens", 256),
                )
            state["raw_outputs"]["response"] = raw
        except Exception as exc:
            state["skill_errors"].append({"skill": self.name, "error": str(exc)})
            raw = DEFAULT_RESPONSE_BY_STRATEGY.get(
                strategy,
                DEFAULT_RESPONSE_BY_STRATEGY[DEFAULT_STRATEGY],
            )

        cleaned = clean_response_text(raw, strategy)
        output_candidate = {
            "response_strategy": strategy,
            "response_text": cleaned,
        }
        judgment = judge_row(row, output_candidate)
        state["response_judgment"] = judgment
        if judgment["hard_issues"]:
            mechanism = state.get("bragging_mechanism", "other")
            fallback = clean_response_text(
                abstract_response_fallback(strategy, mechanism, row),
                strategy,
            )
            fallback_judgment = judge_row(
                row,
                {"response_strategy": strategy, "response_text": fallback},
            )
            state["response_fallback_judgment"] = fallback_judgment
            cleaned = fallback if not fallback_judgment["hard_issues"] else clean_response_text(
                DEFAULT_RESPONSE_BY_STRATEGY.get(
                    strategy,
                    DEFAULT_RESPONSE_BY_STRATEGY[DEFAULT_STRATEGY],
                ),
                strategy,
            )
        state["response_text"] = cleaned
        return state
