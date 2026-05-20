from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .io_utils import write_jsonl


def _message_char_count(messages: list[dict[str, str]]) -> int:
    return sum(len(str(message.get("content", ""))) for message in messages)


class DebugLogger:
    """收集一次 run 内的调试日志，最后由 pipeline 统一写入文件。"""

    def __init__(
        self,
        llm_call_path: Path,
        trace_path: Path,
        save_llm_calls: bool,
        save_prompt_text: bool,
        save_raw_output: bool,
        save_trace: bool,
    ) -> None:
        self.llm_call_path = llm_call_path
        self.trace_path = trace_path
        self.save_llm_calls = save_llm_calls
        self.save_prompt_text = save_prompt_text
        self.save_raw_output = save_raw_output
        self.save_trace = save_trace
        self.llm_call_count = 0
        self.prompt_char_count = 0
        self.llm_calls: list[dict[str, Any]] = []
        self.traces: list[dict[str, Any]] = []

    def timed_llm_call(
        self,
        *,
        episode_id: str,
        skill: str,
        llm_client: Any,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        start = time.perf_counter()
        try:
            response_text = llm_client.call_chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            self.record_llm_call(
                episode_id=episode_id,
                skill=skill,
                llm_client=llm_client,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                elapsed_ms=elapsed_ms,
                success=False,
                response_text="",
                error=str(exc),
            )
            raise

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        self.record_llm_call(
            episode_id=episode_id,
            skill=skill,
            llm_client=llm_client,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            elapsed_ms=elapsed_ms,
            success=True,
            response_text=response_text,
            error=None,
        )
        return response_text

    def record_llm_call(
        self,
        *,
        episode_id: str,
        skill: str,
        llm_client: Any,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        elapsed_ms: int,
        success: bool,
        response_text: str,
        error: str | None,
    ) -> None:
        prompt_chars = _message_char_count(messages)
        self.llm_call_count += 1
        self.prompt_char_count += prompt_chars
        if not self.save_llm_calls:
            return

        row: dict[str, Any] = {
            "episode_id": episode_id,
            "skill": skill,
            "model": getattr(llm_client, "model", "unknown"),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "success": success,
            "elapsed_ms": elapsed_ms,
            "prompt_char_count": prompt_chars,
            "response_char_count": len(response_text or ""),
            "error": error,
        }
        if self.save_prompt_text:
            row["messages"] = messages
        if self.save_raw_output:
            row["response_text"] = response_text
        self.llm_calls.append(row)

    def record_trace(self, state: dict[str, Any]) -> None:
        if not self.save_trace:
            return

        self.traces.append(
            {
                "episode_id": state.get("episode_id"),
                "bragging_mechanism": state.get("bragging_mechanism"),
                "speaker_intention": state.get("speaker_intention"),
                "desired_feedback": state.get("desired_feedback"),
                "risk_labels": state.get("risk_labels", []),
                "risk_assessment": state.get("risk_assessment"),
                "response_strategy": state.get("response_strategy"),
                "response_text": state.get("response_text"),
                "skill_trace": state.get("skill_trace", []),
                "skill_errors": state.get("skill_errors", []),
                "validation_errors": state.get("validation_errors", []),
                "raw_outputs": state.get("raw_outputs", {}),
                "fewshot_examples": state.get("fewshot_examples", {}),
                "memory_used": state.get("memory_used", {}),
                "response_judgment": state.get("response_judgment", {}),
                "response_fallback_judgment": state.get("response_fallback_judgment", {}),
            }
        )

    def write(self) -> None:
        if self.save_llm_calls:
            write_jsonl(self.llm_call_path, self.llm_calls)
        if self.save_trace:
            write_jsonl(self.trace_path, self.traces)
