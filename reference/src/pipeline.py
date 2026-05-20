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

from .baseline import BaselineFlow
from .debug_logger import DebugLogger
from .error_analyzer import run_dev_error_analysis
from .fewshot import build_fewshot_retriever
from .io_utils import load_jsonl, write_jsonl
from .llm_client import LLMClient
from .skillflow import SkillFlow
from .validators import validate_input_row
from .wiki_loader import load_agent_wiki


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
    debug_trace_path: Path
    llm_calls_path: Path


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
        debug_trace_path=run_dir / "debug" / "trace.jsonl",
        llm_calls_path=run_dir / "debug" / "llm_calls.jsonl",
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
    error_analysis_report: dict[str, Any] | None = None,
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
            f"- SkillFlow：`{manifest['use_skillflow']}`",
            f"- Agent Wiki：`{manifest['use_agent_wiki']}`",
            f"- Few-shot：`{manifest['use_fewshot']}`",
            f"- Few-shot K：`{manifest['fewshot_k']}`",
            f"- Debug trace：`{manifest['debug_trace_path']}`",
            f"- LLM 调用日志：`{manifest['llm_calls_path']}`",
            f"- 错误分析：`{manifest['error_analysis_report_path']}`",
            "",
            "## 文件说明",
            "",
            "- `submission.jsonl`：生成的最终提交结果文件，每行一个样本输出。",
            "- `debug/trace.jsonl`：每条样本的 Agent 链路调试信息，包含机制、风险、策略、回复、模型原始输出、few-shot 示例和 skill 错误。",
            "- `debug/llm_calls.jsonl`：逐次 LLM 调用日志，包含 skill 名、prompt、原始输出、耗时和错误；仅在 `SAVE_LLM_CALL_LOGS=True` 时生成。",
            "- `format_report.json`：官方 `format_checker.py` 的完整输出，`parsed_stdout_json.valid` 为 `true` 表示格式通过。",
            "- `dev_eval_report.json`：官方 `evaluate_dev.py` 的完整输出，dev 模式下查看 `parsed_stdout_json.proxy_metrics.proxy_dev_score`。",
            "- `error_analysis/error_report.md`：可选的 dev 错误分析报告，仅在 `RUN_DEV_ERROR_ANALYSIS=True` 时生成。",
            "- `run_manifest.json`：本次运行的配置索引，记录模型名、参数、输入路径、输出路径和脚本退出码。",
            "- `RES.md`：当前结果说明文件。",
        ]
    )
    if error_analysis_report:
        lines.extend(
            [
                "",
                "## 错误分析",
                f"- 错误样本数：`{error_analysis_report['case_count']}`",
                f"- LLM 总结批次数：`{error_analysis_report['llm_review_count']}`",
                f"- 报告：`{error_analysis_report['error_report_path']}`",
            ]
        )
    run_paths.result_summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
                "dev_gold_path": str(cfg.DEV_GOLD_PATH),
            },
        )
    return reports


def run_llm_health_check(cfg: ModuleType, llm_client: LLMClient) -> None:
    if not getattr(cfg, "RUN_LLM_HEALTH_CHECK", True):
        return

    try:
        llm_client.call_chat(
            [
                {
                    "role": "system",
                    "content": "Return only the word ok.",
                },
                {
                    "role": "user",
                    "content": "health check",
                },
            ],
            temperature=0.0,
            max_tokens=8,
        )
    except Exception as exc:
        base_url = getattr(llm_client, "base_url", "unknown")
        model = getattr(llm_client, "model", "unknown")
        raise RuntimeError(
            "LLM 连通性检查失败，已停止运行，避免生成全兜底 submission。\n"
            f"- OPENAI_BASE_URL: {base_url}\n"
            f"- OPENAI_MODEL: {model}\n"
            "- 请确认该服务真的支持 OpenAI-compatible chat completions，"
            "并且 base_url 应该指向 chat/completions 的上一级路径，例如 /v1。\n"
            f"- 原始错误: {exc}"
        ) from exc


