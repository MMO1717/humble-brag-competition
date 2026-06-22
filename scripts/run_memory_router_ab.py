#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import config
from src.llm_client import load_env
from src.pipeline import run_pipeline


CONFIG_PATH = PROJECT_DIR / "config.py"
OUTPUTS_DIR = PROJECT_DIR / "outputs"
ROUTER_RE = re.compile(r'^MEMORY_ROUTER_MODE\s*=\s*["\']([^"\']+)["\'].*$', re.M)


@dataclass(frozen=True)
class RunScore:
    run_dir: Path
    router_mode: str
    proxy_score: float
    metrics: dict[str, Any]


def _metrics_from_report(report_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    metrics = report.get("parsed_stdout_json", {}).get("proxy_metrics")
    if not isinstance(metrics, dict):
        raise ValueError(f"{report_path} does not contain proxy_metrics")
    return metrics


def _router_mode_from_run(run_dir: Path) -> str:
    manifest_path = run_dir / "run_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mode = manifest.get("memory_router_mode")
        if isinstance(mode, str) and mode:
            return mode

    trace_path = run_dir / "debug" / "trace.jsonl"
    if trace_path.exists():
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            trace = json.loads(line)
            router_trace = trace.get("memory_router_trace") or {}
            for item in router_trace.values():
                if item.get("mode") == "llm_rerank":
                    return "llm_rerank"
        return "function"
    return "unknown"


def _collect_dev_scores() -> list[RunScore]:
    scores: list[RunScore] = []
    for report_path in sorted(OUTPUTS_DIR.glob("dev_*/dev_eval_report.json")):
        try:
            metrics = _metrics_from_report(report_path)
            proxy_score = float(metrics["proxy_dev_score"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        run_dir = report_path.parent
        scores.append(
            RunScore(
                run_dir=run_dir,
                router_mode=_router_mode_from_run(run_dir),
                proxy_score=proxy_score,
                metrics=metrics,
            )
        )
    return scores


def _latest_function_score() -> RunScore:
    candidates = [
        score for score in _collect_dev_scores() if score.router_mode == "function"
    ]
    if not candidates:
        raise RuntimeError(
            "No function-router baseline found. Pass --baseline-score explicitly."
        )
    return max(candidates, key=lambda score: score.run_dir.stat().st_mtime)


def _latest_run_after(before: set[Path]) -> Path:
    after = {path for path in OUTPUTS_DIR.glob("dev_*") if path.is_dir()}
    new_runs = sorted(after - before, key=lambda path: path.stat().st_mtime)
    if new_runs:
        return new_runs[-1]
    all_runs = sorted(after, key=lambda path: path.stat().st_mtime)
    if not all_runs:
        raise RuntimeError("No dev run directory found after pipeline execution.")
    return all_runs[-1]


def _set_default_router_mode(mode: str) -> None:
    text = CONFIG_PATH.read_text(encoding="utf-8")
    replacement = f'MEMORY_ROUTER_MODE = "{mode}"  # baseline / function / llm_rerank'
    updated, count = ROUTER_RE.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError("Could not find MEMORY_ROUTER_MODE in config.py")
    CONFIG_PATH.write_text(updated, encoding="utf-8")


def _run_llm_rerank_dev() -> RunScore:
    before = {path for path in OUTPUTS_DIR.glob("dev_*") if path.is_dir()}
    load_env(PROJECT_DIR / ".env")
    config.MEMORY_ROUTER_MODE = "llm_rerank"
    config.RUN_ERROR_ANALYSIS = False
    config.EFFECTIVE_ERROR_ANALYSIS = False
    config.EFFECTIVE_SAVE_ERROR_MEMORY = False
    config.SAVE_LLM_CALL_LOGS = True
    run_pipeline(config)

    run_dir = _latest_run_after(before)
    metrics = _metrics_from_report(run_dir / "dev_eval_report.json")
    return RunScore(
        run_dir=run_dir,
        router_mode=_router_mode_from_run(run_dir),
        proxy_score=float(metrics["proxy_dev_score"]),
        metrics=metrics,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run llm_rerank memory router on dev and keep it only if better."
    )
    parser.add_argument(
        "--baseline-score",
        type=float,
        default=None,
        help="Function-router baseline score. If omitted, latest function dev run is used.",
    )
    parser.add_argument(
        "--min-delta",
        type=float,
        default=0.001,
        help="Minimum proxy-score improvement required to keep llm_rerank.",
    )
    parser.add_argument(
        "--no-apply",
        action="store_true",
        help="Do not edit config.py; only print the decision.",
    )
    args = parser.parse_args()

    baseline = (
        None
        if args.baseline_score is not None
        else _latest_function_score()
    )
    baseline_score = (
        float(args.baseline_score)
        if args.baseline_score is not None
        else baseline.proxy_score
    )

    candidate = _run_llm_rerank_dev()
    delta = candidate.proxy_score - baseline_score
    keep = delta >= args.min_delta
    target_mode = "llm_rerank" if keep else "function"
    if not args.no_apply:
        _set_default_router_mode(target_mode)

    summary = {
        "baseline_score": round(baseline_score, 4),
        "baseline_run_dir": str(baseline.run_dir) if baseline else None,
        "candidate_score": round(candidate.proxy_score, 4),
        "candidate_run_dir": str(candidate.run_dir),
        "delta": round(delta, 4),
        "min_delta": args.min_delta,
        "keep_llm_rerank": keep,
        "config_updated": not args.no_apply,
        "default_router_mode": target_mode,
        "candidate_metrics": candidate.metrics,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
