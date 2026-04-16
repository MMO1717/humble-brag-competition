#!/usr/bin/env python3
"""
Single-Agent Baseline Test (基准测试)
直接调用 Qwen 模型对 10 道 KKS 逻辑题进行单次推理，不启用多智能体辩论框架。
用于对比 MAD 架构对逻辑纠偏的实际增益。
"""

import asyncio
import json
import time
from openai import AsyncOpenAI
from evaluator import evaluate_ground_truth, compute_physio_reward

# API配置 (保持与 test_small_batch.py 一致)
API_KEY = "sk-0aa2c639890944c49abb1ebb72e6a68b"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_ID = "qwen3.5-27b"

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

async def run_single_inference(task_id: int, quiz: str, solution: str):
    """单次模型推理测试"""
    print(f"\n{'='*60}")
    print(f"🎯 [基准任务 {task_id}] 直接推理...")
    print(f"   问题: {quiz[:80]}...")
    print(f"{'='*60}")

    start_time = time.time()
    try:
        # 模拟最直接的单次 Prompt 触发
        response = await client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": "You are a logical reasoning expert. Solve the puzzle step by step and give the final answer."},
                {"role": "user", "content": f"Logic Puzzle:\n{quiz}"}
            ],
            temperature=0.1 # 尽量保证结果稳定
        )
        
        reply_text = response.choices[0].message.content
        total_tokens = response.usage.total_tokens
        elapsed = time.time() - start_time
        
        # 评判
        is_correct = evaluate_ground_truth(reply_text, solution)
        
        # 计算 Reward (以便对比)
        reward = compute_physio_reward(
            is_correct=is_correct,
            interventions=0, # 单智能体无干预
            turns_used=1,    # 固定 1 回合
            d_sem_avg=1.0,   # 无语义对比
            p_eeg_avg=0.0,   # 中性值
            total_tokens=total_tokens,
            prompt_text=quiz
        )

        print(f"🤖 模型回复片段: {reply_text[:150]}...")
        print(f"✅ 判定结果: {'✓ 正确' if is_correct else '✗ 错误'}")
        print(f"⏱️  耗时: {elapsed:.1f}s | Tokens: {total_tokens} | Reward: {reward:.2f}")

        return {
            "task_id": task_id,
            "is_correct": is_correct,
            "tokens": total_tokens,
            "reward": reward,
            "elapsed": elapsed
        }

    except Exception as e:
        print(f"❌ 推理失败: {e}")
        return None

async def main():
    print("🧪 开始执行 Single-Agent 原生能力基准测试...")
    
    # 加载数据集
    import os
    data_path = os.path.join(os.path.dirname(__file__), "kks_test_10.json") or "kks_test_10.json"
    
    with open(data_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    results = []
    for i, item in enumerate(test_data[:10]):
        res = await run_single_inference(i+1, item["quiz"], item["solution_text"])
        results.append(res)
        await asyncio.sleep(0.5) # 避开频率限制

    # 统计
    valid = [r for r in results if r]
    total = len(valid)
    acc = sum(1 for r in valid if r["is_correct"]) / total * 100
    avg_tokens = sum(r["tokens"] for r in valid) / total
    avg_reward = sum(r["reward"] for r in valid) / total

    print(f"\n{'#'*60}")
    print(f"📊 基准测试总结 (Single-Agent Baseline)")
    print(f"{'#'*60}")
    print(f"✅ 原生准确率: {acc:.1f}%")
    print(f"📉 平均 Token 消耗: {avg_tokens:.1f}")
    print(f"📈 平均奖励值 (R): {avg_reward:.2f}")
    print(f"{'#'*60}")
    
    # 保存基准数据用于对比
    with open("baseline_results.json", "w", encoding="utf-8") as f:
        json.dump(valid, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
