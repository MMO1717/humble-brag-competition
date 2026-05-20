from __future__ import annotations

from typing import Any

from ..postprocess import clean_field_text, parse_json_object
from ..prompts import build_understanding_prompt
from ..schemas import DEFAULT_DESIRED_FEEDBACK, DEFAULT_SPEAKER_INTENTION, MAX_WORDS
from .base import Skill


class UnderstandingSkill(Skill):
    name = "UnderstandingSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        row = state["input_row"]
        llm_client = context["llm_client"]
        mechanism = state.get("bragging_mechanism", "other")
        memory_retriever = context.get("memory_retriever")
        memory_snippets = (
            memory_retriever.retrieve(row, self.name, state) if memory_retriever else []
        )
        if memory_snippets:
            state.setdefault("memory_used", {})[self.name] = memory_snippets

        try:
            messages = build_understanding_prompt(
                row,
                mechanism,
                context.get("wiki", {}),
                memory_snippets,
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
            state["raw_outputs"]["understanding"] = raw
            parsed = parse_json_object(raw) or {}
        except Exception as exc:
            state["skill_errors"].append({"skill": self.name, "error": str(exc)})
            parsed = {}

        state["speaker_intention"] = clean_field_text(
            parsed.get("speaker_intention"),
            DEFAULT_SPEAKER_INTENTION,
            MAX_WORDS["speaker_intention"],
        )
        state["desired_feedback"] = clean_field_text(
            parsed.get("desired_feedback"),
            DEFAULT_DESIRED_FEEDBACK,
            MAX_WORDS["desired_feedback"],
        )
        return state
