"""
run_experiment.py
Phase 2 多智能体系统主入口，执行基准测试和验证。
"""

import sys
import asyncio
import os

# 将上级目录加入 sys.path, 为了能够复用上一阶段配置信息，虽然不在同一目录，但目前都是独立文件
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mas_controller import MAS_Controller
from experiments import TASKS, print_experiment_result

# 请确保填写有效的 API_KEY，建议与 agent_test.py 保持一致
API_KEY = "AIzaSyBVqimXAWUTASKwUZQ9NBifCJZb_iRmcLQ"  
MODEL_ID = "gemini-3-flash-preview"

async def run_scenario(level: str, use_curator: bool):
    task_desc = TASKS[level]["prompt"]
    print(f"\n========================================================")
    print(f"🚀 发起测试: {level} | Curator 状态: {'开启(ON)' if use_curator else '关闭(OFF)'}")
    print(f"📌 任务描述: {TASKS[level]['description']}")
    print(f"💬 问题: {task_desc}")
    print(f"========================================================")

    controller = MAS_Controller(api_key=API_KEY, model_id=MODEL_ID)
    
    # 执行最高 3 轮的辩论
    result = await controller.run_collaboration(task=task_desc, max_turns=3, use_curator=use_curator)
    
    print_experiment_result(result, use_curator)
    return result

async def main():
    if API_KEY == "YOUR_API_KEY":
        print("❌ 错误：请先在 run_experiment.py 中填入有效的 API_KEY！")
        return

    print("开始 Phase 2 实验：拓扑剪枝与防懒惰验证...\n")

    # [实验 1]：L1 题目，对比有无 Curator 对 Token 消耗和通信轮数的影响
    print(">>> 实验组 I: 通信图剪枝测试 (L1 题目)")
    # 不带 Curator (基线)
    res_baseline = await run_scenario("L1", use_curator=False)
    # 带 Curator (动态剪枝)
    res_pruned = await run_scenario("L1", use_curator=True)

    print("\n" + "#"*60)
    print("📈 L1 实验对比结论:")
    print(f"无 Curator 总 Token: {res_baseline['tokens_used']} (进行了 {res_baseline['turns']} 轮)")
    print(f"有 Curator 总 Token: {res_pruned['tokens_used']} (进行了 {res_pruned['turns']} 轮)")
    
    if res_pruned['tokens_used'] < res_baseline['tokens_used']:
        savings = (res_baseline['tokens_used'] - res_pruned['tokens_used']) / res_baseline['tokens_used'] * 100
        print(f"🎉 Curator 成功切断了冗余通信！Token 节约率: {savings:.1f}%")
    else:
        print("ℹ️ Curator 介入本身产生了一定 Token 消耗，或者双方辩论激烈且未达收敛。")
    print("#"*60 + "\n")

    # [实验 2]：L2 题目（仅测试带 Curator）
    print(">>> 实验组 II: 防懒惰与深层逻辑挖掘 (L2 题目)")
    await run_scenario("L2", use_curator=True)

if __name__ == "__main__":
    try:
         asyncio.run(main())
    except Exception as e:
         print(f"❌ 运行失败: {e}")
