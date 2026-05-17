from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from .io_utils import load_jsonl, write_jsonl
from .llm_client import LLMClient
from .postprocess import (
    abstract_response_fallback,
    calibrate_mechanism,
    clean_response_text,
    clean_understanding,
    normalize_risk_assessment,
    parse_json_object,
    safe_mechanism,
    safe_strategy,
)
from .prompts import (
    mechanism_classifier_messages,
    response_messages,
    understanding_messages,
)
from .schemas import (
    DEFAULT_DESIRED_FEEDBACK,
    DEFAULT_MECHANISM,
    DEFAULT_RESPONSE_BY_STRATEGY,
    DEFAULT_RISK_ASSESSMENT,
    DEFAULT_SPEAKER_INTENTION,
    DEFAULT_STRATEGY,
    OUTPUT_FIELDS,
    VALID_BRAGGING_MECHANISMS,
    VALID_RESPONSE_STRATEGIES,
)
from .strategy_rules import choose_strategy
from .social_rubric import judge_row
from .validators import validate_input_row, validate_output


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    run_dir: Path
    submission_path: Path
    subset_input_path: Path
    format_report_path: Path
    dev_eval_report_path: Path
    manifest_path: Path
    result_summary_path: Path


def _safe_filename_part(value: Any, default: str = "unknown") -> str:
    text = str(value or default).strip()
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = text.strip("._-")
    return text[:80] or default


def _param_part(value: Any) -> str:
    return _safe_filename_part(str(value).replace(".", "p"))


def build_run_paths(cfg: ModuleType, model_name: str) -> RunPaths:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    max_items = "full" if cfg.MAX_ITEMS is None else f"max{cfg.MAX_ITEMS}"
    prefix = _safe_filename_part(getattr(cfg, "RUN_NAME_PREFIX", ""), "")
    parts = [
        prefix,
        _safe_filename_part(cfg.MODE),
        timestamp,
        _safe_filename_part(model_name),
        max_items,
        f"temp{_param_part(cfg.TEMPERATURE)}",
        f"tok{_param_part(cfg.MAX_TOKENS)}",
    ]
    run_id = "__".join(part for part in parts if part)
    output_dir = Path(cfg.OUTPUT_DIR)
    run_dir = output_dir / run_id
    return RunPaths(
        run_id=run_id,
        run_dir=run_dir,
        submission_path=run_dir / "submission.jsonl",
        subset_input_path=run_dir / "input_subset.jsonl",
        format_report_path=run_dir / "format_report.json",
        dev_eval_report_path=run_dir / "dev_eval_report.json",
        manifest_path=run_dir / "run_manifest.json",
        result_summary_path=run_dir / "RES.md",
    )


def write_json_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parsed_report(reports: dict[str, Any], name: str) -> dict[str, Any]:
    parsed = reports.get(name, {}).get("parsed_stdout_json")
    return parsed if isinstance(parsed, dict) else {}


def _format_status_text(format_report: dict[str, Any]) -> str:
    if not format_report:
        return "未运行"
    if format_report.get("valid") is True:
        warnings = format_report.get("warning_count", 0)
        return f"通过，warning={warnings}"
    errors = format_report.get("error_count", "未知")
    return f"未通过，error={errors}"


def _dev_score_text(dev_report: dict[str, Any]) -> str:
    metrics = dev_report.get("proxy_metrics") if isinstance(dev_report, dict) else None
    if not isinstance(metrics, dict):
        return "未运行"
    score = metrics.get("proxy_dev_score")
    mechanism = metrics.get("mechanism_accuracy")
    strategy = metrics.get("strategy_score")
    risk = metrics.get("risk_label_f1_from_risk_assessment")
    response = metrics.get("response_reference_token_f1")
    return (
        f"{score} "
        f"(mechanism={mechanism}, strategy={strategy}, risk={risk}, response={response})"
    )


