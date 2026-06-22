from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from .debug_logger import DebugLogger
from .error_analyzer import run_dev_error_analysis
from .fewshot import build_fewshot_retriever
from .io_utils import load_jsonl, write_jsonl
from .llm_client import LLMClient
from .memory import MemoryRetriever, load_memories
from .skillflow import SkillFlow
from .validators import validate_input_row


@dataclass(frozen=True)
class RunPaths:
    """一次运行产生的全部文件路径。"""

    run_id: str
    run_dir: Path
    submission_path: Path
    format_report_path: Path
    dev_eval_report_path: Path
    manifest_path: Path
    result_summary_path: Path
    trace_path: Path
    llm_calls_path: Path
    fewshot_log_path: Path
    subset_input_path: Path


def _safe_part(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "unknown"))
    return text.strip("._-")[:80] or "unknown"


def build_run_paths(cfg: ModuleType, model: str) -> RunPaths:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{cfg.RUN_MODE}_{timestamp}_{_safe_part(model)}"
    run_dir = Path(cfg.OUTPUT_DIR) / run_id
    return RunPaths(
        run_id=run_id,
        run_dir=run_dir,
        submission_path=run_dir / "submission.jsonl",
        format_report_path=run_dir / "format_report.json",
        dev_eval_report_path=run_dir / "dev_eval_report.json",
        manifest_path=run_dir / "run_manifest.json",
        result_summary_path=run_dir / "RES.md",
        trace_path=run_dir / "debug" / "trace.jsonl",
        llm_calls_path=run_dir / "debug" / "llm_calls.jsonl",
        fewshot_log_path=run_dir / "debug" / "fewshot.jsonl",
        subset_input_path=run_dir / "debug" / "input_subset.jsonl",
    )


def write_json_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _run_script(
    label: str,
    command: list[str],
    report_path: Path,
) -> dict[str, Any]:
    result = subprocess.run(command, text=True, capture_output=True)
    parsed: Any = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed = None
    report = {
        "label": label,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "parsed_stdout_json": parsed,
    }
    write_json_report(report_path, report)
    print(f"{label}：{'通过' if result.returncode == 0 else '失败'}")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "无错误详情"
        print(
            f"[WARN] {label}未通过，退出码 {result.returncode}：{detail}",
            flush=True,
        )
    return report


def run_official_checks(
    cfg: ModuleType,
    paths: RunPaths,
    reference_input_path: Path,
) -> dict[str, Any]:
    reports = {
        "format_checker": _run_script(
            "格式检查",
            [
                sys.executable,
                str(cfg.FORMAT_CHECKER_PATH),
                str(paths.submission_path),
                str(reference_input_path),
            ],
            paths.format_report_path,
        )
    }
    if cfg.RUN_DEV_EVAL:
        reports["evaluate_dev"] = _run_script(
            "dev 评分",
            [
                sys.executable,
                str(cfg.EVALUATE_DEV_PATH),
                str(reference_input_path),
                str(cfg.DEV_GOLD_PATH),
                str(paths.submission_path),
            ],
            paths.dev_eval_report_path,
        )
    return reports


def run_llm_health_check(cfg: ModuleType, client: LLMClient) -> None:
    """在正式处理样本前确认 API 和模型可用。"""
    if not cfg.RUN_LLM_HEALTH_CHECK:
        return
    try:
        result, _source = client.call_chat(
            [
                {"role": "system", "content": "Return only the word ok."},
                {"role": "user", "content": "health check"},
            ],
            temperature=0.0,
            max_tokens=8,
        )
    except Exception as exc:
        raise RuntimeError(
            "LLM 连通性检查失败。请检查 .env 中的 API 地址、Key，"
            f"以及 OPENAI_MODEL。原始错误：{exc}"
        ) from exc
    if not result.strip():
        raise RuntimeError("LLM 连通性检查返回了空内容")


