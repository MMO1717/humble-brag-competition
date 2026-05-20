from __future__ import annotations

from typing import Any

from ..postprocess import clean_response_text
from ..prompts import build_response_prompt
from ..schemas import DEFAULT_RESPONSE_BY_STRATEGY, DEFAULT_STRATEGY
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
        strategy = state.get("response_strategy", DEFAULT_STRATEGY)

        try:
            messages = build_response_prompt(
                row,
                state,
                context.get("wiki", {}),
                fewshot_examples,
            )
            logger = context.get("debug_logger")
            if logger:
                raw = logger.timed_llm_call(
                    episode_id=state["episode_id"],
                    skill=self.name,
                    llm_client=llm_client,
                    messages=messages,
                    temperature=context["cfg"].TEMPERATURE,
                    max_tokens=context["cfg"].MAX_TOKENS,
                )
            else:
                raw = llm_client.call_chat(
                    messages,
                    temperature=context["cfg"].TEMPERATURE,
                    max_tokens=context["cfg"].MAX_TOKENS,
                )
            state["raw_outputs"]["response"] = raw
        except Exception as exc:
            state["skill_errors"].append({"skill": self.name, "error": str(exc)})
            raw = DEFAULT_RESPONSE_BY_STRATEGY.get(
                strategy,
                DEFAULT_RESPONSE_BY_STRATEGY[DEFAULT_STRATEGY],
            )

        state["response_text"] = clean_response_text(raw, strategy)
        return state
