from __future__ import annotations

import os
from typing import Iterable

from openai import OpenAI


class EmbeddingClient:
    """调用 OpenAI-compatible embeddings 接口。"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        batch_size: int = 64,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.batch_size = max(1, batch_size)
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=100.0)

    @classmethod
    def from_env(cls, batch_size: int = 64) -> "EmbeddingClient":
        """独立配置缺失时复用主 LLM 的地址、Key 和模型名。"""
        base_url = (
            os.getenv("FEWSHOT_EMBEDDING_BASE_URL", "").strip()
            or os.getenv("OPENAI_BASE_URL", "").strip()
        )
        api_key = (
            os.getenv("FEWSHOT_EMBEDDING_API_KEY", "").strip()
            or os.getenv("OPENAI_API_KEY", "").strip()
        )
        model = (
            os.getenv("FEWSHOT_EMBEDDING_MODEL", "").strip()
            or os.getenv("OPENAI_MODEL", "").strip()
        )
        missing = [
            name
            for name, value in {
                "embedding base URL": base_url,
                "embedding API key": api_key,
                "embedding model": model,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"缺少 embedding 配置：{', '.join(missing)}")
        return cls(base_url, api_key, model, batch_size)

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        """按批次生成向量，保持输入顺序不变。"""
        values = [str(text) for text in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(values), self.batch_size):
            batch = values[start : start + self.batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend([list(item.embedding) for item in ordered])
        return vectors
