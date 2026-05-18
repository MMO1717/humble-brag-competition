from __future__ import annotations

import os
import time
from pathlib import Path

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
    ) -> None:
        self.model = model
        self.retry_times = max(1, retry_times)
        self.retry_sleep_seconds = retry_sleep_seconds
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    @classmethod
    def from_env(cls, retry_times: int, retry_sleep_seconds: float) -> "LLMClient":
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
                    time.sleep(self.retry_sleep_seconds)
        raise RuntimeError(f"LLM call failed after {self.retry_times} attempt(s): {last_error}")
