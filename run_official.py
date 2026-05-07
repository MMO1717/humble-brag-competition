#!/usr/bin/env python3
"""
run_official.py
BRAG-Agent v6 官方格式提交 Runner。

用法：
  python run_official.py --input BRAG-Agent-public/data/dev_input.jsonl --output outputs/dev_submission.jsonl --limit 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))

from src.BraggingResponseAgent import BraggingResponseAgent, AgentInput

# 官方要求的 7 个字段
OFFICIAL_FIELDS = [
    "episode_id",
    "bragging_mechanism",
    "speaker_intention",
    "desired_feedback",
    "risk_assessment",
    "response_strategy",
    "response_text",
]

SAVE_LOCK = asyncio.Lock()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_completed_ids(path: Path) -> set[str]:
    """加载已成功完成的 episode_id 集合（用于断点续传）。"""
    ids = set()
    if not path.exists():
        return ids
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if "episode_id" in obj and "error" not in obj:
                ids.add(obj["episode_id"])
        except json.JSONDecodeError:
            continue
    return ids


def to_official_row(output) -> dict[str, Any]:
    """将 AgentOutput 转为官方 7 字段 dict。"""
    d = asdict(output)
    return {k: d[k] for k in OFFICIAL_FIELDS}


async def process_one(
    agent: BraggingResponseAgent,
    row: dict[str, Any],
    output_path: Path,
    error_path: Path,
    completed: set[str],
):
    """处理单条数据。"""
    eid = row["episode_id"]
    if eid in completed:
        return

    try:
        inp = AgentInput(
            episode_id=eid,
            speaker_post=row["speaker_post"],
            platform=row.get("platform", ""),
            relationship=row.get("relationship", ""),
            agent_role=row.get("agent_role", ""),
            interaction_goal=row.get("interaction_goal", ""),
        )
        out = await agent.arun(inp)
        official_row = to_official_row(out)

        async with SAVE_LOCK:
            with open(output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(official_row, ensure_ascii=False) + "\n")
            completed.add(eid)

        logger.info(f"[{eid}] OK strategy={out.response_strategy} mechanism={out.bragging_mechanism}")

    except Exception as e:
        logger.error(f"[{eid}] FAIL: {e}")
        async with SAVE_LOCK:
            with open(error_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"episode_id": eid, "error": str(e)}, ensure_ascii=False) + "\n")


async def main():
    parser = argparse.ArgumentParser(description="BRAG-Agent v6 Official Submission Runner")
    parser.add_argument("--input", default="BRAG-Agent-public/data/dev_input.jsonl", help="输入 JSONL 文件路径")
    parser.add_argument("--output", default="outputs/dev_submission.jsonl", help="输出 JSONL 文件路径")
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 条（调试用）")
    parser.add_argument("--concurrency", type=int, default=5, help="并发数")
    parser.add_argument("--model", default=None, help="模型名称（默认使用 QWEN_MODEL 环境变量或 qwen-turbo）")
    args = parser.parse_args()

    if not os.getenv("DASHSCOPE_API_KEY"):
        sys.exit("ERROR: missing DASHSCOPE_API_KEY")

    input_path = Path(args.input)
    output_path = Path(args.output)
    error_path = output_path.with_suffix(".errors.jsonl")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 加载输入
    rows = load_jsonl(input_path)
    if args.limit:
        rows = rows[: args.limit]

    # 断点续传：加载已完成的 episode_id
    completed = load_completed_ids(output_path)
    if completed:
        logger.info(f"Resume: {len(completed)} already done, skipping")

    # 过滤出待处理行
    to_process = [r for r in rows if r["episode_id"] not in completed]
    if not to_process:
        logger.info("All rows already processed.")
        return

    logger.info(f"Processing {len(to_process)} rows (concurrency={args.concurrency})")

    agent = BraggingResponseAgent(model=args.model)
    sem = asyncio.Semaphore(args.concurrency)

    async def bounded_process(row):
        async with sem:
            await process_one(agent, row, output_path, error_path, completed)

    tasks = [bounded_process(row) for row in to_process]
    await asyncio.gather(*tasks)

    logger.info(f"Done. Output: {output_path}, Errors: {error_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted.")
