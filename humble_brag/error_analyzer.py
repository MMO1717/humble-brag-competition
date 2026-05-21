from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .io_utils import load_jsonl, write_jsonl


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

RISK_KEYWORDS = {
    "sycophancy": [
        "sycophancy", "sycophantic", "overpraise", "over-praise",
        "excessive praise", "blind validation", "flattery",
    ],
    "preachiness": [
        "preach", "preachy", "moralize", "moralizing", "lecture", "judgmental",
    ],
    "misrecognition": [
        "misrecognition", "misread", "misinterpret", "false assumption",
        "assume expertise", "unsupported assumption",
    ],
    "strategy_inconsistency": [
        "strategy inconsistency", "inconsistent strategy", "mismatch",
        "does not match the strategy",
    ],
    "context_insensitivity": [
        "context insensitivity", "context insensitive", "ignore the context",
        "miss the context", "audience", "setting",
    ],
    "over_coldness": [
        "over cold", "over-cold", "too cold", "dismissive", "curt", "coldness",
    ],
}


def normalize_tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(str(text or "").lower())


def token_f1(prediction: str, gold: str) -> float:
    pred_tokens = normalize_tokens(prediction)
    gold_tokens = normalize_tokens(gold)
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0

    gold_counts: dict[str, int] = {}
    for token in gold_tokens:
        gold_counts[token] = gold_counts.get(token, 0) + 1

    overlap = 0
    for token in pred_tokens:
        if gold_counts.get(token, 0) > 0:
            gold_counts[token] -= 1
            overlap += 1

    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def extract_risk_labels(text: str) -> set[str]:
    lowered = str(text or "").lower()
    labels: set[str] = set()
    for label, keywords in RISK_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            labels.add(label)
    return labels


def set_f1(predicted: set[str], gold: set[str]) -> float:
    if not predicted and not gold:
        return 1.0
    if not predicted or not gold:
        return 0.0
    overlap = len(predicted & gold)
    precision = overlap / len(predicted)
    recall = overlap / len(gold)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _load_jsonl_by_id(path: Path) -> dict[str, dict[str, Any]]:
    return {row["episode_id"]: row for row in load_jsonl(path)}


def _strategy_score(predicted: str, gold: dict[str, Any]) -> float:
    if predicted == gold.get("preferred_strategy"):
        return 1.0
    if predicted in gold.get("acceptable_strategies", []):
        return 0.5
    return 0.0


def build_error_cases(
    dev_input_path: Path,
    dev_gold_path: Path,
    submission_path: Path,
    trace_path: Path | None,
    top_k: int,
) -> list[dict[str, Any]]:
    inputs = _load_jsonl_by_id(dev_input_path)
    golds = _load_jsonl_by_id(dev_gold_path)
    submissions = _load_jsonl_by_id(submission_path)
    traces = _load_jsonl_by_id(trace_path) if trace_path and trace_path.exists() else {}

    cases: list[dict[str, Any]] = []
    for episode_id, pred in submissions.items():
        gold = golds[episode_id]
        input_row = inputs[episode_id]

        mechanism_score = 1.0 if pred["bragging_mechanism"] == gold["gold_bragging_mechanism"] else 0.0
        strategy_score = _strategy_score(pred["response_strategy"], gold)
        predicted_risks = extract_risk_labels(pred["risk_assessment"])
        gold_risks = set(gold.get("gold_risk_labels", []))
        risk_score = set_f1(predicted_risks, gold_risks)
        response_score = token_f1(pred["response_text"], gold["reference_response"])
        intention_score = token_f1(pred["speaker_intention"], gold["gold_speaker_intention"])
        feedback_score = token_f1(pred["desired_feedback"], gold["gold_desired_feedback"])

        weighted_score = (
            0.30 * mechanism_score
            + 0.20 * strategy_score
            + 0.20 * risk_score
            + 0.15 * response_score
            + 0.075 * intention_score
            + 0.075 * feedback_score
        )
        error_score = round(1.0 - weighted_score, 4)

        cases.append(
            {
                "episode_id": episode_id,
                "error_score": error_score,
                "scores": {
                    "mechanism": round(mechanism_score, 4),
                    "strategy": round(strategy_score, 4),
                    "risk": round(risk_score, 4),
                    "response": round(response_score, 4),
                    "speaker_intention": round(intention_score, 4),
                    "desired_feedback": round(feedback_score, 4),
                },
                "input": input_row,
                "prediction": pred,
                "gold": gold,
                "trace": traces.get(episode_id, {}),
            }
        )

    cases.sort(key=lambda item: item["error_score"], reverse=True)
    return cases[: max(0, int(top_k))]


