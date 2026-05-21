from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .baseline import generate_baseline_row
from .io_utils import load_jsonl, read_json_from_stdout, write_json, write_jsonl
from .llm_client import LLMClient
from .prompts import SUPPORTED_PROMPT_VERSIONS, build_prompt, memory_version_for_prompt
from .json_repair import extract_and_parse_json
from .contract import ALLOWED_MECHANISMS, ALLOWED_STRATEGIES, normalize_output_row
from .strategy_rules import apply_strategy_rules



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

    trace_path = manifest.get("trace_path", "not generated")
    if trace_path != "not generated":
        try:
            trace_path = f"`{Path(trace_path).relative_to(PROJECT_ROOT)}`"
        except ValueError:
            trace_path = f"`{trace_path}`"

    lines = [
        "# Pipeline Run Result",
        "",
        "## Summary",
        "",
        f"- run_id: `{manifest['run_id']}`",
        f"- backend: `{manifest.get('backend', 'heuristic')}`",
        f"- prompt_version: `{manifest.get('prompt_version', 'n/a')}`",
        f"- memory_version: `{manifest.get('memory_version', 'n/a')}`",
        f"- use_skillflow: `{manifest.get('use_skillflow', False)}`",
        f"- mode: `{manifest['mode']}`",
        f"- input rows: `{manifest['input_rows']}`",
        f"- output rows: `{manifest['output_rows']}`",
        f"- format valid: `{fmt_json.get('valid')}`",
        f"- format errors: `{fmt_json.get('error_count')}`",
        f"- format warnings: `{fmt_json.get('warning_count')}`",
        f"- fallback count: `{manifest.get('fallback_count', 0)}`",
        f"- parse failure count: `{manifest.get('parse_failure_count', 0)}`",
        f"- invalid label count: `{manifest.get('invalid_label_count', 0)}`",
        f"- strategy_rules: `{manifest.get('strategy_rules', 'none')}`",
        f"- strategy_rule_applied_count: `{manifest.get('strategy_rule_applied_count', 0)}`",
        f"- skillflow_fallback_count: `{manifest.get('skillflow_fallback_count', 0)}`",
        f"- trace path: {trace_path}",
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
            "- `debug/trace.jsonl`: detailed execution trace for debugging",
        ]
    )
    (run_dir / "RES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(
    mode: str,
    max_items: int | None = None,
    input_path: Path | None = None,
    backend: str = "heuristic",
    prompt_version: str = "llm_a_minimal_v1",
    strategy_rules: str = "none",
    use_skillflow: bool = False,
    use_fewshot: bool = False,
    fewshot_k: int = 3,
) -> Path:
    if backend == "llm" and not use_skillflow and prompt_version not in SUPPORTED_PROMPT_VERSIONS:
        supported = ", ".join(sorted(SUPPORTED_PROMPT_VERSIONS))
        raise ValueError(f"unsupported prompt version: {prompt_version}; supported: {supported}")

    input_path = input_path or default_input_path(mode)
    rows = load_jsonl(input_path)
    if max_items is not None:
        rows = rows[:max_items]

    output_rows: list[dict[str, str]] = []
    trace_rows: list[dict[str, Any]] = []

    # 统计指标
    fallback_count = 0
    parse_failure_count = 0
    invalid_label_count = 0
    api_failure_count = 0
    strategy_rule_applied_count = 0
    skillflow_fallback_count = 0

    active_prompt_version = "n/a"
    active_memory_version = "n/a"
    model_name_for_slug = "baseline"

    llm_client = None
    if backend == "llm":
        active_prompt_version = prompt_version if not use_skillflow else "skillflow"
        active_memory_version = memory_version_for_prompt(prompt_version) if not use_skillflow else "n/a"
        llm_client = LLMClient()
        model_name_for_slug = llm_client.model

    # Few-shot 初始化
    fewshot_retriever = None
    if use_fewshot and backend == "llm":
        from .fewshot import build_fewshot_retriever
        train_path = PUBLIC_DATA_DIR / "train.jsonl"
        fewshot_retriever = build_fewshot_retriever(
            use_fewshot=True,
            train_path=train_path,
            k=fewshot_k,
            min_score=0.0,
            include_fields=True,
        )

    # SkillFlow 初始化
    skillflow = None
    skillflow_context = {}
    if use_skillflow and backend == "llm":
        from .skillflow import SkillFlow
        skillflow = SkillFlow()
        skillflow_context = {
            "llm_client": llm_client,
            "temperature": 0.3,
            "max_tokens": 256,
            "wiki": {},
            "debug_skill_trace": True,
            "fewshot_retriever": fewshot_retriever,
        }

    for row in rows:
        episode_id = row.get("episode_id", "")
        baseline_row = generate_baseline_row(row)

        if backend == "heuristic":
            output_rows.append(baseline_row)
            trace_rows.append({
                "episode_id": episode_id,
                "backend": "heuristic",
                "prompt_version": "n/a",
                "memory_version": "n/a",
                "use_skillflow": False,
                "input": row,
                "prompt": None,
                "raw_model_output": None,
                "parse_status": "ok",
                "parse_error": None,
                "parsed_output": None,
                "normalized_output": baseline_row,
                "fallback_used": False,
                "fallback_reason": None,
                "normalization_notes": ["Directly generated by heuristic rules."],
                "strategy_rule_version": "none",
                "strategy_rule_applied": False,
                "strategy_before": baseline_row.get("response_strategy", "neutral_observation"),
                "strategy_after": baseline_row.get("response_strategy", "neutral_observation"),
                "strategy_rule_reason": None,
                "skill_trace": [],
                "skill_errors": [],
            })
            continue

        # SkillFlow 路径
        if use_skillflow and skillflow is not None:
            try:
                state = skillflow.run_row(row, skillflow_context)
                final_output = state.get("final_output")
                if final_output:
                    output_rows.append(final_output)
                else:
                    output_rows.append(baseline_row)
                    skillflow_fallback_count += 1

                trace_rows.append({
                    "episode_id": episode_id,
                    "backend": "llm_skillflow",
                    "prompt_version": "skillflow",
                    "memory_version": "n/a",
                    "use_skillflow": True,
                    "input": row,
                    "bragging_mechanism": state.get("bragging_mechanism"),
                    "speaker_intention": state.get("speaker_intention"),
                    "desired_feedback": state.get("desired_feedback"),
                    "risk_assessment": state.get("risk_assessment"),
                    "response_strategy": state.get("response_strategy"),
                    "response_text": state.get("response_text"),
                    "raw_outputs": state.get("raw_outputs", {}),
                    "skill_trace": state.get("skill_trace", []),
                    "skill_errors": state.get("skill_errors", []),
                    "validation_errors": state.get("validation_errors", []),
                    "is_valid": state.get("is_valid", False),
                    "normalized_output": final_output or baseline_row,
                    "fallback_used": final_output is None,
                    "fallback_reason": "skillflow_failed" if final_output is None else None,
                    "fewshot_examples": state.get("fewshot_examples", {}),
                    "memory_used": state.get("memory_used", {}),
                    "response_judgment": state.get("response_judgment"),
                })
            except Exception as exc:
                output_rows.append(baseline_row)
                skillflow_fallback_count += 1
                trace_rows.append({
                    "episode_id": episode_id,
                    "backend": "llm_skillflow",
                    "prompt_version": "skillflow",
                    "memory_version": "n/a",
                    "use_skillflow": True,
                    "input": row,
                    "normalized_output": baseline_row,
                    "fallback_used": True,
                    "fallback_reason": f"skillflow_exception: {exc}",
                    "skill_trace": [],
                    "skill_errors": [{"skill": "SkillFlow", "error": str(exc)}],
                })
            continue

        # 原有 LLM 单次 prompt 路径
        prompt = build_prompt(row, active_prompt_version)
        raw_output = None
        parsed_output = None
        fallback_used = False
        fallback_reason = None
        parse_status = "ok"
        parse_error = None
        normalized_row = None

        try:
            raw_output = llm_client.call_chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=384
            )
        except Exception as e:
            fallback_used = True
            fallback_reason = "api_call_failed"
            api_failure_count += 1
            parse_status = "failed"
            parse_error = str(e)

        if not fallback_used:
            try:
                parsed_output = extract_and_parse_json(raw_output)
            except Exception as e:
                fallback_used = True
                fallback_reason = "json_parse_failed"
                parse_failure_count += 1
                parse_status = "failed"
                parse_error = str(e)

        if not fallback_used and parsed_output:
            req_fields = ["bragging_mechanism", "speaker_intention", "desired_feedback", "risk_assessment", "response_strategy", "response_text"]
            missing = [f for f in req_fields if f not in parsed_output]
            if missing:
                fallback_used = True
                fallback_reason = "missing_fields"
                parse_status = "failed"
                parse_error = f"Missing required fields: {missing}"
            else:
                mech = parsed_output.get("bragging_mechanism")
                strat = parsed_output.get("response_strategy")
                if mech not in ALLOWED_MECHANISMS or strat not in ALLOWED_STRATEGIES:
                    fallback_used = True
                    fallback_reason = "invalid_label"
                    invalid_label_count += 1
                    parse_status = "failed"
                    parse_error = f"Invalid label(s): mechanism={mech}, strategy={strat}"

        rule_trace = {
            "strategy_rule_version": strategy_rules,
            "strategy_rule_applied": False,
            "strategy_before": parsed_output.get("response_strategy", "neutral_observation") if parsed_output else "neutral_observation",
            "strategy_after": parsed_output.get("response_strategy", "neutral_observation") if parsed_output else "neutral_observation",
            "strategy_rule_reason": None
        }

        if not fallback_used and parsed_output:
            try:
                candidate = dict(parsed_output)
                candidate, rule_trace = apply_strategy_rules(row, candidate, rule_version=strategy_rules)
                if rule_trace.get("strategy_rule_applied"):
                    strategy_rule_applied_count += 1

                candidate["episode_id"] = episode_id
                normalized_row = normalize_output_row(candidate, input_context=row)
            except Exception as e:
                fallback_used = True
                fallback_reason = "normalization_failed"
                parse_status = "failed"
                parse_error = f"Normalization/Rules failed: {e}"

        if fallback_used:
            fallback_count += 1
            final_row = baseline_row
            rule_trace = {
                "strategy_rule_version": strategy_rules,
                "strategy_rule_applied": False,
                "strategy_before": baseline_row.get("response_strategy", "neutral_observation"),
                "strategy_after": baseline_row.get("response_strategy", "neutral_observation"),
                "strategy_rule_reason": None
            }
        else:
            final_row = normalized_row  # type: ignore

        output_rows.append(final_row)

        trace_rows.append({
            "episode_id": episode_id,
            "backend": "llm",
            "prompt_version": active_prompt_version,
            "memory_version": active_memory_version,
            "use_skillflow": False,
            "input": row,
            "prompt": prompt,
            "raw_model_output": raw_output,
            "parse_status": parse_status,
            "parse_error": parse_error,
            "parsed_output": parsed_output,
            "normalized_output": final_row,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "normalization_notes": [] if not fallback_used else [f"Fallback triggered: {fallback_reason}"],
            "strategy_rule_version": rule_trace["strategy_rule_version"],
            "strategy_rule_applied": rule_trace["strategy_rule_applied"],
            "strategy_before": rule_trace["strategy_before"],
            "strategy_after": rule_trace["strategy_after"],
            "strategy_rule_reason": rule_trace["strategy_rule_reason"]
        })

    count_label = f"max{max_items}" if max_items is not None else "full"
    if use_skillflow:
        slug = f"llm_{model_slug(model_name_for_slug)}_skillflow"
    elif backend == "llm":
        slug = f"llm_{model_slug(model_name_for_slug)}"
    else:
        slug = "heuristic_baseline"
    run_id = f"{mode}__{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}__{slug}__{count_label}"
    run_dir = OUTPUT_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    submission_path = run_dir / "submission.jsonl"
    input_subset_path = run_dir / "input_subset.jsonl"
    trace_path = run_dir / "debug" / "trace.jsonl"

    write_jsonl(submission_path, output_rows)
    write_jsonl(input_subset_path, rows)
    write_jsonl(trace_path, trace_rows)

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
        "backend": backend,
        "prompt_version": active_prompt_version,
        "memory_version": active_memory_version,
        "use_skillflow": use_skillflow,
        "use_fewshot": use_fewshot,
        "fewshot_k": fewshot_k if use_fewshot else 0,
        "strategy_rules": strategy_rules,
        "strategy_rule_applied_count": strategy_rule_applied_count,
        "skillflow_fallback_count": skillflow_fallback_count,
        "input_path": str(input_path),
        "input_subset_path": str(input_subset_path),
        "submission_path": str(submission_path),
        "trace_path": str(trace_path),
        "input_rows": len(rows),
        "output_rows": len(output_rows),
        "max_items": max_items,
        "generator": slug,
        "fallback_count": fallback_count,
        "parse_failure_count": parse_failure_count,
        "invalid_label_count": invalid_label_count,
        "api_failure_count": api_failure_count,
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
    parser = argparse.ArgumentParser(description="Run the humble brag pipeline.")
    parser.add_argument("--mode", choices=["dev", "test"], default="dev")
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--input-path", type=Path, default=None)
    parser.add_argument("--backend", choices=["heuristic", "llm"], default="heuristic")
    parser.add_argument(
        "--prompt-version",
        choices=sorted(SUPPORTED_PROMPT_VERSIONS),
        default="llm_a_minimal_v1",
    )
    parser.add_argument(
        "--strategy-rules",
        choices=["none", "v1"],
        default="none",
        help="Specify strategy rules version to apply."
    )
    parser.add_argument(
        "--use-skillflow",
        action="store_true",
        default=False,
        help="Use SkillFlow multi-step pipeline instead of single-prompt LLM."
    )
    parser.add_argument(
        "--use-fewshot",
        action="store_true",
        default=False,
        help="Enable few-shot retrieval from train.jsonl."
    )
    parser.add_argument(
        "--fewshot-k",
        type=int,
        default=3,
        help="Number of few-shot examples to retrieve (default: 3)."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = run_pipeline(
        mode=args.mode,
        max_items=args.max_items,
        input_path=args.input_path,
        backend=args.backend,
        prompt_version=args.prompt_version,
        strategy_rules=args.strategy_rules,
        use_skillflow=args.use_skillflow,
        use_fewshot=args.use_fewshot,
        fewshot_k=args.fewshot_k,
    )
    print(run_dir)


if __name__ == "__main__":
    main()
