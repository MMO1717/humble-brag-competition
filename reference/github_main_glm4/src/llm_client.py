from __future__ import annotations

import os
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
            raise RuntimeError(f"Missing required environment variable(s): {joined}")
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
    ) -> str:
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
                content = response.choices[0].message.content or ""
                return content.strip()
            except Exception as exc:  # 不同 OpenAI-compatible 后端的异常类型不完全一致。
                last_error = exc
                if attempt < self.retry_times:
                    sleep_seconds = self.retry_sleep_seconds * (2 ** (attempt - 1))
                    print(f"API 调用失败（第 {attempt}/{self.retry_times} 次尝试）：{exc}。将在 {sleep_seconds:.1f} 秒后重试...")
                    time.sleep(sleep_seconds)
        raise RuntimeError(f"LLM call failed after {self.retry_times} attempt(s): {last_error}")



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

            if rpm_limit is not None and len(self.request_events) >= rpm_limit:
                wait_seconds = max(wait_seconds, 60.0 - (now - self.request_events[0]))

            if tpm_limit is not None:
                used_tokens = sum(tokens for _, tokens in self.token_events)
                if used_tokens + estimated_tokens > tpm_limit and self.token_events:
                    wait_seconds = max(wait_seconds, 60.0 - (now - self.token_events[0][0]))

            if wait_seconds <= 0:
                self.request_events.append(now)
                self.token_events.append((now, estimated_tokens))
                return

            # 强制多加 1 秒缓冲，避免由于浮点数精度、线程调度或临界状态导致的微小抖动和反复等待
            wait_seconds += 1.0
            print(f"API 限速等待 {wait_seconds:.1f}s，避免超过 RPM/TPM。")
            time.sleep(min(wait_seconds, 10.0))
