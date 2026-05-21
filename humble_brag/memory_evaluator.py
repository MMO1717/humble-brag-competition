from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_memory_eval_record(
    *,
    memory_dir: Path,
    run_id: str,
    manifest: dict[str, Any],
    dev_report: dict[str, Any],
    format_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    eval_dir = memory_dir / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    record_path = eval_dir / "memory_eval_runs.jsonl"
    summary_path = eval_dir / "memory_ablation_summary.md"

    metrics = {}
    parsed = dev_report.get("parsed_stdout_json") if isinstance(dev_report, dict) else None
    if isinstance(parsed, dict):
        metrics = parsed.get("proxy_metrics", {}) or {}
    format_valid = None
    parsed_format = (format_report or {}).get("parsed_stdout_json") if isinstance(format_report, dict) else None
    if isinstance(parsed_format, dict):
        format_valid = parsed_format.get("valid")

    record = {
        "run_id": run_id,
        "memory_mode": manifest.get("memory_mode"),
        "use_agent_memory": manifest.get("use_agent_memory"),
        "memory_top_k_per_skill": manifest.get("memory_top_k_per_skill"),
        "active_memory_count": manifest.get("active_memory_count"),
        "candidate_memory_count": manifest.get("candidate_memory_count"),
        "static_memory_count": manifest.get("static_memory_count"),
        "memory_used_count": manifest.get("memory_used_count"),
        "model": manifest.get("model"),
        "max_items": manifest.get("max_items"),
        "metrics": metrics,
        "format_valid": format_valid,
    }

    with record_path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    _write_summary(summary_path, record_path)
    return {
        "memory_eval_record_path": str(record_path),
        "memory_ablation_summary_path": str(summary_path),
    }


def _write_summary(summary_path: Path, record_path: Path) -> None:
    rows = []
    if record_path.exists():
        for line in record_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))

    lines = ["# Memory 消融实验摘要", ""]
    for row in rows[-20:]:
        metrics = row.get("metrics", {})
        lines.append(
            "- "
            f"`{row.get('run_id')}` | mode=`{row.get('memory_mode')}` | "
            f"score=`{metrics.get('proxy_dev_score')}` | "
            f"mechanism=`{metrics.get('mechanism_accuracy')}` | "
            f"strategy=`{metrics.get('strategy_score')}` | "
            f"risk=`{metrics.get('risk_label_f1_from_risk_assessment')}` | "
            f"response=`{metrics.get('response_reference_token_f1')}` | "
            f"format=`{row.get('format_valid')}` | "
            f"memory_used=`{row.get('memory_used_count')}`"
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
