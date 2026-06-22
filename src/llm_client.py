from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from collections import deque
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import OpenAI


def load_env(env_path: Path | None = None) -> None:
    if env_path is not None:
        load_dotenv(env_path)
    else:
        load_dotenv()


# --- Thinking model output extraction ---

_FINAL_MARKERS = re.compile(
    r"\b(final\s+answer|final:|answer:|output:|label:|result:)\s*",
    re.IGNORECASE,
)
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL | re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[\*\-•]\s+")
_REASONING_LEAK_PATTERNS = [
    "post content:",
    "key elements:",
    "the speaker is",
    "the user wants",
    "bragging mechanism",
    "response strategy",
]


def extract_final_answer_from_reasoning(text: str) -> str:
    """Last-resort fallback: try to recover a short final answer from thinking text.

    Does NOT return full chain-of-thought / reasoning.
    """
    if not isinstance(text, str) or not text.strip():
        return ""
    text = text.strip()

    # 1. Try fenced JSON.
    for match in _JSON_FENCE_RE.finditer(text):
        candidate = match.group(1).strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return candidate
        except json.JSONDecodeError:
            pass

    # 2. Try ALL JSON objects, prefer the LAST one (likely the answer, not input context).
    json_candidates: list[tuple[int, str]] = []
    search_start = 0
    while True:
        start = text.find("{", search_start)
        if start == -1:
            break
        # Find matching closing brace (simple heuristic: find next })
        end = text.find("}", start)
        if end == -1:
            break
        candidate = text[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                json_candidates.append((start, candidate))
        except json.JSONDecodeError:
            pass
        search_start = end + 1

    if json_candidates:
        # Prefer JSON that contains "label" key (likely the answer).
        for _pos, candidate in json_candidates:
            try:
                parsed = json.loads(candidate)
                if "label" in parsed:
                    return candidate
            except json.JSONDecodeError:
                pass
        # Otherwise return the last one.
        return json_candidates[-1][1]

    # 3. Try explicit final markers.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        lower = line.lower()
        for marker in ("final answer:", "final:", "answer:", "output:", "label:", "result:"):
            if marker in lower:
                extracted = line.split(":", 1)[-1].strip().strip('"').strip("'")
                if extracted and len(extracted.split()) <= 20:
                    return extracted

    # 4. Try last non-bullet short line.
    for line in reversed(lines):
        if _BULLET_RE.match(line):
            continue
        stripped = line.strip().strip("*").strip('"').strip("'").strip()
        if stripped and len(stripped.split()) <= 12:
            # Check it's not a reasoning leak.
            lower = stripped.lower()
            if not any(pat in lower for pat in _REASONING_LEAK_PATTERNS):
                return stripped

    # 5. Do NOT return full reasoning.
    return ""


def extract_model_text(content: str, reasoning: str, *, allow_reasoning_fallback: bool = False) -> tuple[str, str]:
    """Extract final answer text from model response.

    Returns (extracted_text, source) where source is one of:
    "content", "reasoning_extracted", "empty"

    Rules:
    1. Prefer message.content.
    2. Do not return message.reasoning by default.
    3. If allow_reasoning_fallback=True, only extract possible final answer from reasoning.
    4. Never return full reasoning text as final answer.
    """
    if isinstance(content, str) and content.strip():
        return content.strip(), "content"

    if allow_reasoning_fallback and isinstance(reasoning, str) and reasoning.strip():
        extracted = extract_final_answer_from_reasoning(reasoning)
        if extracted:
            return extracted, "reasoning_extracted"

    return "", "empty"


class LLMClient:
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        retry_times: int,
        retry_sleep_seconds: float,
        enable_rate_limit: bool = False,
        requests_per_minute: int | None = None,
        tokens_per_minute: int | None = None,
        rate_limit_safety_margin: float = 0.9,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.retry_times = max(1, retry_times)
        self.retry_sleep_seconds = retry_sleep_seconds
        self.rate_limiter = RateLimiter(
            enabled=enable_rate_limit,
            requests_per_minute=requests_per_minute,
            tokens_per_minute=tokens_per_minute,
            safety_margin=rate_limit_safety_margin,
        )
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=100.0)

    @classmethod
    def from_env(
        cls,
        retry_times: int,
        retry_sleep_seconds: float,
        enable_rate_limit: bool = False,
        requests_per_minute: int | None = None,
        tokens_per_minute: int | None = None,
        rate_limit_safety_margin: float = 0.9,
    ) -> "LLMClient":
        base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        missing = [
            name
            for name, value in {
                "OPENAI_BASE_URL": base_url,
                "OPENAI_API_KEY": api_key,
                "OPENAI_MODEL": model,
            }.items()
            if not value
        ]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"缺少必需的环境变量：{joined}")
        return cls(
            model=model,
            base_url=base_url,
            api_key=api_key,
            retry_times=retry_times,
            retry_sleep_seconds=retry_sleep_seconds,
            enable_rate_limit=enable_rate_limit,
            requests_per_minute=requests_per_minute,
            tokens_per_minute=tokens_per_minute,
            rate_limit_safety_margin=rate_limit_safety_margin,
        )

    def call_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        *,
        allow_reasoning_fallback: bool = False,
    ) -> tuple[str, str]:
        """Call chat and return (extracted_text, source).

        source is one of: "content", "reasoning_extracted", "empty"
        """
        last_error: Exception | None = None
        for attempt in range(1, self.retry_times + 1):
            try:
                self.rate_limiter.wait(messages=messages, max_tokens=max_tokens)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                message = response.choices[0].message
                content = message.content or ""
                reasoning = ""
                if hasattr(message, "reasoning"):
                    reasoning = getattr(message, "reasoning", None) or ""

                extracted, source = extract_model_text(
                    content, reasoning,
                    allow_reasoning_fallback=allow_reasoning_fallback,
                )

                if source == "empty" and reasoning.strip():
                    print(
                        "[WARN] model returned empty content and non-empty reasoning. "
                        "Final answer unavailable unless allow_reasoning_fallback is enabled.",
                        flush=True,
                    )

                return extracted, source
            except Exception as exc:  # 不同 OpenAI-compatible 后端的异常类型不完全一致。
                last_error = exc
                if attempt < self.retry_times:
                    sleep_seconds = self.retry_sleep_seconds * (2 ** (attempt - 1))
                    print(
                        f"[WARN] API 调用失败（第 {attempt}/{self.retry_times} 次尝试）："
                        f"{exc}。将在 {sleep_seconds:.1f} 秒后重试...",
                        flush=True,
                    )
                    time.sleep(sleep_seconds)
        raise RuntimeError(f"LLM 调用在 {self.retry_times} 次尝试后仍然失败：{last_error}")



