from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener


def _load_simple_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_env(env_path: Path | None = None) -> None:
    if env_path is not None:
        _load_simple_env(env_path)
    else:
        _load_simple_env(Path(".env"))


class OllamaClient:
    def __init__(
        self,
        model: str,
        base_url: str,
        retry_times: int,
        retry_sleep_seconds: float,
        think: bool,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.retry_times = max(1, retry_times)
        self.retry_sleep_seconds = retry_sleep_seconds
        self.think = think
        self.opener = build_opener(ProxyHandler({}))

    @classmethod
    def from_env(cls, retry_times: int, retry_sleep_seconds: float) -> "OllamaClient":
        model = (
            os.getenv("OLLAMA_MODEL", "").strip()
            or os.getenv("OPENAI_MODEL", "").strip()
        )
        if not model:
            raise RuntimeError("Missing required environment variable: OLLAMA_MODEL")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        think = os.getenv("OLLAMA_THINK", "false").strip().lower() in {"1", "true", "yes"}
        return cls(
            model=model,
            base_url=base_url,
            retry_times=retry_times,
            retry_sleep_seconds=retry_sleep_seconds,
            think=think,
        )

    def call_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": self.think,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(1, self.retry_times + 1):
            try:
                with self.opener.open(request, timeout=180) as response:
                    parsed = json.loads(response.read().decode("utf-8"))
                message = parsed.get("message") if isinstance(parsed, dict) else None
                if isinstance(message, dict):
                    return str(message.get("content", "")).strip()
                return ""
            except (OSError, URLError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.retry_times:
                    time.sleep(self.retry_sleep_seconds)
        raise RuntimeError(f"Ollama call failed after {self.retry_times} attempt(s): {last_error}")


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
        self.base_url = base_url
        self.retry_times = max(1, retry_times)
        self.retry_sleep_seconds = retry_sleep_seconds
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The OpenAI backend requires the openai package. "
                "Use LLM_BACKEND=ollama for local Ollama, or install requirements.txt."
            ) from exc
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    @classmethod
    def from_env(cls, retry_times: int, retry_sleep_seconds: float) -> "LLMClient | OllamaClient":
        backend = os.getenv("LLM_BACKEND", "openai").strip().lower()
        if backend == "ollama":
            return OllamaClient.from_env(retry_times, retry_sleep_seconds)
        if backend != "openai":
            raise RuntimeError(f"Unsupported LLM_BACKEND: {backend}")

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
