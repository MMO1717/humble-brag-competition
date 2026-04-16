"""
experiments.py
存放实验任务数据集（Level 1~3），并负责执行实验和格式化输出。
"""

# 数据集设计
TASKS = {
    "L1": {
        "description": "经典逻辑与常识题（验证基础逻辑和惊吓反应）",
        "prompt": "树上有10只鸟，开枪打死1只，还在树上剩几只？"
    },
    "L2": {
        "description": "带有隐蔽逻辑陷阱的数学题（验证推理深度）",
        "prompt": "如果 3 只猫 3 分钟能抓 3 只老鼠，那么 100 只猫抓 100 只老鼠需要多少分钟？"
    },
    "L3": {
        "description": "高歧义性/多解物理逻辑题（测试 Curator 在无绝对答案边界时的终止判定能力）",
        "prompt": "一个在真空、无重力空间中静止的密封箱子，内部有一只鸟在飞。请问箱子的整体质量相比鸟停在箱底时会改变吗？"
    }
}

def print_experiment_result(result: dict, use_curator: bool):
    """
    格式化输出单个实验结果。
    """
    mode = "ON" if use_curator else "OFF"
    print("\n" + "="*60)
    print(f"📊 实验结果总结 [Curator: {mode}]")
    print("="*60)
    print(f"- 最终状态: {result['status']}")
    print(f"- 会话轮数: {result['turns']} 轮")
    print(f"- Curator 干预次数: {result['curator_interventions']} 次")
    print(f"- 总 Token 消耗: {result['tokens_used']} tokens")
    print("-" * 60)
    print(f"🥇 Alpha 最终言论摘录:\n{result['final_alpha'][:200]}...")
    print("-" * 60)
    print(f"🥈 Beta 最终言论摘录:\n{result['final_beta'][:200]}...")
    print("="*60 + "\n")