def print_result_summary(
    cfg: ModuleType,
    run_paths: RunPaths,
    reports: dict[str, Any],
) -> None:
    format_report = _parsed_report(reports, "format_checker")
    dev_report = _parsed_report(reports, "evaluate_dev")
    print("\n运行结果摘要:")
    print(f"- 结果文件夹: {run_paths.run_dir}")
    print(f"- 格式检查: {_format_status_text(format_report)}")
    if cfg.MODE == "dev":
        print(f"- dev 代理分数: {_dev_score_text(dev_report)}")
        if cfg.MAX_ITEMS is not None:
            print("- 说明: 当前是 subset 冒烟测试分数，只用于确认链路和初步观察。")
    else:
        print("- test 模式没有公开 gold，本地只看格式检查是否通过。")


def write_run_result_markdown(
    cfg: ModuleType,
    run_paths: RunPaths,
    reports: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    format_report = _parsed_report(reports, "format_checker")
    dev_report = _parsed_report(reports, "evaluate_dev")
    lines = [
        "## 本次运行结果",
        "",
    ]
    if cfg.MODE == "dev":
        lines.append(f"- dev 代理分数：{_dev_score_text(dev_report)}。")
    else:
        lines.append("- dev 代理分数：未运行。")
    lines.append(f"- 格式检查：{_format_status_text(format_report)}。")

    lines.extend(
        [
            "",
            "## 本次配置",
            f"- run_id：`{run_paths.run_id}`",
            f"- 模式：`{manifest['mode']}`",
            f"- 模型：`{manifest['model']}`",
            f"- 样本数：`{manifest['row_count']}`",
            f"- MAX_ITEMS：`{manifest['max_items']}`",
            f"- 温度：`{manifest['temperature']}`",
            f"- max_tokens：`{manifest['max_tokens']}`",
            "",
            "## 文件说明",
            "",
            "- `submission.jsonl`：生成的最终提交结果文件，每行一个样本输出。",
            "- `format_report.json`：官方 `format_checker.py` 的完整输出，`parsed_stdout_json.valid` 为 `true` 表示格式通过。",
            "- `dev_eval_report.json`：官方 `evaluate_dev.py` 的完整输出，dev 模式下查看 `parsed_stdout_json.proxy_metrics.proxy_dev_score`。",
            "- `run_manifest.json`：本次运行的配置索引，记录模型名、参数、输入路径、输出路径和脚本退出码。",
            "- `RES.md`：当前结果说明文件。",
        ]
    )
    run_paths.result_summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def classify_mechanism(row: dict[str, Any], llm_client: LLMClient, cfg: ModuleType) -> str:
    try:
        raw = llm_client.call_chat(
            mechanism_classifier_messages(row),
            temperature=0.0,
            max_tokens=32,
        )
    except Exception as exc:
        print(f"  机制分类使用兜底值: {exc}")
        return DEFAULT_MECHANISM
    return safe_mechanism(raw, VALID_BRAGGING_MECHANISMS)


def generate_understanding(
    row: dict[str, Any],
    mechanism: str,
    llm_client: LLMClient,
    cfg: ModuleType,
) -> dict[str, str]:
    try:
        raw = llm_client.call_chat(
            understanding_messages(row, mechanism),
            temperature=cfg.TEMPERATURE,
            max_tokens=cfg.MAX_TOKENS,
        )
        parsed = parse_json_object(raw)
    except Exception as exc:
        print(f"  理解字段使用兜底值: {exc}")
        parsed = None
    return clean_understanding(parsed)


def generate_response(
    row: dict[str, Any],
    mechanism: str,
    understanding: dict[str, Any],
    strategy: str,
    llm_client: LLMClient,
    cfg: ModuleType,
) -> str:
    try:
        raw = llm_client.call_chat(
            response_messages(row, mechanism, understanding, strategy),
            temperature=cfg.TEMPERATURE,
            max_tokens=cfg.MAX_TOKENS,
        )
    except Exception as exc:
        print(f"  回复文本使用兜底值: {exc}")
        raw = DEFAULT_RESPONSE_BY_STRATEGY.get(strategy, DEFAULT_RESPONSE_BY_STRATEGY["light_acknowledgment"])
    cleaned = clean_response_text(raw, strategy)
    candidate = {
        "episode_id": str(row["episode_id"]),
        "bragging_mechanism": mechanism,
        "speaker_intention": str(understanding.get("speaker_intention", DEFAULT_SPEAKER_INTENTION)),
        "desired_feedback": str(understanding.get("desired_feedback", DEFAULT_DESIRED_FEEDBACK)),
        "risk_assessment": str(understanding.get("risk_assessment", DEFAULT_RISK_ASSESSMENT)),
        "response_strategy": strategy,
        "response_text": cleaned,
    }
    first_judgment = judge_row(row, candidate)
    if not first_judgment["hard_issues"]:
        return cleaned

    fallback = clean_response_text(abstract_response_fallback(strategy, mechanism, row), strategy)
    fallback_candidate = dict(candidate)
    fallback_candidate["response_text"] = fallback
    fallback_judgment = judge_row(row, fallback_candidate)
    if not fallback_judgment["hard_issues"]:
        return fallback
    return clean_response_text(
        DEFAULT_RESPONSE_BY_STRATEGY.get(strategy, DEFAULT_RESPONSE_BY_STRATEGY[DEFAULT_STRATEGY]),
        strategy,
    )


def build_fallback_row(input_row: dict[str, Any]) -> dict[str, str]:
    strategy = "neutral_observation" if input_row.get("platform") in {
        "workplace_channel",
        "academic_forum",
        "public_social_media",
    } else "light_acknowledgment"
    return {
        "episode_id": str(input_row["episode_id"]),
        "bragging_mechanism": DEFAULT_MECHANISM,
        "speaker_intention": DEFAULT_SPEAKER_INTENTION,
        "desired_feedback": DEFAULT_DESIRED_FEEDBACK,
        "risk_assessment": DEFAULT_RISK_ASSESSMENT,
        "response_strategy": strategy,
        "response_text": DEFAULT_RESPONSE_BY_STRATEGY[strategy],
    }


def build_output_row(
    input_row: dict[str, Any],
    mechanism: str,
    understanding: dict[str, str],
    strategy: str,
    response_text: str,
) -> dict[str, str]:
    strategy = safe_strategy(strategy, VALID_RESPONSE_STRATEGIES)
    risk_assessment = normalize_risk_assessment(
        understanding.get("risk_assessment", DEFAULT_RISK_ASSESSMENT),
        input_row=input_row,
        strategy=strategy,
    )
    row = {
        "episode_id": str(input_row["episode_id"]),
        "bragging_mechanism": mechanism,
        "speaker_intention": understanding.get("speaker_intention", DEFAULT_SPEAKER_INTENTION),
        "desired_feedback": understanding.get("desired_feedback", DEFAULT_DESIRED_FEEDBACK),
        "risk_assessment": risk_assessment,
        "response_strategy": strategy,
        "response_text": response_text,
    }
    return {field: row[field] for field in OUTPUT_FIELDS}


def process_row(input_row: dict[str, Any], llm_client: LLMClient, cfg: ModuleType) -> dict[str, str]:
    mechanism = classify_mechanism(input_row, llm_client, cfg)
    mechanism = calibrate_mechanism(input_row, mechanism)
    understanding = generate_understanding(input_row, mechanism, llm_client, cfg)
    strategy = choose_strategy(input_row, mechanism, understanding)
    response_text = generate_response(input_row, mechanism, understanding, strategy, llm_client, cfg)
    output_row = build_output_row(input_row, mechanism, understanding, strategy, response_text)
    try:
        validate_output(output_row, input_row)
    except Exception as exc:
        print(f"  输出行校验失败，使用整行兜底: {exc}")
        output_row = build_fallback_row(input_row)
        validate_output(output_row, input_row)
    return output_row


def _run_command(
    label: str,
    command: list[str],
    report_path: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    print(f"\n{label}:")
    print(" ".join(str(part) for part in command))
    result = subprocess.run(command, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())

    parsed_stdout: Any = None
    if result.stdout.strip():
        try:
            parsed_stdout = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed_stdout = None

    report = {
        "label": label,
        "command": [str(part) for part in command],
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "parsed_stdout_json": parsed_stdout,
        "metadata": metadata,
    }
    write_json_report(report_path, report)
    print(f"{label} 报告已保存: {report_path}")
    if result.returncode != 0:
        print(f"{label} 执行失败，退出码: {result.returncode}")
    return report


def run_official_checks(
    cfg: ModuleType,
    run_paths: RunPaths,
    reference_input_path: Path,
) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    if cfg.RUN_OFFICIAL_FORMAT_CHECK:
        reports["format_checker"] = _run_command(
            "format_checker",
            [
                sys.executable,
                str(cfg.FORMAT_CHECKER_PATH),
                str(run_paths.submission_path),
                str(reference_input_path),
            ],
            run_paths.format_report_path,
            {
                "run_id": run_paths.run_id,
                "submission_path": str(run_paths.submission_path),
                "reference_input_path": str(reference_input_path),
            },
        )
    if cfg.RUN_DEV_EVAL and cfg.MODE == "dev":
        reports["evaluate_dev"] = _run_command(
            "evaluate_dev",
            [
                sys.executable,
                str(cfg.EVALUATE_DEV_PATH),
                str(reference_input_path),
                str(cfg.DEV_GOLD_PATH),
                str(run_paths.submission_path),
            ],
            run_paths.dev_eval_report_path,
            {
                "run_id": run_paths.run_id,
                "submission_path": str(run_paths.submission_path),
                "reference_input_path": str(reference_input_path),
                "gold_path": str(cfg.DEV_GOLD_PATH),
            },
        )
    return reports


def run_pipeline(cfg: ModuleType) -> list[dict[str, str]]:
    if cfg.MODE not in {"dev", "test"}:
        raise ValueError('MODE must be "dev" or "test"')

    llm_client = LLMClient.from_env(
        retry_times=cfg.RETRY_TIMES,
        retry_sleep_seconds=cfg.RETRY_SLEEP_SECONDS,
    )
    model_name = getattr(llm_client, "model", "unknown_model")
    run_paths = build_run_paths(cfg, model_name)
    print(f"本次运行 ID: {run_paths.run_id}")
    print(f"本次结果文件夹: {run_paths.run_dir}")

    input_rows = load_jsonl(cfg.INPUT_PATH)
    for index, row in enumerate(input_rows, start=1):
        validate_input_row(row, index)

    selected_rows = input_rows
    reference_input_path = cfg.INPUT_PATH
    if cfg.MAX_ITEMS is not None:
        selected_rows = input_rows[: int(cfg.MAX_ITEMS)]
        write_jsonl(run_paths.subset_input_path, selected_rows)
        reference_input_path = run_paths.subset_input_path
        print(f"已写入本次 input subset: {run_paths.subset_input_path}")

    output_rows: list[dict[str, str]] = []
    total = len(selected_rows)
    for index, input_row in enumerate(selected_rows, start=1):
        episode_id = input_row["episode_id"]
        print(f"[{index}/{total}] {episode_id}")
        output_rows.append(process_row(input_row, llm_client, cfg))

    write_jsonl(run_paths.submission_path, output_rows)
    print(f"\n已写入提交文件: {run_paths.submission_path}")

    reports = run_official_checks(cfg, run_paths, Path(reference_input_path))
    manifest = {
        "run_id": run_paths.run_id,
        "mode": cfg.MODE,
        "model": model_name,
        "input_path": str(cfg.INPUT_PATH),
        "reference_input_path": str(reference_input_path),
        "submission_path": str(run_paths.submission_path),
        "subset_input_path": str(run_paths.subset_input_path) if cfg.MAX_ITEMS is not None else None,
        "format_report_path": str(run_paths.format_report_path) if cfg.RUN_OFFICIAL_FORMAT_CHECK else None,
        "dev_eval_report_path": str(run_paths.dev_eval_report_path)
        if cfg.RUN_DEV_EVAL and cfg.MODE == "dev"
        else None,
        "result_summary_path": str(run_paths.result_summary_path),
        "max_items": cfg.MAX_ITEMS,
        "temperature": cfg.TEMPERATURE,
        "max_tokens": cfg.MAX_TOKENS,
        "retry_times": cfg.RETRY_TIMES,
        "row_count": len(output_rows),
        "report_returncodes": {
            name: report["returncode"] for name, report in reports.items()
        },
    }
    write_json_report(run_paths.manifest_path, manifest)
    write_run_result_markdown(cfg, run_paths, reports, manifest)
    print(f"本次运行清单已保存: {run_paths.manifest_path}")
    print(f"本次结果说明已保存: {run_paths.result_summary_path}")
    print_result_summary(cfg, run_paths, reports)
    return output_rows
