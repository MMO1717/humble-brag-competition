from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .embedding_client import EmbeddingClient
from .io_utils import load_jsonl


TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: Any) -> set[str]:
    return set(TOKEN_RE.findall(str(value or "").lower()))


def _jaccard(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _task_text(
    task: str,
    row: dict[str, Any],
    state: dict[str, Any] | None = None,
) -> str:
    state = state or {}
    fields = [
        row.get("speaker_post", ""),
        row.get("platform", ""),
        row.get("relationship", ""),
        row.get("agent_role", ""),
        row.get("interaction_goal", ""),
    ]
    if task in {"strategy", "response"}:
        fields.append(state.get("bragging_mechanism", ""))
    if task == "response":
        fields.append(state.get("response_strategy", ""))
    return " ".join(str(value) for value in fields)


@dataclass(frozen=True)
class ScoredExample:
    index: int
    score: float
    lexical_score: float
    semantic_score: float
    matched_fields: tuple[str, ...]


class FewShotRetriever:
    """从训练集检索示例，支持 embedding、hybrid 和 Jaccard。"""

    def __init__(
        self,
        train_path: Path,
        task_k: dict[str, int],
        save_logs: bool,
        mode: str = "embedding",
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self.train_path = train_path
        self.train_rows = load_jsonl(train_path)
        self.task_k = task_k
        self.save_logs = save_logs
        self.requested_mode = mode if mode in {"embedding", "hybrid", "jaccard"} else "jaccard"
        self.effective_mode = self.requested_mode
        self.fallback_reason = ""
        self.embedding_client = embedding_client
        self.embedding_model = (
            embedding_client.model if embedding_client is not None else None
        )
        self._train_embedding_cache: dict[str, list[list[float]]] = {}
        self._query_embedding_cache: dict[tuple[str, str], list[float]] = {}
        self.logs: list[dict[str, Any]] = []

    def _fallback_to_jaccard(self, exc: Exception) -> None:
        self.effective_mode = "jaccard"
        self.fallback_reason = str(exc)
        self.embedding_client = None
        self._train_embedding_cache.clear()
        self._query_embedding_cache.clear()
        print(
            f"[WARN] embedding few-shot 不可用，已自动切换 Jaccard：{exc}",
            flush=True,
        )

    def _embedding_scores(
        self,
        task: str,
        query: str,
    ) -> list[float]:
        if self.embedding_client is None:
            raise RuntimeError("未配置 embedding 客户端")
        if task not in self._train_embedding_cache:
            candidate_texts = [
                _task_text(task, candidate, candidate)
                for candidate in self.train_rows
            ]
            self._train_embedding_cache[task] = self.embedding_client.embed(
                candidate_texts
            )
        cache_key = (task, query)
        if cache_key not in self._query_embedding_cache:
            self._query_embedding_cache[cache_key] = self.embedding_client.embed(
                [query]
            )[0]
        query_vector = self._query_embedding_cache[cache_key]
        return [
            _cosine(query_vector, vector)
            for vector in self._train_embedding_cache[task]
        ]

    def _field_bonus(
        self,
        task: str,
        row: dict[str, Any],
        candidate: dict[str, Any],
        state: dict[str, Any],
    ) -> tuple[float, tuple[str, ...]]:
        weights = {
            "platform": 0.08,
            "relationship": 0.08,
            "agent_role": 0.04,
            "interaction_goal": 0.10,
        }
        score = 0.0
        matched: list[str] = []
        for field, weight in weights.items():
            if row.get(field) and row.get(field) == candidate.get(field):
                score += weight
                matched.append(field)
        if task in {"strategy", "response"}:
            if state.get("bragging_mechanism") == candidate.get("bragging_mechanism"):
                score += 0.16
                matched.append("bragging_mechanism")
        if task == "response":
            if state.get("response_strategy") == candidate.get("response_strategy"):
                score += 0.20
                matched.append("response_strategy")
        return score, tuple(matched)

    def get_examples(
        self,
        row: dict[str, Any],
        task: str,
        state: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if task not in {"mechanism", "strategy", "response"}:
            return []
        k = max(0, int(self.task_k.get(task, 0)))
        if k == 0:
            return []

        current_state = state or {}
        query = _task_text(task, row, current_state)
        semantic_scores = [0.0] * len(self.train_rows)
        mode = self.effective_mode
        if mode in {"embedding", "hybrid"}:
            try:
                semantic_scores = self._embedding_scores(task, query)
            except Exception as exc:
                self._fallback_to_jaccard(exc)
                mode = "jaccard"

        scored: list[ScoredExample] = []
        for index, candidate in enumerate(self.train_rows):
            lexical = _jaccard(query, _task_text(task, candidate, candidate))
            semantic = semantic_scores[index]
            bonus, matched = self._field_bonus(
                task, row, candidate, current_state
            )
            if mode == "embedding":
                retrieval_score = semantic
            elif mode == "hybrid":
                retrieval_score = 0.7 * semantic + 0.3 * lexical
            else:
                retrieval_score = lexical
            scored.append(
                ScoredExample(
                    index,
                    retrieval_score + bonus,
                    lexical,
                    semantic,
                    matched,
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)

        examples: list[dict[str, Any]] = []
        for rank, item in enumerate(scored[:k], start=1):
            candidate = dict(self.train_rows[item.index])
            candidate["_fewshot_meta"] = {
                "rank": rank,
                "score": round(item.score, 4),
                "lexical_score": round(item.lexical_score, 4),
                "semantic_score": round(item.semantic_score, 4),
                "retrieval_mode": mode,
                "matched_fields": list(item.matched_fields),
            }
            examples.append(candidate)

        if self.save_logs:
            self.logs.append(
                {
                    "episode_id": row.get("episode_id"),
                    "task": task,
                    "effective_mode": self.effective_mode,
                    "fallback_reason": self.fallback_reason,
                    "selected_examples": examples,
                }
            )
        return examples


def build_fewshot_retriever(cfg: Any) -> FewShotRetriever | None:
    """按配置创建 few-shot 检索器。"""
    if not getattr(cfg, "USE_FEWSHOT", False):
        return None
    train_path = Path(cfg.TRAIN_PATH)
    if not train_path.exists():
        print(
            f"[WARN] 训练集不存在，已关闭 few-shot：{train_path}",
            flush=True,
        )
        return None
    requested_mode = str(
        getattr(cfg, "FEWSHOT_RETRIEVAL_MODE", "embedding")
    ).strip().lower()
    effective_mode = requested_mode
    embedding_client: EmbeddingClient | None = None
    fallback_reason = ""
    if requested_mode in {"embedding", "hybrid"}:
        try:
            embedding_client = EmbeddingClient.from_env(
                batch_size=int(
                    getattr(cfg, "FEWSHOT_EMBEDDING_BATCH_SIZE", 64)
                )
            )
        except Exception as exc:
            fallback_reason = str(exc)
            effective_mode = "jaccard"
            print(
                f"[WARN] embedding few-shot 初始化失败，已自动切换 Jaccard：{exc}",
                flush=True,
            )

    retriever = FewShotRetriever(
        train_path=train_path,
        task_k=dict(getattr(cfg, "FEWSHOT_TASK_K", {})),
        save_logs=bool(getattr(cfg, "SAVE_FEWSHOT_LOGS", False)),
        mode=effective_mode,
        embedding_client=embedding_client,
    )
    retriever.requested_mode = requested_mode
    retriever.fallback_reason = fallback_reason
    return retriever
