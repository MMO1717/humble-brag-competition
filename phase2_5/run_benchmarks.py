"""
run_benchmarks.py
Phase 2.5 综合自动化基准测试 (Qwen / DashScope 版本)。
"""

import sys
import asyncio
import os
import time

from eeg_sensor import eeg_sensor_instance
from mas_controller import MAS_Controller
from evaluator import compute_physio_reward, evaluate_ground_truth

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 阿里云 DashScope 配置
API_KEY = os.getenv("DASHSCOPE_API_KEY")
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_ID = os.getenv("DASHSCOPE_MODEL_ID", "qwen-turbo")

# Mini Benchmark DB (GSM8K/MATH simplified)
BENCHMARKS = [
    {
        "id": "MATH_001",
        "task": "一个水池，单开甲管 4 小时注满，单开乙管 6 小时注满。若甲乙齐开，同时底部漏洞每小时漏掉总水量的 1/12。池满需多少小时？",
        "expected_kw": ["3", "三"], # 1/(1/4 + 1/6 - 1/12) = 1/(1/3) = 3
    },
    {
         "id": "GSM8K_012",
         "task": "Alice bought 3 apples for $2 each. She paid with a $10 bill. But wait, the cashier says apples are actually 3 for $5. How much change does she get?",
         "expected_kw": ["5", "five", "五"], # 10 - 5 = 5
    }
]

async def run_single_benchmark(bm: dict, mock_fatigue: bool = False):
    print(f"\n=============================================")
    print(f"🚀 Running Benchmark: {bm['id']} (Qwen-Turbo)")
    print(f"   Human Fatigue Mock: OFF [PROMPT-ONLY MODE]")
    print(f"=============================================")
    
    eeg_sensor_instance.set_mock_human_fatigue(mock_fatigue)
    time.sleep(2) 
    
    # 传入 Qwen 的 API 配置
    controller = MAS_Controller(api_key=API_KEY, model_id=MODEL_ID, base_url=BASE_URL)
    result = await controller.run_collaboration(task=bm["task"], max_turns=3)
    
    print("\n--- 实验结束，提取数据并执行 Reward 评价 ---")
    
    is_correct = evaluate_ground_truth(result["final_answer"], bm["expected_kw"])
    p_eeg_grad = eeg_sensor_instance.get_attention_gradient(window=5)
    d_sem_avg = 0.5 # 占位符
    
    R = compute_physio_reward(
        is_correct=is_correct,
        interventions=result["curator_interventions"],
        turns_used=result["turns"],
        d_sem_avg=d_sem_avg,
        p_eeg_avg=p_eeg_grad,
        total_tokens=result["tokens_used"],
        prompt_text=bm["task"]
    )
    
    print(f"✅ Accuracy Check: {'PASSED' if is_correct else 'FAILED'}")
    print(f"⚡ Status: {result['status']} | Turns: {result['turns']} | Tokens: {result['tokens_used']}")
    print(f"🧠 Interventions: {result['curator_interventions']} | Peak Physio Loss: {p_eeg_grad:.2f}")
    print(f"💰 Computed Total Reward (R): {R:.2f}")
    
    return R

async def main():
    print("⏳ [PROMPT-ONLY MODE] 跳过 EEG 硬件检测，专注于模型 Prompt 表现...")
    eeg_sensor_instance.start_sampling()
    time.sleep(1) 
    
    rewards = []
    
    try:
        # Run BM 1 with stable human attention
        r1 = await run_single_benchmark(BENCHMARKS[0], mock_fatigue=False)
        rewards.append(r1)
        
        # Run BM 2 with dropping human attention
        r2 = await run_single_benchmark(BENCHMARKS[1], mock_fatigue=True)
        rewards.append(r2)
        
        print("\n\n" + "#"*50)
        print("🎯 BATCH COMPLETE (Qwen Backend)")
        print(f"Avg Reward: {sum(rewards)/len(rewards):.2f}")
        print("#"*50)
            
    finally:
        eeg_sensor_instance.stop_sampling()
        print("EEG Mock Daemon shutdown.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error during benchmarks: {e}")
