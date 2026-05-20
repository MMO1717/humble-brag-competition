from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .baseline import generate_baseline_row
from .io_utils import load_jsonl, read_json_from_stdout, write_json, write_jsonl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA_DIR = PROJECT_ROOT / "reference" / "BRAG-Agent-public" / "data"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def model_slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name).strip("_") or "baseline"


def default_input_path(mode: str) -> Path:
    if mode == "dev":
        return PUBLIC_DATA_DIR / "dev_input.jsonl"
    if mode == "test":
        return PUBLIC_DATA_DIR / "test_input.jsonl"
    raise ValueError(f"unsupported mode: {mode}")


def run_command(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=PROJECT_ROOT, text=True, capture_output=True)
    parsed = read_json_from_stdout(proc.stdout)
    return {
        "args": args,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "parsed_stdout_json": parsed,
    }


def write_res(run_dir: Path, manifest: dict[str, Any], format_report: dict[str, Any], dev_report: dict[str, Any] | None) -> None:
    fmt_json = format_report.get("parsed_stdout_json") or {}
    dev_json = (dev_report or {}).get("parsed_stdout_json") or {}
    metrics = dev_json.get("proxy_metrics") or {}

    lines = [
        "# Baseline Run Result",
        "",
        "## Summary",
        "",
        f"- run_id: `{manifest['run_id']}`",
        f"- mode: `{manifest['mode']}`",
        f"- input rows: `{manifest['input_rows']}`",
        f"- output rows: `{manifest['output_rows']}`",
        f"- format valid: `{fmt_json.get('valid')}`",
        f"- format errors: `{fmt_json.get('error_count')}`",
        f"- format warnings: `{fmt_json.get('warning_count')}`",
    ]

    if metrics:
        lines.extend(
            [
                f"- proxy_dev_score: `{metrics.get('proxy_dev_score')}`",
                f"- mechanism_accuracy: `{metrics.get('mechanism_accuracy')}`",
                f"- strategy_score: `{metrics.get('strategy_score')}`",
                f"- risk_label_f1: `{metrics.get('risk_label_f1_from_risk_assessment')}`",
                f"- response_reference_token_f1: `{metrics.get('response_reference_token_f1')}`",
            ]
        )
    else:
        lines.append("- proxy_dev_score: `not run`")

    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `submission.jsonl`: generated submission rows",
            "- `run_manifest.json`: run configuration and command status",
            "- `format_report.json`: local format checker output",
            "- `dev_eval_report.json`: dev proxy score output when mode is dev",
        ]
    )
    (run_dir / "RES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(mode: str, max_items: int | None = None, input_path: Path | None = None) -> Path:
    input_path = input_path or default_input_path(mode)
    rows = load_jsonl(input_path)
    if max_items is not None:
        rows = rows[:max_items]

    output_rows = [generate_baseline_row(row) for row in rows]

    count_label = f"max{max_items}" if max_items is not None else "full"
    run_id = f"{mode}__{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}__heuristic_baseline__{count_label}"
    run_dir = OUTPUT_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    submission_path = run_dir / "submission.jsonl"
    input_subset_path = run_dir / "input_subset.jsonl"
    write_jsonl(submission_path, output_rows)
    write_jsonl(input_subset_path, rows)

    format_input_path = input_subset_path if max_items is not None else input_path
    format_report = run_command(
        [
            sys.executable,
            str(SCRIPTS_DIR / "format_checker.py"),
            str(submission_path),
            str(format_input_path),
        ]
    )
    write_json(run_dir / "format_report.json", format_report)

    dev_report = None
    if mode == "dev":
        dev_report = run_command(
            [
                sys.executable,
                str(SCRIPTS_DIR / "evaluate_dev.py"),
                str(format_input_path),
                str(PUBLIC_DATA_DIR / "dev_gold.jsonl"),
                str(submission_path),
            ]
        )
        write_json(run_dir / "dev_eval_report.json", dev_report)

    manifest = {
        "run_id": run_id,
        "mode": mode,
        "input_path": str(input_path),
        "input_subset_path": str(input_subset_path),
        "submission_path": str(submission_path),
        "input_rows": len(rows),
        "output_rows": len(output_rows),
        "max_items": max_items,
        "generator": "heuristic_baseline",
        "format_returncode": format_report["returncode"],
        "dev_eval_returncode": None if dev_report is None else dev_report["returncode"],
    }
    write_json(run_dir / "run_manifest.json", manifest)
    write_res(run_dir, manifest, format_report, dev_report)

    if format_report["returncode"] != 0:
        raise RuntimeError(f"format check failed; see {run_dir / 'format_report.json'}")
    if dev_report is not None and dev_report["returncode"] != 0:
        raise RuntimeError(f"dev evaluation failed; see {run_dir / 'dev_eval_report.json'}")

    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the heuristic baseline pipeline.")
    parser.add_argument("--mode", choices=["dev", "test"], default="dev")
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--input-path", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = run_pipeline(mode=args.mode, max_items=args.max_items, input_path=args.input_path)
    print(run_dir)


if __name__ == "__main__":
    main()

