from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List
from urllib.request import Request, build_opener, ProxyHandler


def _detect_ollama_model() -> str:
    """自动检测本地 Ollama 服务中第一个可用的模型名称"""
    try:
        req = Request("http://localhost:11434/api/tags", method="GET")
        # 排除代理干扰
        opener = build_opener(ProxyHandler({}))
        with opener.open(req, timeout=3.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
        models = res_data.get("models", [])
        if models:
            return str(models[0].get("name", "qwen3:8b"))
    except Exception:
        pass
    return "qwen3:8b"


class LLMClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        # 兼容读取环境变量，如果不存在则使用本地默认值
        self.base_url = (
            base_url
            or os.getenv("LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
        )
        self.api_key = (
            api_key
            or os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        self.model = (
            model
            or os.getenv("LLM_MODEL")
            or os.getenv("OPENAI_MODEL")
        )

        # 智能探测本地 Ollama
        is_local_ollama_running = False
        try:
            req = Request("http://localhost:11434/", method="GET")
            opener = build_opener(ProxyHandler({}))
            with opener.open(req, timeout=2.0) as response:
                if response.status == 200:
                    is_local_ollama_running = True
        except Exception:
            pass

        if not self.base_url:
            if is_local_ollama_running:
                self.base_url = "http://localhost:11434/v1"
            else:
                self.base_url = "http://localhost:5001/v1"

        if not self.api_key:
            self.api_key = "sk-local"

        if not self.model:
            if is_local_ollama_running:
                self.model = _detect_ollama_model()
            else:
                self.model = "your-model-name"

        try:
            self.timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", str(timeout)))
        except ValueError:
            self.timeout = timeout

        try:
            self.max_retries = int(os.getenv("LLM_MAX_RETRIES", str(max_retries)))
        except ValueError:
            self.max_retries = max_retries

        # 尝试实例化 openai 官方 SDK 客户端以实现标准的 API 功能
        self.use_openai_lib = False
        try:
            import openai
            self.client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key)
            self.use_openai_lib = True
        except (ImportError, AttributeError):
            self.client = None

    def call_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 256,
    ) -> str:
        """调用大模型聊天接口，带异常重试与超时保障"""
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if self.use_openai_lib and self.client:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,  # type: ignore
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=self.timeout,
                    )
                    return (response.choices[0].message.content or "").strip()
                else:
                    # 原生 urllib 降级实现，彻底避免包依赖问题
                    payload = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": False,
                    }
                    headers = {
                        "Content-Type": "application/json",
                    }
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"

                    req = Request(
                        f"{self.base_url.rstrip('/')}/chat/completions",
                        data=json.dumps(payload).encode("utf-8"),
                        headers=headers,
                        method="POST",
                    )
                    opener = build_opener(ProxyHandler({}))
                    with opener.open(req, timeout=self.timeout) as response:
                        res_data = json.loads(response.read().decode("utf-8"))

                    choices = res_data.get("choices", [])
                    if choices:
                        return str(choices[0].get("message", {}).get("content", "") or "").strip()
                    return ""
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(1.0 * attempt)

        raise RuntimeError(f"LLM call failed after {self.max_retries} attempt(s): {last_error}")
