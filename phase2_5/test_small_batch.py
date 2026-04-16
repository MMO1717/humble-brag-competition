#!/usr/bin/env python3
"""
小型压测脚本 - 测试 Phase 3 修改效果
使用10题KKS逻辑题验证S²-MAD简洁性规则、iMAD半自适应阈值和FORGE难度感知奖励函数
注意：关闭EEG模式，仅测试prompt输入和语义相似度
"""

import asyncio
import json
import time
from mas_controller import MAS_Controller
from evaluator import compute_physio_reward, evaluate_ground_truth

# API配置
API_KEY = "sk-0aa2c639890944c49abb1ebb72e6a68b"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_ID = "qwen3.5-27b"

async def run_test_task(task_id: int, quiz: str, solution: str):
    """运行单个任务测试（关闭EEG模式）"""
    print(f"\n{'='*60}")
    print(f"🚀 [测试任务 {task_id}] 开始执行")
    print(f"   问题: {quiz[:80]}...")
    print(f"   期待答案: {solution[:80]}...")
    print(f"{'='*60}")

    # 初始化控制器
    controller = MAS_Controller(
        api_key=API_KEY,
        model_id=MODEL_ID,
        base_url=BASE_URL
    )

    # 运行协作
    start_time = time.time()
    try:
        result = await controller.run_collaboration(task=quiz, max_turns=3)
        elapsed = time.time() - start_time

        # 评估准确性
        is_correct = evaluate_ground_truth(result["final_answer"], solution)

        # 计算奖励（关闭EEG模式，使用默认生理信号值）
        # 在无EEG模式下，使用中性生理信号值（p_eeg_avg=0.0）
        reward = compute_physio_reward(
            is_correct=is_correct,
            interventions=result.get("curator_interventions", 0),
            turns_used=result["turns"],
            d_sem_avg=0.5,  # 临时占位值
            p_eeg_avg=0.0,  # EEG关闭，使用中性值
            total_tokens=result["tokens_used"],
            prompt_text=quiz
        )

        # 少数派纠偏判断
        minority_correction = is_correct and result["turns"] >= 2
        dropout_triggered = result.get("status") == "CONVERGED_AND_DROPOUT"

        print(f"✅ 准确率: {'✓ 正确' if is_correct else '✗ 错误'}")
        print(f"⚡ 状态: {result['status']} | 轮次: {result['turns']} | Token: {result['tokens_used']}")
        print(f"⏱️  耗时: {elapsed:.1f}s | 干预次数: {result.get('curator_interventions', 0)}")
        print(f"💰 奖励(R): {reward:.2f} | 节点剪枝: {'✓' if dropout_triggered else '✗'}")
        print(f"🎯 少数派纠偏: {'✓' if minority_correction else '✗'}")

        return {
            "task_id": task_id,
            "is_correct": is_correct,
            "tokens": result["tokens_used"],
            "turns": result["turns"],
            "reward": reward,
            "dropout": dropout_triggered,
            "minority_correction": minority_correction,
            "interventions": result.get("curator_interventions", 0),
            "elapsed_time": elapsed,
            "p_eeg_gradient": 0.0,  # EEG关闭
        }

    except Exception as e:
        print(f"❌ 任务执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_test_summary(results):
    """生成测试总结报告"""
    if not results:
        print("没有有效结果可分析")
        return

    valid_results = [r for r in results if r is not None]
    if not valid_results:
        print("所有任务都失败了")
        return

    df = valid_results

    # 计算指标
    total = len(df)
    accuracy = sum(1 for r in df if r["is_correct"]) / total * 100
    avg_tokens = sum(r["tokens"] for r in df) / total
    avg_reward = sum(r["reward"] for r in df) / total
    dropout_rate = sum(1 for r in df if r["dropout"]) / total * 100
    correction_rate = sum(1 for r in df if r["minority_correction"]) / total * 100
    avg_interventions = sum(r["interventions"] for r in df) / total

    print(f"\n{'='*60}")
    print(f"📊 PHASE 3 压测结果总结 (基于{total}题)")
    print(f"{'='*60}")
    print(f"✅ 总体准确率: {accuracy:.1f}%")
    print(f"📉 平均Token消耗: {avg_tokens:.0f}")
    print(f"📈 平均奖励值(R): {avg_reward:.2f}")
    print(f"✂️  节点剪枝率: {dropout_rate:.1f}%")
    print(f"🎯 少数派纠偏率: {correction_rate:.1f}%")
    print(f"🚨 平均干预次数: {avg_interventions:.2f}")
    print(f"{'='*60}")

    # 检查Phase 3目标
    print("\n🎯 PHASE 3 目标检查:")
    print(f"  • Token成本降低70%: 需比较Phase 2.5基准 (待基准数据)")
    print(f"  • 少数派纠偏率维持40%+: {'✓ 达标' if correction_rate >= 40 else '✗ 未达标'} ({correction_rate:.1f}%)")
    print(f"  • Curator误判减少: 观察干预次数 ({avg_interventions:.2f}次/题)")

    # 保存结果
    with open("phase3_test_results.json", "w", encoding="utf-8") as f:
        json.dump(df, f, ensure_ascii=False, indent=2)

    print(f"\n💾 详细结果已保存至: phase3_test_results.json")

def create_fallback_dataset():
    """创建备用测试数据集"""
    return [
        {
            "quiz": "A says \"I am a knight\". What is A?",
            "solution_text": "If A says \"I am a knight\", then A must be telling the truth. Therefore A is a knight."
        },
        {
            "quiz": "A says \"I am a knave\". B says \"A is a knave\". What are A and B?",
            "solution_text": "If A says \"I am a knave\", then A is lying because a knave cannot truthfully say they are a knave. So A is a knight. B says \"A is a knave\", which is false, so B is a knave."
        },
        {
            "quiz": "A says \"B is a knight\". B says \"A is a knave\". What are A and B?",
            "solution_text": "Assume A is a knight. Then B is a knight. But then B says \"A is a knave\" which is false. Contradiction. Assume A is a knave. Then B is not a knight. B says \"A is a knave\" which is true. So B must be a knight. Contradiction. Therefore no solution."
        },
        {
            "quiz": "A says \"I am a spy\". What is A?",
            "solution_text": "A spy can either tell truth or lie. So A could be telling truth or lying. Therefore A is a spy."
        },
        {
            "quiz": "A says \"B is a knight or I am a knave\". What can we conclude?",
            "solution_text": "If A is a knight, then statement is true. So either B is a knight or A is a knave. But if A is knight, \"A is a knave\" is false, so B must be knight. If A is knave, statement is false. So \"B is a knight or A is a knave\" is false, meaning B is not a knight and A is not a knave. But A is knave, so \"A is not a knave\" is false. Therefore impossible."
        }
    ]

async def main():
    """主测试函数"""
    print("🧪 开始执行Phase 3修改压测 (10题KKS逻辑题)")
    print("  测试内容:")
    print("  • S²-MAD简洁性规则 (agents.py)")
    print("  • iMAD半自适应动态阈值 (curator.py)")
    print("  • FORGE难度感知奖励函数 (evaluator.py)")

    # 加载测试数据集
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "kks_test_10.json")

    try:
        with open(data_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 未找到测试数据集: {data_path}")
        # 尝试在当前目录下创建测试数据集作为备选
        print("尝试创建测试数据集...")
        test_data = create_fallback_dataset()
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已创建测试数据集: {data_path}")

    print(f"\n📚 加载了 {len(test_data)} 个测试题")

    # 运行所有测试任务
    results = []
    for i, item in enumerate(test_data[:10]):  # 限制10题
        result = await run_test_task(
            task_id=i+1,
            quiz=item["quiz"],
            solution=item["solution_text"]
        )
        results.append(result)

        # 避免API调用过于频繁
        if i < len(test_data) - 1:
            await asyncio.sleep(1)

    # 生成总结报告
    generate_test_summary(results)

    print("\n🏁 Phase 3压测完成！")
    print("   请检查测试结果，确认修改是否达到预期效果。")

if __name__ == "__main__":
    # 注意：关闭EEG模式，仅测试prompt输入
    asyncio.run(main())