def run_pipeline(cfg: ModuleType) -> list[dict[str, str]]:
    if cfg.MODE not in {"dev", "test"}:
        raise ValueError('MODE must be "dev" or "test"')
    use_skillflow = getattr(cfg, "USE_SKILLFLOW", True)

    llm_client = LLMClient.from_env(
        retry_times=cfg.RETRY_TIMES,
        retry_sleep_seconds=cfg.RETRY_SLEEP_SECONDS,
    )
    run_llm_health_check(cfg, llm_client)
    model_name = getattr(llm_client, "model", "unknown_model")
    run_paths = build_run_paths(cfg, model_name)
    print(f"本次运行 ID: {run_paths.run_id}")
    print(f"本次结果文件夹: {run_paths.run_dir}")

    wiki = load_agent_wiki(
        Path(getattr(cfg, "WIKI_DIR")),
        enabled=getattr(cfg, "USE_AGENT_WIKI", True),
    )
    fewshot_retriever = build_fewshot_retriever(cfg)
    debug_logger = DebugLogger(
        llm_call_path=run_paths.llm_calls_path,
        trace_path=run_paths.debug_trace_path,
        save_llm_calls=getattr(cfg, "SAVE_LLM_CALL_LOGS", False),
        save_prompt_text=getattr(cfg, "SAVE_PROMPT_TEXT", True),
        save_raw_output=getattr(cfg, "SAVE_RAW_LLM_OUTPUT", True),
        save_trace=getattr(cfg, "SAVE_DEBUG_TRACE", True),
    )
    flow = SkillFlow() if use_skillflow else BaselineFlow()

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
        state = flow.run_row(
            input_row,
            {
                "cfg": cfg,
                "llm_client": llm_client,
                "wiki": wiki,
                "fewshot_retriever": fewshot_retriever,
                "debug_logger": debug_logger,
                "row_index": index,
                "total": total,
            },
        )
        output_rows.append(state["final_output"])
        debug_logger.record_trace(state)

    write_jsonl(run_paths.submission_path, output_rows)
    print(f"\n已写入提交文件: {run_paths.submission_path}")

    debug_logger.write()
    if getattr(cfg, "SAVE_LLM_CALL_LOGS", False):
        print(f"已写入 LLM 调用日志: {run_paths.llm_calls_path}")
    if getattr(cfg, "SAVE_DEBUG_TRACE", True):
        print(f"已写入 Agent 调试链路: {run_paths.debug_trace_path}")

    reports = run_official_checks(cfg, run_paths, Path(reference_input_path))
    error_analysis_report = run_dev_error_analysis(
        cfg=cfg,
        llm_client=llm_client,
        run_paths=run_paths,
        reference_input_path=Path(reference_input_path),
        trace_path=run_paths.debug_trace_path
        if getattr(cfg, "SAVE_DEBUG_TRACE", True)
        else None,
    )
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
        "use_skillflow": use_skillflow,
        "flow_name": type(flow).__name__,
        "use_agent_wiki": getattr(cfg, "USE_AGENT_WIKI", True),
        "wiki_dir": str(getattr(cfg, "WIKI_DIR", "")),
        "use_fewshot": bool(fewshot_retriever),
        "fewshot_k": getattr(cfg, "FEWSHOT_K", None),
        "train_path": str(getattr(cfg, "TRAIN_PATH", "")),
        "save_debug_trace": getattr(cfg, "SAVE_DEBUG_TRACE", True),
        "debug_trace_path": str(run_paths.debug_trace_path)
        if getattr(cfg, "SAVE_DEBUG_TRACE", True)
        else None,
        "save_llm_call_logs": getattr(cfg, "SAVE_LLM_CALL_LOGS", False),
        "save_prompt_text": getattr(cfg, "SAVE_PROMPT_TEXT", True),
        "save_raw_llm_output": getattr(cfg, "SAVE_RAW_LLM_OUTPUT", True),
        "llm_calls_path": str(run_paths.llm_calls_path)
        if getattr(cfg, "SAVE_LLM_CALL_LOGS", False)
        else None,
        "run_dev_error_analysis": getattr(cfg, "RUN_DEV_ERROR_ANALYSIS", False),
        "error_analysis_report_path": (
            error_analysis_report["error_report_path"] if error_analysis_report else None
        ),
        "error_analysis": error_analysis_report,
        "row_count": len(output_rows),
        "report_returncodes": {
            name: report["returncode"] for name, report in reports.items()
        },
    }
    write_json_report(run_paths.manifest_path, manifest)
    write_run_result_markdown(cfg, run_paths, reports, manifest, error_analysis_report)
    print(f"本次运行清单已保存: {run_paths.manifest_path}")
    print(f"本次结果说明已保存: {run_paths.result_summary_path}")
    print_result_summary(cfg, run_paths, reports)
    return output_rows
