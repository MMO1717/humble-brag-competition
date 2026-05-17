from __future__ import annotations

import http.client
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import OpenAI


def load_env(env_path: Path | None = None) -> None:
    if env_path is not None:
        load_dotenv(env_path)
    else:
        load_dotenv()


def _is_ollama(base_url: str) -> bool:
    """Detect whether base_url points to an Ollama server."""
    normalized = base_url.rstrip("/").lower()
    return (
        "localhost:11434" in normalized
        or "127.0.0.1:11434" in normalized
        or os.getenv("LLM_BACKEND", "").strip().lower() == "ollama"
    )


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
        self.use_ollama = _is_ollama(base_url)
        if self.use_ollama:
            # Strip /v1 suffix if present, then parse host/port/path.
            clean_url = base_url.rstrip("/")
            if clean_url.endswith("/v1"):
                clean_url = clean_url[:-3]
            parsed = urlparse(clean_url.rstrip("/") + "/api/chat")
            self._ollama_host = parsed.hostname or "127.0.0.1"
            self._ollama_port = parsed.port or 11434
            self._ollama_path = parsed.path or "/api/chat"
        else:
            self.client = OpenAI(base_url=base_url, api_key=api_key)

    @classmethod
    def from_env(cls, retry_times: int, retry_sleep_seconds: float) -> "LLMClient":
        base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        is_ollama = _is_ollama(base_url)
        # Ollama doesn't need a real API key.
        if is_ollama and not api_key:
            api_key = "ollama"
        required = {"OPENAI_BASE_URL": base_url, "OPENAI_MODEL": model}
        if not is_ollama:
            required["OPENAI_API_KEY"] = api_key
        missing = [name for name, value in required.items() if not value]
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

    # ------------------------------------------------------------------
    # Ollama native /api/chat
    # ------------------------------------------------------------------

    def _call_ollama(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "think": False,  # disable qwen3 thinking/reasoning output
        }
        body = json.dumps(payload).encode("utf-8")
        conn = http.client.HTTPConnection(
            self._ollama_host, self._ollama_port, timeout=120,
        )
        try:
            conn.request(
                "POST", self._ollama_path, body=body,
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            if resp.status != 200:
                raise RuntimeError(
                    f"Ollama returned HTTP {resp.status}: {resp.read().decode('utf-8', errors='replace')}"
                )
            data = json.loads(resp.read().decode("utf-8"))
        finally:
            conn.close()
        content = data.get("message", {}).get("content", "")
        return content.strip()

    # ------------------------------------------------------------------
    # OpenAI-compatible /v1/chat/completions
    # ------------------------------------------------------------------

    def _call_openai(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        return content.strip()

    # ------------------------------------------------------------------
    # Public entry point (with retry)
    # ------------------------------------------------------------------

    def call_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        backend = self._call_ollama if self.use_ollama else self._call_openai
        last_error: Exception | None = None
        for attempt in range(1, self.retry_times + 1):
            try:
                return backend(messages, temperature, max_tokens)
            except Exception as exc:
                last_error = exc
                if attempt < self.retry_times:
                    time.sleep(self.retry_sleep_seconds)
        raise RuntimeError(f"LLM call failed after {self.retry_times} attempt(s): {last_error}")
