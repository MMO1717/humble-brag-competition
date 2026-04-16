#!/usr/bin/env python3
"""
Single-Agent Baseline Test with CoSTAR Framework
使用完整的 CoSTAR 框架结构对 10 道 KKS 逻辑题进行单轮推理。
用于对比：[Simple Prompt] vs [CoSTAR Framework] vs [MAD 多智能体架构] 之间的性能差异。
"""

import asyncio
import json
import time
from openai import AsyncOpenAI
from evaluator import evaluate_ground_truth, compute_physio_reward

# API配置
API_KEY = "sk-0aa2c639890944c49abb1ebb72e6a68b"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_ID = "qwen3.5-27b"

# CoSTAR 系统提示词定义
COSTAR_SYSTEM_PROMPT = """
# Context
You are a master logic puzzle solver specializing in "Knights, Knaves, and Spies" logic puzzles. You are operating in a rigorous benchmarking environment.

# Objective
Provide a 100% accurate solution to the provided logic puzzle. You must verify that the roles assigned to every character (A, B, C, etc.) are perfectly consistent with the rules of the puzzle and the statements made by those characters.

# Style
Provide a rigorous, step-by-step logical deduction using formal logic and the process of elimination (Chain-of-Thought).

# Tone
Analytical, objective, and precise. Avoid any conversational filler.

# Audience
Logic experts and researchers evaluating your deep reasoning capabilities.

# Response Format (MANDATORY)
You must output exactly in the following format:
<Rationale>
[Detailed step-by-step logical deduction. Prove why your answer is the only possibility.]
</Rationale>
<Response>
[The final definitive answer: e.g., A is a Knight, B is a Knave.]
</Response>
"""

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

async def run_costar_inference(task_id: int, quiz: str, solution: str):
    """使用 CoSTAR 框架的单次模型推理测试"""
    print(f"\n{'='*60}")
    print(f"🌟 [CoSTAR 任务 {task_id}] 开始推理...")
    print(f"   问题: {quiz[:80]}...")
    print(f"{'='*60}")

    start_time = time.time()
    try:
        response = await client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": COSTAR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Logic Puzzle to Solve:\n{quiz}"}
            ],
            temperature=0.1 # 保持稳定性以便公平对比
        )
        
        reply_text = response.choices[0].message.content
        total_tokens = response.usage.total_tokens
        elapsed = time.time() - start_time
        
        # 评判
        is_correct = evaluate_ground_truth(reply_text, solution)
        
        # 计算 Reward (以便对比)
        reward = compute_physio_reward(
            is_correct=is_correct,
            interventions=0, 
            turns_used=1,    
            d_sem_avg=1.0,   
            p_eeg_avg=0.0,   
            total_tokens=total_tokens,
            prompt_text=quiz
        )

        print(f"🤖 CoSTAR 回复片段: {reply_text[:150]}...")
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
        print(f"❌ CoSTAR 推理失败: {e}")
        return None

async def main():
    print("🧪 开始执行 Single-Agent [CoSTAR 框架] 基准测试...")
    
    # 获取数据集
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "kks_test_10.json")
    
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 未找到数据集: {data_path}")
        return

    results = []
    for i, item in enumerate(test_data[:10]):
        res = await run_costar_inference(i+1, item["quiz"], item["solution_text"])
        results.append(res)
        await asyncio.sleep(0.5)

    # 统计
    valid = [r for r in results if r]
    total = len(valid)
    if total == 0: return
    
    acc = sum(1 for r in valid if r["is_correct"]) / total * 100
    avg_tokens = sum(r["tokens"] for r in valid) / total
    avg_reward = sum(r["reward"] for r in valid) / total

    print(f"\n{'#'*60}")
    print(f"📊 CoSTAR 框架基准测试总结")
    print(f"{'#'*60}")
    print(f"✅ CoSTAR 准确率: {acc:.1f}%")
    print(f"📉 平均 Token 消耗: {avg_tokens:.1f}")
    print(f"📈 平均奖励值 (R): {avg_reward:.2f}")
    print(f"对比参考：[原生单点 80%] | [MAD 架构 25%]")
    print(f"{'#'*60}")
    
    # 保存结果
    with open("costar_baseline_results.json", "w", encoding="utf-8") as f:
        json.dump(valid, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
