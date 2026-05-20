from __future__ import annotations

from typing import Any

from ..postprocess import safe_mechanism
from ..prompts import build_mechanism_prompt
from ..schemas import DEFAULT_MECHANISM, VALID_BRAGGING_MECHANISMS
from .base import Skill


class MechanismSkill(Skill):
    name = "MechanismSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        row = state["input_row"]
        llm_client = context["llm_client"]
        retriever = context.get("fewshot_retriever")
        fewshot_examples = retriever.get_examples(row, "mechanism") if retriever else []
        if fewshot_examples:
            state.setdefault("fewshot_examples", {})["mechanism"] = fewshot_examples

        try:
            messages = build_mechanism_prompt(row, context.get("wiki", {}), fewshot_examples)
            logger = context.get("debug_logger")
            if logger:
                raw = logger.timed_llm_call(
                    episode_id=state["episode_id"],
                    skill=self.name,
                    llm_client=llm_client,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=32,
                )
            else:
                raw = llm_client.call_chat(messages, temperature=0.0, max_tokens=32)
            state["raw_outputs"]["mechanism"] = raw
            state["bragging_mechanism"] = safe_mechanism(raw, VALID_BRAGGING_MECHANISMS)
        except Exception as exc:
            state["skill_errors"].append({"skill": self.name, "error": str(exc)})
            state["bragging_mechanism"] = DEFAULT_MECHANISM
        return state
