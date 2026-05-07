#!/usr/bin/env python3
"""
run.py
ACL 2025 凡尔赛回应 Agent 的主运行入口。

用法：
  # 单条测试
  python run.py --text "唉，这个月又要飞巴黎开会了，真羡慕能在家宅着的人"

  # 批量跑数据集（输出到 results/output.json）
  python run.py --dataset Bragging_data.json --output results/output.json

  # 指定平台和关系
  python run.py --text "随便写了个项目，GitHub 破万 Star 了" --platform 开发者群 --relationship 同行
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# 确保 src 包可被导入
sys.path.insert(0, str(Path(__file__).parent))

from src.BraggingResponseAgent import BraggingResponseAgent, AgentInput
from src.prompts import run_bragging_agent, run_batch


def _single_mode(args: argparse.Namespace) -> None:
    out = run_bragging_agent(
        speaker_post=args.text,
        episode_id="cli_test",
        platform=args.platform,
        relationship=args.relationship,
        agent_role=args.agent_role,
        interaction_goal=args.goal,
    )
    print("\n" + "─" * 60)
    print(f"📌 言论: {args.text}")
    print("─" * 60)
    print(f"🔍 炫耀机制:   {out.bragging_mechanism}")
    print(f"🎯 真实意图:   {out.speaker_intention}")
    print(f"💬 期望反馈:   {out.desired_feedback}")
    print(f"⚠️  风险评估:   {out.risk_assessment}")
    print(f"🃏 回应策略:   {out.response_strategy}")
    print(f"✅ 最佳回应:\n   {out.response_text}")
    print("─" * 60 + "\n")


def _batch_mode(args: argparse.Namespace) -> None:
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        sys.exit(f"数据集文件不存在: {dataset_path}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 加载已有结果（断点续传）
    results = []
    processed_ids = set()
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                results = json.load(f)
                # 提取已成功处理的 episode_id（排除 error 条目）
                processed_ids = {r["episode_id"] for r in results if isinstance(r, dict) and "error" not in r}
                logging.info(f"检测到已有结果文件，已成功跳过 {len(processed_ids)} 条已处理数据。")
        except Exception as e:
            logging.warning(f"读取已有结果失败（可能文件损坏或非 JSON 格式）: {e}")

    # 2. 准备待处理数据
    with open(dataset_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    episodes_to_process = []
    for i, item in enumerate(raw_data):
        eid = f"ep_{i:04d}"
        if eid in processed_ids:
            continue
        
        episodes_to_process.append({
            "episode_id": eid,
            "speaker_post": item.get("speaker_post") or item.get("original_text", ""),
            "platform": item.get("platform", "微信朋友圈"),
            "relationship": item.get("relationship", "普通朋友"),
            "agent_role": item.get("agent_role", "旁观者"),
            "interaction_goal": item.get("interaction_goal", "维持友好关系"),
        })

    if args.limit:
        episodes_to_process = episodes_to_process[: args.limit]

    if not episodes_to_process:
        logging.info("所有数据已处理完毕，无需运行。")
        return

    logging.info(f"共 {len(episodes_to_process)} 条待处理数据，开始增量保存模式…")
    
    # 3. 循环处理并实时保存
    try:
        for ep in episodes_to_process:
            try:
                out = run_bragging_agent(
                    speaker_post=ep["speaker_post"],
                    episode_id=ep["episode_id"],
                    platform=ep["platform"],
                    relationship=ep["relationship"],
                    agent_role=ep["agent_role"],
                    interaction_goal=ep["interaction_goal"]
                )
                
                # 记录结果并立刻写入硬盘
                results.append(asdict(out))
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
                logging.info(f"[episode={ep['episode_id']}] ✓ 已实时同步 - strategy={out.response_strategy}")
                
            except Exception as e:
                # 如果是模型解析错误，记录错误信息并保存，继续下一条
                logging.error(f"[episode={ep['episode_id']}] ✗ 失败: {e}")
                results.append({"episode_id": ep["episode_id"], "error": str(e)})
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

    except KeyboardInterrupt:
        logging.info("\n检测到用户中断。当前进度已安全保存。")
        
    success_count = sum(1 for r in results if isinstance(r, dict) and "error" not in r)
    logging.info(f"任务结束。总计成功条数: {success_count} / {len(raw_data)}，结果保存在 {output_path}")



def main() -> None:
    parser = argparse.ArgumentParser(description="凡尔赛回应 Agent Runner")
    sub = parser.add_subparsers(dest="mode")

    # 单条模式
    p_single = sub.add_parser("single", help="单条文本测试")
    p_single.add_argument("--text", required=True, help="凡尔赛原文")
    p_single.add_argument("--platform", default="微信朋友圈")
    p_single.add_argument("--relationship", default="普通朋友")
    p_single.add_argument("--agent-role", default="旁观者")
    p_single.add_argument("--goal", default="维持友好关系")

    # 批量模式
    p_batch = sub.add_parser("batch", help="批量跑数据集")
    p_batch.add_argument("--dataset", default="Bragging_data.json")
    p_batch.add_argument("--output", default="results/output.json")
    p_batch.add_argument("--limit", type=int, default=None, help="只处理前 N 条（调试用）")

    # 兼容直接 --text 的简洁用法
    parser.add_argument("--text", help="凡尔赛原文（快速单条测试）")
    parser.add_argument("--platform", default="微信朋友圈")
    parser.add_argument("--relationship", default="普通朋友")
    parser.add_argument("--agent-role", default="旁观者")
    parser.add_argument("--goal", default="维持友好关系")
    parser.add_argument("--dataset", default="Bragging_data.json")
    parser.add_argument("--output", default="results/output.json")
    parser.add_argument("--limit", type=int, default=None)

    args = parser.parse_args()

    # 检查 API Key
    if not os.getenv("DASHSCOPE_API_KEY"):
        sys.exit("❌ 缺少 DASHSCOPE_API_KEY，请复制 .env.example 为 .env 并填入 API Key。")

    if args.mode == "single" or (args.mode is None and args.text):
        _single_mode(args)
    elif args.mode == "batch" or (args.mode is None and not args.text):
        _batch_mode(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
