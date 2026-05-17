#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_no_overfit_stress_set import build_rows
from src.postprocess import abstract_response_fallback, normalize_risk_assessment
from src.social_rubric import judge_row
from src.strategy_rules import choose_strategy
from src.validators import validate_output


OUTPUT_FIELDS = (
    "episode_id",
    "bragging_mechanism",
    "speaker_intention",
    "desired_feedback",
    "risk_assessment",
    "response_strategy",
    "response_text",
)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def assert_strategy_examples() -> list[str]:
    failures: list[str] = []
    examples = [
        (
            {
                "platform": "workplace_channel",
                "relationship": "supervisor",
                "interaction_goal": "stay_professional_and_avoid_sycophancy",
                "speaker_post": "I usually solve this faster than others.",
            },
            "comparison_superiority",
            "redirect",
        ),
        (
            {
                "platform": "public_social_media",
                "relationship": "online_peer",
                "interaction_goal": "stay_neutral",
                "speaker_post": "The result was better than expected.",
            },
            "understated_flex",
            "neutral_observation",
        ),
        (
            {
                "platform": "direct_message",
                "relationship": "acquaintance",
                "interaction_goal": "avoid_sycophancy",
                "speaker_post": "Not sure how the result landed so well.",
            },
            "faux_modesty",
            "ask_followup",
        ),
        (
            {
                "platform": "group_chat",
                "relationship": "close_friend",
                "interaction_goal": "be_supportive_without_overpraising",
                "speaker_post": "Tiny brag, the plan worked.",
            },
            "self_aware_brag",
            "humor_tease",
        ),
    ]
    for row, mechanism, expected in examples:
        actual = choose_strategy(row, mechanism, {})
        if actual != expected:
            failures.append(f"strategy expected {expected}, got {actual} for {mechanism}")
    return failures


def assert_risk_examples() -> list[str]:
    failures: list[str] = []
    text = normalize_risk_assessment(
        "",
        input_row={
            "platform": "workplace_channel",
            "relationship": "supervisor",
            "interaction_goal": "stay_professional_and_avoid_sycophancy",
        },
        strategy="neutral_observation",
    ).lower()
    for keyword in ("misrecognition", "context_insensitivity", "sycophancy"):
        if keyword not in text:
            failures.append(f"risk text missing {keyword}")
    return failures


def assert_judge_examples() -> list[str]:
    failures: list[str] = []
    input_row = {
        "platform": "workplace_channel",
        "relationship": "supervisor",
        "interaction_goal": "stay_professional_and_avoid_sycophancy",
    }
    outputs = [
        {
            "response_strategy": "neutral_observation",
            "response_text": "That is amazing and incredible work.",
        },
        {
            "response_strategy": "ask_followup",
            "response_text": "That is useful context.",
        },
        {
            "response_strategy": "neutral_observation",
            "response_text": "You should stop showing off and be humble.",
        },
    ]
    for output in outputs:
        judged = judge_row(input_row, output)
        if not judged["hard_issues"]:
            failures.append(f"judge missed hard issue for {output['response_text']}")
    return failures


def build_stress_submission(stress_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    input_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []
    for row in stress_rows:
        input_row = {
            key: row[key]
            for key in ("episode_id", "speaker_post", "platform", "relationship", "agent_role", "interaction_goal")
        }
        mechanism = str(row["expected_mechanism"])
        strategy = choose_strategy(input_row, mechanism, {})
        risk = normalize_risk_assessment("", input_row=input_row, strategy=strategy)
        response = abstract_response_fallback(strategy, mechanism, input_row)
        output_row = {
            "episode_id": input_row["episode_id"],
            "bragging_mechanism": mechanism,
            "speaker_intention": "The speaker is presenting themselves positively through a generalized social pattern.",
            "desired_feedback": "They likely want measured acknowledgment without excessive praise.",
            "risk_assessment": risk,
            "response_strategy": strategy,
            "response_text": response,
        }
        validate_output(output_row, input_row)
        judged = judge_row(input_row, output_row)
        if judged["hard_issues"]:
            raise AssertionError(f"{input_row['episode_id']} hard issues: {judged['hard_issues']}")
        input_rows.append(input_row)
        output_rows.append({field: output_row[field] for field in OUTPUT_FIELDS})
    return input_rows, output_rows


def write_report(report_path: Path, output_rows: list[dict[str, Any]], failures: list[str]) -> None:
    counter = Counter(row["response_text"] for row in output_rows)
    strategy_counts = Counter(row["response_strategy"] for row in output_rows)
    lines = [
        "# BRAG-Pipeline no-overfit 离线检查报告",
        "",
        "## 摘要",
        "",
        f"- stress rows: {len(output_rows)}",
        f"- unique responses: {len(counter)}",
        f"- most frequent response count: {counter.most_common(1)[0][1] if counter else 0}",
        f"- failures: {len(failures)}",
        "",
        "## Strategy 分布",
        "",
        "| Strategy | Count |",
        "|---|---:|",
    ]
    for strategy, count in sorted(strategy_counts.items()):
        lines.append(f"| `{strategy}` | {count} |")
    lines.extend(["", "## 失败项", ""])
    if failures:
        lines.extend(f"- {failure}" for failure in failures)
    else:
        lines.append("- none")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    out_dir = ROOT / "outputs" / "no_overfit_offline"
    failures = []
    failures.extend(assert_strategy_examples())
    failures.extend(assert_risk_examples())
    failures.extend(assert_judge_examples())

    stress_rows = build_rows()
    input_rows, output_rows = build_stress_submission(stress_rows)
    write_jsonl(out_dir / "stress_input.jsonl", input_rows)
    write_jsonl(out_dir / "stress_submission.jsonl", output_rows)
    write_report(out_dir / "offline_check_report.md", output_rows, failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)
    print(f"Offline checks passed. Wrote reports to {out_dir}")


if __name__ == "__main__":
    main()
