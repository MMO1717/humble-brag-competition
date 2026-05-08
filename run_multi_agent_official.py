#!/usr/bin/env python3
"""
run_multi_agent_official.py
Multi-Agent pipeline runner for BRAG-Agent v6.
Outputs JSONL (one JSON per line) compatible with format_checker.py.

Usage:
  python run_multi_agent_official.py \
    --input BRAG-Agent-public/data/dev_input.jsonl \
    --output outputs/dev_submission_multi_v1.jsonl \
    --concurrency 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))

from src.BraggingResponseAgent import AgentInput
from src.MultiAgentBraggingAgent import MultiAgentBraggingAgent


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_completed_ids(path: Path) -> set[str]:
    """Load episode_ids already present in output file for resume."""
    if not path.exists():
        return set()
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                obj = json.loads(line)
                if "episode_id" in obj and "error" not in obj:
                    ids.add(obj["episode_id"])
            except json.JSONDecodeError:
                pass
    return ids


async def process_one(
    agent: MultiAgentBraggingAgent,
    ep: dict,
    output_path: Path,
    error_path: Path,
    lock: asyncio.Lock,
    stats_lock: asyncio.Lock,
) -> None:
    eid = ep["episode_id"]
    try:
        inp = AgentInput(
            episode_id=eid,
            speaker_post=ep["speaker_post"],
            platform=ep.get("platform", "微信朋友圈"),
            relationship=ep.get("relationship", "普通朋友"),
            agent_role=ep.get("agent_role", "旁观者"),
            interaction_goal=ep.get("interaction_goal", "维持友好关系"),
        )
        out, meta = await agent.arun(inp)
        row = asdict(out)

        async with lock:
            with open(output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        status = "OK"
        if meta.get("rewrite_attempted"):
            status = f"REWRITE({meta.get('rewrite_status', '?')})"
        logger.info(f"[{eid}] {status} strategy={out.response_strategy} mechanism={out.bragging_mechanism}")

    except Exception as e:
        logger.error(f"[{eid}] FAILED: {e}")
        error_row = {"episode_id": eid, "error": str(e)}
        async with lock:
            with open(error_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_row, ensure_ascii=False) + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="BRAG-Agent Multi-Agent Runner")
    parser.add_argument("--input", required=True, help="Input JSONL file")
    parser.add_argument("--output", default="outputs/dev_submission_multi_v1.jsonl",
                        help="Output JSONL file")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max episodes to process")
    parser.add_argument("--concurrency", type=int, default=3,
                        help="Max concurrent requests")
    parser.add_argument("--model", default=None,
                        help="Override model name")
    args = parser.parse_args()

    if not os.getenv("DASHSCOPE_API_KEY"):
        sys.exit("ERROR: DASHSCOPE_API_KEY not set")

    input_path = Path(args.input)
    output_path = Path(args.output)
    error_path = output_path.with_suffix(".errors.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load input
    episodes = load_jsonl(input_path)
    if args.limit:
        episodes = episodes[:args.limit]

    # Resume support: skip already completed
    completed_ids = load_completed_ids(output_path)
    if completed_ids:
        logger.info(f"Resume: {len(completed_ids)} already completed, skipping.")
    to_process = [ep for ep in episodes if ep["episode_id"] not in completed_ids]

    if not to_process:
        logger.info("All episodes already processed.")
        return

    logger.info(f"Processing {len(to_process)} episodes (concurrency={args.concurrency})")

    agent = MultiAgentBraggingAgent(model=args.model)
    lock = asyncio.Lock()
    stats_lock = asyncio.Lock()
    sem = asyncio.Semaphore(args.concurrency)

    async def bounded(ep):
        async with sem:
            await process_one(agent, ep, output_path, error_path, lock, stats_lock)

    start = time.time()
    await asyncio.gather(*[bounded(ep) for ep in to_process])
    elapsed = time.time() - start

    # Print stats
    s = agent.stats
    logger.info("=" * 50)
    logger.info(f"Done in {elapsed:.1f}s")
    logger.info(f"Total: {s['total']}")
    logger.info(f"Generator OK (no rewrite): {s['generator_ok']}")
    logger.info(f"Rewrite triggered: {s['rewrite_triggered']}")
    logger.info(f"Rewrite success: {s['rewrite_success']}")
    logger.info(f"Rewrite failed: {s['rewrite_failed']}")
    logger.info(f"Auto-fix fallback: {s['autofix_used']}")
    if s["issue_codes"]:
        logger.info(f"Issue codes: {s['issue_codes']}")
    logger.info(f"Output: {output_path}")
    logger.info(f"Errors: {error_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted.")