def _compact_case_for_llm(case: dict[str, Any]) -> dict[str, Any]:
    gold = case["gold"]
    pred = case["prediction"]
    return {
        "episode_id": case["episode_id"],
        "error_score": case["error_score"],
        "scores": case["scores"],
        "speaker_post": case["input"].get("speaker_post", ""),
        "context": {
            "platform": case["input"].get("platform", ""),
            "relationship": case["input"].get("relationship", ""),
            "agent_role": case["input"].get("agent_role", ""),
            "interaction_goal": case["input"].get("interaction_goal", ""),
        },
        "prediction": {
            "bragging_mechanism": pred.get("bragging_mechanism"),
            "risk_assessment": pred.get("risk_assessment"),
            "response_strategy": pred.get("response_strategy"),
            "response_text": pred.get("response_text"),
        },
        "gold": {
            "bragging_mechanism": gold.get("gold_bragging_mechanism"),
            "risk_labels": gold.get("gold_risk_labels", []),
            "preferred_strategy": gold.get("preferred_strategy"),
            "acceptable_strategies": gold.get("acceptable_strategies", []),
            "reference_response": gold.get("reference_response"),
        },
        "raw_outputs": case.get("trace", {}).get("raw_outputs", {}),
    }


def _analysis_messages(cases: list[dict[str, Any]]) -> list[dict[str, str]]:
    payload = [_compact_case_for_llm(case) for case in cases]
    return [
        {
            "role": "system",
            "content": (
                "You are analyzing errors in a BRAG-Agent dev run. "
                "Write concise diagnostics for prompt and rule improvement. "
                "Do not rewrite the submission; only explain likely causes and actionable fixes."
            ),
        },
        {
            "role": "user",
            "content": (
                "Analyze these high-error cases. For each case, identify the main error type, "
                "why the prediction differs from gold, and one concrete improvement suggestion. "
                "Then give 3 overall improvement priorities.\n\n"
                f"{json.dumps(payload, ensure_ascii=False)}"
            ),
        },
    ]


def _write_error_report(path: Path, cases: list[dict[str, Any]], llm_reviews: list[str]) -> None:
    lines = [
        "# Dev 错误分析",
        "",
        "## 高错误样本",
        "",
    ]
    for case in cases:
        lines.extend(
            [
                f"### {case['episode_id']}",
                "",
                f"- error_score：`{case['error_score']}`",
                f"- scores：`{json.dumps(case['scores'], ensure_ascii=False)}`",
                f"- mechanism：`{case['prediction']['bragging_mechanism']}` -> gold `{case['gold']['gold_bragging_mechanism']}`",
                f"- strategy：`{case['prediction']['response_strategy']}` -> preferred `{case['gold']['preferred_strategy']}`",
                f"- risk：`{case['prediction']['risk_assessment']}` -> gold `{case['gold'].get('gold_risk_labels', [])}`",
                f"- response：{case['prediction']['response_text']}",
                f"- reference：{case['gold']['reference_response']}",
                "",
            ]
        )

    if llm_reviews:
        lines.extend(["## LLM 错误总结", ""])
        for index, review in enumerate(llm_reviews, start=1):
            lines.extend([f"### Batch {index}", "", review.strip(), ""])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_dev_error_analysis(
    *,
    llm_client: Any,
    run_dir: Path,
    dev_input_path: Path,
    dev_gold_path: Path,
    submission_path: Path,
    trace_path: Path | None,
    memory_dir: Path | None = None,
    top_k: int = 10,
    use_llm: bool = True,
    generate_candidates: bool = False,
) -> dict[str, Any] | None:
    output_dir = run_dir / "error_analysis"
    cases_path = output_dir / "error_cases.jsonl"
    review_path = output_dir / "llm_error_review.jsonl"
    report_path = output_dir / "error_report.md"

    cases = build_error_cases(
        dev_input_path=dev_input_path,
        dev_gold_path=dev_gold_path,
        submission_path=submission_path,
        trace_path=trace_path,
        top_k=top_k,
    )
    write_jsonl(cases_path, cases)

    llm_reviews: list[str] = []
    review_rows: list[dict[str, Any]] = []
    if use_llm and cases and llm_client:
        batch_size = 5
        for start in range(0, len(cases), batch_size):
            batch = cases[start : start + batch_size]
            try:
                review = llm_client.call_chat(
                    _analysis_messages(batch),
                    temperature=0.2,
                    max_tokens=1200,
                )
                llm_reviews.append(review)
                review_rows.append(
                    {
                        "batch_index": len(review_rows) + 1,
                        "episode_ids": [case["episode_id"] for case in batch],
                        "review": review,
                        "error": None,
                    }
                )
            except Exception as exc:
                review_rows.append(
                    {
                        "batch_index": len(review_rows) + 1,
                        "episode_ids": [case["episode_id"] for case in batch],
                        "review": "",
                        "error": str(exc),
                    }
                )
        write_jsonl(review_path, review_rows)

    _write_error_report(report_path, cases, llm_reviews)

    result: dict[str, Any] = {
        "error_cases_path": str(cases_path),
        "llm_error_review_path": str(review_path) if review_rows else None,
        "error_report_path": str(report_path),
        "case_count": len(cases),
        "llm_review_count": len(llm_reviews),
    }

    if generate_candidates and memory_dir and cases:
        from .memory_candidate_generator import generate_candidate_memories
        candidate_report = generate_candidate_memories(
            llm_client=llm_client,
            run_id=run_dir.name,
            cases=cases,
            memory_dir=memory_dir,
        )
        result["candidate_memory"] = candidate_report

    return result
