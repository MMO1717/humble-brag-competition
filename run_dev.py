#!/usr/bin/env python3
"""
run_dev.py
开发验证脚本：随机抽取 N 条数据，并发生成回应，并利用 LLM-as-Judge 自动打分。
最终生成 Markdown 分析报告。

用法：
  python3 run_dev.py                      # 默认随机 100 条
  python3 run_dev.py --limit 30           # 随机 30 条
  python3 run_dev.py --seed 42            # 固定随机种子
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

sys.path.insert(0, str(Path(__file__).parent))

from src.BraggingResponseAgent import BraggingResponseAgent, AgentInput
from src.BraggingEvaluator import BraggingEvaluator, EvaluationResult
from src.system import VALID_STRATEGIES

MAX_CONCURRENT = 5
SAVE_LOCK = asyncio.Lock()


async def process_evaluate(agent, evaluator, ep: dict, results: list, output_path: Path, sem: asyncio.Semaphore) -> None:
    async with sem:
        eid = ep["episode_id"]
        try:
            # 1. 生成回应
            inp = AgentInput(episode_id=eid, speaker_post=ep["speaker_post"])
            out = await agent.arun(inp)
            agent_data = asdict(out)
            
            # 2. 自动打分
            eval_res = await evaluator.aevaluate(ep["speaker_post"], agent_data)
            
            # 3. 组合结果
            eval_dict = asdict(eval_res)
            eval_dict["average_score"] = eval_res.average_score
            combined = {
                "episode": ep,
                "agent_output": agent_data,
                "evaluation": eval_dict
            }
            
            async with SAVE_LOCK:
                results.append(combined)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
            
            logging.info(f"[{eid}] ✓ 生成完成 | 策略: {out.response_strategy:<20} | 均分: {eval_res.average_score:.1f}")
        except Exception as e:
            logging.error(f"[{eid}] ✗ 失败: {e}")
            async with SAVE_LOCK:
                results.append({"episode_id": eid, "error": str(e)})
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)


def generate_markdown_report(results: list, report_path: Path, agent_model: str, eval_model: str) -> None:
    success = [r for r in results if "error" not in r]
    if not success:
        logging.warning("没有成功运行的数据，无法生成报告。")
        return
        
    n = len(success)
    avg_und = sum(r["evaluation"]["understanding_score"] for r in success) / n
    avg_str = sum(r["evaluation"]["strategy_score"] for r in success) / n
    avg_nat = sum(r["evaluation"]["naturalness_score"] for r in success) / n
    avg_ali = sum(r["evaluation"]["alignment_score"] for r in success) / n
    avg_tot = sum(r["evaluation"]["average_score"] for r in success) / n
    
    # 获取高低分样本
    sorted_by_score = sorted(success, key=lambda x: x["evaluation"]["average_score"], reverse=True)
    top_samples = sorted_by_score[:3]
    bottom_samples = sorted_by_score[-3:] if len(sorted_by_score) >= 3 else []
    
    report = f"""# 凡尔赛 Agent：LLM-as-Judge 质量评估报告

**测试详情**
- 样本数量：{n} 条
- 生成模型：`{agent_model}`
- 裁判模型：`{eval_model}`

## 1. 维度平均得分 (满分 10)

| 评估维度 | 平均分 |
| :--- | :--- |
| **状态理解质量** (准确拆解意图与机制) | **{avg_und:.1f}** |
| **策略选择合理性** (适合语境并规避风险) | **{avg_str:.1f}** |
| **回复自然度与真实性** (口语化、不油腻) | **{avg_nat:.1f}** |
| **策略与内容一致性** (回复是否落实了策略) | **{avg_ali:.1f}** |
| **综合平均分数** | **{avg_tot:.1f}** |

## 2. 策略分布直方图
"""
    # 策略分布
    strategy_counter = Counter(r["agent_output"]["response_strategy"] for r in success)
    for s in sorted(VALID_STRATEGIES):
        cnt = strategy_counter.get(s, 0)
        report += f"- `{s}`: {cnt}\n"
        
    report += "\n## 3. 典型案例分析\n\n### 🏆 优秀案例 (Top 3)\n\n"
    for r in top_samples:
        report += _format_sample(r)
        
    report += "### 🤔 待提升案例 (Bottom 3)\n\n"
    for r in reversed(bottom_samples):
        report += _format_sample(r)
        
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    logging.info(f"质量评估报告已生成：{report_path}")

def _format_sample(r: dict) -> str:
    ep = r["episode"]
    ao = r["agent_output"]
    ev = r["evaluation"]
    return f"""#### Episode: {ep['episode_id']} | 综合得分: {ev['average_score']:.1f}
- **原文**: {ep['speaker_post']}
- **提取机制**: {ao['bragging_mechanism']}
- **选择策略**: `{ao['response_strategy']}`
- **生成回复**: {ao['response_text']}
> **裁判总评**: {ev['overall_comment']} (理解:{ev['understanding_score']}, 策略:{ev['strategy_score']}, 自然:{ev['naturalness_score']}, 一致:{ev['alignment_score']})
\n"""


async def run(args: argparse.Namespace) -> None:
    dataset_path = Path(args.dataset)
    output_path = Path(args.output)
    report_path = Path(args.report)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dataset_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    random.seed(args.seed)
    indices = random.sample(range(len(raw_data)), min(args.limit, len(raw_data)))
    episodes = [
        {
            "episode_id": f"ep_{i:04d}",
            "speaker_post": raw_data[i].get("speaker_post") or raw_data[i].get("original_text", ""),
        }
        for i in sorted(indices)
    ]

    logging.info(f"随机抽取 {len(episodes)} 条（seed={args.seed}）准备评估...")

    agent = BraggingResponseAgent(model=args.model)
    evaluator = BraggingEvaluator(model=args.eval_model)
    
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    results: list = []

    tasks = [process_evaluate(agent, evaluator, ep, results, output_path, sem) for ep in episodes]
    await asyncio.gather(*tasks)

    generate_markdown_report(results, report_path, agent.model, evaluator.model)


def main() -> None:
    parser = argparse.ArgumentParser(description="凡尔赛 Agent 开发验证脚本 (带评估)")
    parser.add_argument("--dataset", default="Bragging_data.json")
    parser.add_argument("--output", default="results/dev_evaluated_100.json")
    parser.add_argument("--report", default="results/dev_evaluation_report.md")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default=None, help="Agent 模型")
    parser.add_argument("--eval_model", default="qwen-max", help="评估模型")
    args = parser.parse_args()

    if not os.getenv("DASHSCOPE_API_KEY"):
        sys.exit("❌ 缺少 DASHSCOPE_API_KEY")

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        logging.info("中断，已有结果已保存。")

if __name__ == "__main__":
    main()