def _parsed_report(
    reports: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    value = reports.get(name, {}).get("parsed_stdout_json")
    return value if isinstance(value, dict) else {}


def _build_stats(states: list[dict[str, Any]]) -> dict[str, Any]:
    memory_by_skill: Counter[str] = Counter()
    memory_by_type: Counter[str] = Counter()
    mechanism_changes: Counter[str] = Counter()
    mechanism_decisions: Counter[str] = Counter()
    mechanism_cache_hits = 0
    mechanism_review_count = 0
    mechanism_review_failure_count = 0
    mechanism_rule_override_count = 0
    strategy_changes: Counter[str] = Counter()
    risk_review_added: Counter[str] = Counter()
    fallback_reasons: Counter[str] = Counter()
    failed_episodes: dict[str, list[dict[str, Any]]] = {}

    for state in states:
        for skill, items in state.get("memory_used", {}).items():
            memory_by_skill[skill] += len(items)
            for item in items:
                memory_by_type[str(item.get("memory_type", "unknown"))] += 1
        calibration = state.get("mechanism_calibration") or {}
        mechanism_decisions[str(calibration.get("decision", "unknown"))] += 1
        if calibration.get("cache_hit"):
            mechanism_cache_hits += 1
        if (
            not calibration.get("cache_hit")
            and calibration.get("review_reason")
        ):
            mechanism_review_count += 1
            if calibration.get("review_error"):
                mechanism_review_failure_count += 1
        if calibration.get("decision") == "rule_override":
            mechanism_rule_override_count += 1
        if calibration.get("changed"):
            mechanism_changes[
                f"{calibration.get('initial_label')} -> {calibration.get('label')}"
            ] += 1
        strategy = state.get("strategy_trace") or {}
        if strategy.get("rule_strategy") != strategy.get("final_strategy"):
            strategy_changes[
                f"{strategy.get('rule_strategy')} -> {strategy.get('final_strategy')}"
            ] += 1
        for item in state.get("response_risk_review_warnings", []):
            risk_review_added[str(item).split(":", 1)[0]] += 1
        if state.get("fallback_used"):
            fallback_reasons[
                str(state.get("fallback_reason", "unknown")).split(":", 1)[0]
            ] += 1
        if state.get("skill_errors"):
            failed_episodes[str(state.get("episode_id"))] = state["skill_errors"]

    return {
        "memory_used_count": sum(memory_by_skill.values()),
        "memory_used_by_skill": dict(memory_by_skill),
        "memory_used_by_type": dict(memory_by_type),
        "mechanism_changes": dict(mechanism_changes),
        "mechanism_decisions": dict(mechanism_decisions),
        "mechanism_cache_hits": mechanism_cache_hits,
        "mechanism_review_count": mechanism_review_count,
        "mechanism_review_failure_count": mechanism_review_failure_count,
        "mechanism_rule_override_count": mechanism_rule_override_count,
        "strategy_changes": dict(strategy_changes),
        "risk_review_added": dict(risk_review_added),
        "fallback_count": sum(fallback_reasons.values()),
        "fallback_reasons": dict(fallback_reasons),
        "failed_episodes": failed_episodes,
    }


def _write_result_summary(
    cfg: ModuleType,
    paths: RunPaths,
    reports: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    format_report = _parsed_report(reports, "format_checker")
    dev_report = _parsed_report(reports, "evaluate_dev")
    metrics = dev_report.get("proxy_metrics", {})
    lines = [
        "# 运行结果",
        "",
        f"- 运行模式：`{cfg.RUN_MODE}`",
        f"- 模型：`{manifest['model']}`",
        f"- 样本数：`{manifest['row_count']}`",
        f"- 格式检查：`{'通过' if format_report.get('valid') else '未通过'}`",
    ]
    if cfg.RUN_DEV_EVAL:
        lines.append(f"- dev 代理分数：`{metrics.get('proxy_dev_score', '未生成')}`")
        lines.extend(
            [
                f"- 机制准确率：`{metrics.get('mechanism_accuracy', '未生成')}`",
                f"- 策略得分：`{metrics.get('strategy_score', '未生成')}`",
                f"- 风险 F1：`{metrics.get('risk_label_f1_from_risk_assessment', '未生成')}`",
                f"- 回复 token F1：`{metrics.get('response_reference_token_f1', '未生成')}`",
            ]
        )
    lines.extend(
        [
            "",
            "## 流程统计",
            "",
            f"- memory 命中：`{manifest['stats']['memory_used_count']}`",
            f"- 机制校准变化：`{manifest['stats']['mechanism_changes']}`",
            f"- 机制缓存命中：`{manifest['stats']['mechanism_cache_hits']}`",
            f"- 机制复核调用：`{manifest['stats']['mechanism_review_count']}`",
            f"- 机制复核失败：`{manifest['stats']['mechanism_review_failure_count']}`",
            f"- 机制决策来源：`{manifest['stats']['mechanism_decisions']}`",
            f"- 策略变化：`{manifest['stats']['strategy_changes']}`",
            f"- 回复风险复查：`{manifest['stats']['risk_review_added']}`",
            f"- 兜底次数：`{manifest['stats']['fallback_count']}`",
            f"- Skill 异常样本：`{len(manifest['stats']['failed_episodes'])}`",
            "",
            "## 文件",
            "",
            "- `submission.jsonl`：本次输出；test 模式下可直接提交。",
            "- `format_report.json`：格式检查结果。",
            "- `dev_eval_report.json`：smoke/dev 评分明细。",
            "- `run_manifest.json`：配置、统计和文件索引。",
            "- `debug/trace.jsonl`：逐样本 SkillFlow 轨迹。",
            "- `error_analysis/`：完整 dev 的可选错误分析。",
        ]
    )
    paths.result_summary_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_pipeline(cfg: ModuleType) -> list[dict[str, str]]:
    """执行配置指定的 smoke、dev 或 test 流程。"""
    client = LLMClient.from_env(
        retry_times=cfg.RETRY_TIMES,
        retry_sleep_seconds=cfg.RETRY_SLEEP_SECONDS,
        enable_rate_limit=cfg.ENABLE_API_RATE_LIMIT,
        requests_per_minute=cfg.API_REQUESTS_PER_MINUTE,
        tokens_per_minute=cfg.API_TOKENS_PER_MINUTE,
        rate_limit_safety_margin=cfg.API_RATE_LIMIT_SAFETY_MARGIN,
    )
    run_llm_health_check(cfg, client)
    paths = build_run_paths(cfg, client.model)
    paths.run_dir.mkdir(parents=True, exist_ok=True)
    print(f"运行模式：{cfg.RUN_MODE}")
    print(f"结果目录：{paths.run_dir}")

    memories = (
        load_memories(
            Path(cfg.MEMORY_PATH),
            Path(cfg.GENERATED_MEMORY_PATH),
            bool(cfg.USE_GENERATED_MEMORY),
        )
        if cfg.USE_MEMORY
        else []
    )
    memory_retriever = (
        MemoryRetriever(
            memories,
            dict(cfg.MEMORY_TOP_K_BY_SKILL),
            dict(cfg.MEMORY_MAX_CHARS_BY_SKILL),
            dict(cfg.MEMORY_MIN_SCORE_BY_SKILL),
            getattr(cfg, "MEMORY_ROUTER_MODE", "function"),
        )
        if memories
        else None
    )
    fewshot_retriever = build_fewshot_retriever(cfg)
    logger = DebugLogger(
        llm_call_path=paths.llm_calls_path,
        trace_path=paths.trace_path,
        fewshot_log_path=paths.fewshot_log_path,
        save_llm_calls=cfg.SAVE_LLM_CALL_LOGS,
        save_prompt_text=cfg.SAVE_PROMPT_TEXT,
        save_raw_output=cfg.SAVE_RAW_LLM_OUTPUT,
        save_trace=cfg.SAVE_DEBUG_TRACE,
        save_fewshot_logs=cfg.SAVE_FEWSHOT_LOGS,
    )

    all_rows = load_jsonl(Path(cfg.INPUT_PATH))
    selected_rows = all_rows[: cfg.MAX_ITEMS] if cfg.MAX_ITEMS else all_rows
    for index, row in enumerate(selected_rows, start=1):
        validate_input_row(row, index)
    reference_input_path = Path(cfg.INPUT_PATH)
    if cfg.MAX_ITEMS:
        write_jsonl(paths.subset_input_path, selected_rows)
        reference_input_path = paths.subset_input_path

    flow = SkillFlow(cfg)
    mechanism_knowledge = (
        memory_retriever.get_mechanism_knowledge()
        if memory_retriever
        else []
    )
    run_context = {
        "cfg": cfg,
        "llm_client": client,
        "fewshot_retriever": fewshot_retriever,
        "memory_retriever": memory_retriever,
        "mechanism_knowledge": mechanism_knowledge,
        "mechanism_cache": {},
        "debug_logger": logger,
    }
    outputs: list[dict[str, str]] = []
    states: list[dict[str, Any]] = []
    total = len(selected_rows)
    start_time = time.time()
    bar_width = 30
    for index, row in enumerate(selected_rows, start=1):
        item_start = time.time()
        state = flow.run_row(row, run_context)
        elapsed = time.time() - start_time
        avg_per_item = elapsed / index
        remaining = avg_per_item * (total - index)
        filled = int(bar_width * index / total)
        bar = "█" * filled + "░" * (bar_width - filled)

        def _fmt(seconds: float) -> str:
            m, s = divmod(int(seconds), 60)
            h, m = divmod(m, 60)
            return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

        elapsed_str = _fmt(elapsed)
        remain_str = _fmt(remaining)
        item_ms = (time.time() - item_start) * 1000
        sys.stdout.write(
            f"\r[{bar}] {index}/{total}  "
            f"已用 {elapsed_str}  剩余 ~{remain_str}  "
            f"本条 {item_ms:.0f}ms  {row['episode_id']}   "
        )
        sys.stdout.flush()
        states.append(state)
        outputs.append(state["final_output"])
        logger.record_trace(state)
    total_time = time.time() - start_time
    m, s = divmod(int(total_time), 60)
    h, m = divmod(m, 60)
    time_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    print(f"\n全部完成，共 {total} 条，耗时 {time_str}")

    write_jsonl(paths.submission_path, outputs)
    logger.write(fewshot_retriever.logs if fewshot_retriever else None)
    reports = run_official_checks(cfg, paths, reference_input_path)
    error_analysis = run_dev_error_analysis(
        cfg=cfg,
        llm_client=client,
        run_paths=paths,
        reference_input_path=reference_input_path,
        trace_path=paths.trace_path if cfg.SAVE_DEBUG_TRACE else None,
    )
    stats = _build_stats(states)
    if stats["fallback_count"]:
        print(
            f"[WARN] 本次运行有 {stats['fallback_count']} 条回复使用兜底，"
            "请查看 RES.md 或 debug/trace.jsonl。",
            flush=True,
        )
    if stats["failed_episodes"]:
        print(
            f"[WARN] 本次运行有 {len(stats['failed_episodes'])} 个样本出现 "
            "Skill 异常，请查看 RES.md 或 debug/trace.jsonl。",
            flush=True,
        )
    manifest = {
        "run_id": paths.run_id,
        "run_mode": cfg.RUN_MODE,
        "model": client.model,
        "row_count": len(outputs),
        "input_path": str(cfg.INPUT_PATH),
        "submission_path": str(paths.submission_path),
        "use_memory": cfg.USE_MEMORY,
        "memory_router_mode": getattr(cfg, "MEMORY_ROUTER_MODE", "function"),
        "memory_llm_router_candidate_k": getattr(
            cfg,
            "MEMORY_LLM_ROUTER_CANDIDATE_K",
            None,
        ),
        "memory_llm_router_top_k": getattr(cfg, "MEMORY_LLM_ROUTER_TOP_K", None),
        "use_generated_memory": cfg.USE_GENERATED_MEMORY,
        "memory_count": len(memories),
        "memory_count_by_type": dict(
            Counter(item.memory_type for item in memories)
        ),
        "mechanism_knowledge_count": len(mechanism_knowledge),
        "mechanism_knowledge_ids": [
            item.get("memory_id") for item in mechanism_knowledge
        ],
        "use_fewshot": bool(fewshot_retriever),
        "fewshot_requested_mode": (
            getattr(fewshot_retriever, "requested_mode", None)
            if fewshot_retriever
            else None
        ),
        "fewshot_mode": (
            getattr(fewshot_retriever, "effective_mode", None)
            if fewshot_retriever
            else None
        ),
        "fewshot_embedding_model": (
            getattr(fewshot_retriever, "embedding_model", None)
            if fewshot_retriever
            else None
        ),
        "fewshot_fallback_reason": (
            getattr(fewshot_retriever, "fallback_reason", "")
            if fewshot_retriever
            else ""
        ),
        "run_error_analysis": cfg.EFFECTIVE_ERROR_ANALYSIS,
        "save_error_memory": cfg.EFFECTIVE_SAVE_ERROR_MEMORY,
        "error_analysis": error_analysis,
        "llm_call_count": logger.llm_call_count,
        "prompt_char_count": logger.prompt_char_count,
        "stats": stats,
        "report_returncodes": {
            name: report["returncode"] for name, report in reports.items()
        },
    }
    write_json_report(paths.manifest_path, manifest)
    _write_result_summary(cfg, paths, reports, manifest)

    failed_reports = [
        name for name, report in reports.items() if report["returncode"] != 0
    ]
    print(f"输出文件：{paths.submission_path}")
    print(f"结果摘要：{paths.result_summary_path}")
    if failed_reports:
        raise RuntimeError(f"检查未通过：{', '.join(failed_reports)}")
    return outputs
