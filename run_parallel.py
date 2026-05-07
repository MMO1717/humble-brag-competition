#!/usr/bin/env python3
"""
run_parallel.py
凡尔赛回应 Agent 异步并发版。

通过 asyncio 实现多路并发请求，极大提升处理速度。
默认并发数为 5，可根据 API 限制自行调整。
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

sys.path.insert(0, str(Path(__file__).parent))

from src.BraggingResponseAgent import BraggingResponseAgent, AgentInput

# ── 并发配置 ──────────────────────────────────────────────────────────────
MAX_CONCURRENT_REQUESTS = 5  # 建议初次测试设为 5，后续可尝试提升至 10-20
SAVE_LOCK = asyncio.Lock()   # 确保多协程写文件时不冲突


async def process_episode(agent, ep: Dict[str, Any], results: List[Dict[str, Any]], output_path: Path, sem: asyncio.Semaphore):
    """单条数据处理协程"""
    eid = ep["episode_id"]
    async with sem:
        try:
            inp = AgentInput(
                episode_id=eid,
                speaker_post=ep["speaker_post"],
                platform=ep.get("platform", "微信朋友圈"),
                relationship=ep.get("relationship", "普通朋友"),
                agent_role=ep.get("agent_role", "旁观者"),
                interaction_goal=ep.get("interaction_goal", "维持友好关系"),
            )
            
            # 使用异步方法调用大模型
            out = await agent.arun(inp)
            data = asdict(out)
            
            # 实时保存（加锁保护）
            async with SAVE_LOCK:
                results.append(data)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
            
            logging.info(f"[{eid}] ✓ 成功 | 策略: {out.response_strategy:<20} | 回应: {out.response_text[:20]}...")
            
        except Exception as e:
            logging.error(f"[{eid}] ✗ 失败: {e}")
            async with SAVE_LOCK:
                results.append({"episode_id": eid, "error": str(e)})
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="凡尔赛 Agent 异步并发 Runner")
    parser.add_argument("--dataset", default="Bragging_data.json")
    parser.add_argument("--output", default="results/output.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=MAX_CONCURRENT_REQUESTS)
    args = parser.parse_args()

    if not os.getenv("DASHSCOPE_API_KEY"):
        sys.exit("❌ 缺少 DASHSCOPE_API_KEY")

    dataset_path = Path(args.dataset)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 加载已有结果
    results = []
    processed_ids = set()
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                results = json.load(f)
                processed_ids = {r["episode_id"] for r in results if "error" not in r}
                logging.info(f"断点续传：跳过已处理的 {len(processed_ids)} 条数据。")
        except:
            pass

    # 2. 读取数据集
    with open(dataset_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    to_process = []
    for i, item in enumerate(raw_data):
        eid = f"ep_{i:04d}"
        if eid in processed_ids:
            continue
        to_process.append({
            "episode_id": eid,
            "speaker_post": item.get("speaker_post") or item.get("original_text", ""),
            "platform": item.get("platform", "微信朋友圈"),
            "relationship": item.get("relationship", "普通朋友"),
            "agent_role": item.get("agent_role", "旁观者"),
            "interaction_goal": item.get("interaction_goal", "维持友好关系"),
        })

    if args.limit:
        to_process = to_process[:args.limit]

    if not to_process:
        logging.info("所有任务已完成！")
        return

    logging.info(f"🚀 开始并发处理：并发数={args.concurrency}, 剩余任务={len(to_process)}")
    
    agent = BraggingResponseAgent()
    sem = asyncio.Semaphore(args.concurrency)
    
    # 创建所有任务
    tasks = [process_episode(agent, ep, results, output_path, sem) for ep in to_process]
    
    # 并发执行
    await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if "error" not in r)
    logging.info(f"🏁 处理完毕！成功: {success_count}/{len(raw_data)}, 结果保存在 {output_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("收到中断信号，程序退出。")
