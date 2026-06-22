#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_DIR / "scripts"
for path in (PROJECT_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from format_checker import load_expected_episode_ids, validate_submission_rows
from src.judges.local_official_like import evaluate_output_rows


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate outputs with a local Core/Bloom-like heuristic judge."
    )
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("submission_jsonl", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the JSON report.",
    )
    args = parser.parse_args()

    input_rows = load_jsonl(args.input_jsonl)
    output_rows = load_jsonl(args.submission_jsonl)
    format_report = validate_submission_rows(
        output_rows,
        load_expected_episode_ids(args.input_jsonl),
    )
    report = {
        "submission": str(args.submission_jsonl),
        "input": str(args.input_jsonl),
        "valid_submission": format_report["valid"],
        "format_report": format_report,
        "local_official_like": evaluate_output_rows(input_rows, output_rows),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)

    if not format_report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
