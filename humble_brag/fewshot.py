from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import load_jsonl


TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: Any) -> set[str]:
    return set(TOKEN_RE.findall(str(text or "").lower()))


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


@dataclass(frozen=True)
class FewShotExample:
    row: dict[str, Any]
    score: float


class FewShotRetriever:
    def __init__(
        self,
        train_rows: list[dict[str, Any]],
        k: int,
        min_score: float,
        include_fields: bool,
    ) -> None:
        self.train_rows = train_rows
        self.k = max(0, int(k))
        self.min_score = float(min_score)
        self.include_fields = include_fields
        self._post_tokens = [_tokens(row.get("speaker_post", "")) for row in train_rows]

    def score(self, row: dict[str, Any], candidate: dict[str, Any], index: int) -> float:
        current_tokens = _tokens(row.get("speaker_post", ""))
        candidate_tokens = self._post_tokens[index]
        score = 2.0 * _jaccard(current_tokens, candidate_tokens)

        if row.get("platform") == candidate.get("platform"):
            score += 0.5
        if row.get("relationship") == candidate.get("relationship"):
            score += 0.3
        if row.get("agent_role") == candidate.get("agent_role"):
            score += 0.2
        if row.get("interaction_goal") == candidate.get("interaction_goal"):
            score += 0.5
        elif _tokens(row.get("interaction_goal", "")) & _tokens(candidate.get("interaction_goal", "")):
            score += 0.2

        return score

    def get_examples(self, row: dict[str, Any], task: str) -> list[dict[str, Any]]:
        if self.k <= 0:
            return []

        scored: list[FewShotExample] = []
        for index, candidate in enumerate(self.train_rows):
            score = self.score(row, candidate, index)
            if score >= self.min_score:
                scored.append(FewShotExample(row=candidate, score=score))

        scored.sort(key=lambda item: item.score, reverse=True)
        return [
            self._public_example(item.row, item.score, task)
            for item in scored[: self.k]
        ]

    def _public_example(self, row: dict[str, Any], score: float, task: str) -> dict[str, Any]:
        example: dict[str, Any] = {
            "speaker_post": row.get("speaker_post", ""),
            "score": round(score, 4),
        }
        if self.include_fields:
            example.update(
                {
                    "platform": row.get("platform", ""),
                    "relationship": row.get("relationship", ""),
                    "agent_role": row.get("agent_role", ""),
                    "interaction_goal": row.get("interaction_goal", ""),
                }
            )

        if task == "mechanism":
            example["bragging_mechanism"] = row.get("bragging_mechanism", "")
        elif task == "response":
            example.update(
                {
                    "bragging_mechanism": row.get("bragging_mechanism", ""),
                    "response_strategy": row.get("response_strategy", ""),
                    "response_text": row.get("response_text", ""),
                }
            )
        return example


def build_fewshot_retriever(
    use_fewshot: bool,
    train_path: str | Path | None = None,
    k: int = 3,
    min_score: float = 0.0,
    include_fields: bool = True,
) -> FewShotRetriever | None:
    if not use_fewshot:
        return None

    if train_path is None:
        return None

    path = Path(train_path)
    try:
        rows = load_jsonl(path)
    except Exception as exc:
        print(f"Few-shot 训练集读取失败，已自动关闭: {path} ({exc})")
        return None

    if not rows:
        print(f"Few-shot 训练集为空，已自动关闭: {path}")
        return None

    return FewShotRetriever(
        train_rows=rows,
        k=k,
        min_score=min_score,
        include_fields=include_fields,
    )