@dataclass
class RateLimiter:
    """面向 OpenAI-compatible API 的简单本地限速器。

    这里只做保守的本地节流，不依赖服务端返回的 token 用量。
    token 数用字符数粗估，目的是避免 SiliconFlow 等远程服务触发 RPM/TPM 限制。
    """

    enabled: bool = False
    requests_per_minute: int | None = None
    tokens_per_minute: int | None = None
    safety_margin: float = 0.9
    request_events: deque[float] = field(default_factory=deque)
    token_events: deque[tuple[float, int]] = field(default_factory=deque)

    def _effective_limit(self, value: int | None) -> int | None:
        if value is None or value <= 0:
            return None
        margin = min(max(self.safety_margin, 0.1), 1.0)
        return max(1, int(value * margin))

    def _prune(self, now: float) -> None:
        cutoff = now - 60.0
        while self.request_events and self.request_events[0] <= cutoff:
            self.request_events.popleft()
        while self.token_events and self.token_events[0][0] <= cutoff:
            self.token_events.popleft()

    def _estimate_tokens(self, messages: list[dict[str, str]], max_tokens: int) -> int:
        prompt_text = "\n".join(str(message.get("content", "")) for message in messages)
        # 英文约 4 字符/token；中文会更保守一些。再把 max_tokens 加进去，防止输出超额。
        prompt_tokens = max(1, len(prompt_text) // 3)
        return prompt_tokens + max(0, int(max_tokens))

    def wait(self, messages: list[dict[str, str]], max_tokens: int) -> None:
        if not self.enabled:
            return

        rpm_limit = self._effective_limit(self.requests_per_minute)
        tpm_limit = self._effective_limit(self.tokens_per_minute)
        estimated_tokens = self._estimate_tokens(messages, max_tokens)

        while True:
            now = time.monotonic()
            self._prune(now)
            wait_seconds = 0.0
            limit_reasons: list[str] = []

            if rpm_limit is not None and len(self.request_events) >= rpm_limit:
                rpm_wait = 60.0 - (now - self.request_events[0])
                wait_seconds = max(wait_seconds, rpm_wait)
                limit_reasons.append("RPM")

            if tpm_limit is not None:
                used_tokens = sum(tokens for _, tokens in self.token_events)
                if used_tokens + estimated_tokens > tpm_limit and self.token_events:
                    tpm_wait = 60.0 - (now - self.token_events[0][0])
                    wait_seconds = max(wait_seconds, tpm_wait)
                    limit_reasons.append("TPM")

            if wait_seconds <= 0:
                self.request_events.append(now)
                self.token_events.append((now, estimated_tokens))
                return

            # 多留 1 秒缓冲，避免临界状态下反复短暂等待。
            wait_seconds += 1.0
            reason_text = "/".join(limit_reasons)
            print(
                f"已达到本地 {reason_text} 限制，预计等待 {wait_seconds:.1f} 秒。",
                flush=True,
            )
            time.sleep(min(wait_seconds, 10.0))
