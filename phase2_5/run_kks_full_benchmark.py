"""
run_kks_full_benchmark.py
Phase 2.5 测试延伸：KKS 数据集集成与全自动化跑批体系
执行多智能体抗压测试、物理共识测试，并产出最终指标与分析报告图表。
"""

import asyncio
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datasets import load_dataset
from eeg_sensor import eeg_sensor_instance
from mas_controller import MAS_Controller
from evaluator import compute_physio_reward, evaluate_ground_truth

from dotenv import load_dotenv

# 加载环境配置
load_dotenv()

# ============================================================
# API 配置 (Qwen / DashScope)
# ============================================================
API_KEY = os.getenv("DASHSCOPE_API_KEY")
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_ID = os.getenv("DASHSCOPE_MODEL_ID", "qwen-turbo")

# ============================================================
# 测试配置参数
# ============================================================
SAMPLE_SIZE = int(os.getenv("KKS_SAMPLES", "20"))
USE_MOCK_EEG = os.getenv("MOCK_EEG", "false").lower() == "true"

async def run_single_kks(index: int, data_row: dict) -> dict:
    """运行单个 KKS 测试用例并搜集指标"""
    # 修正 KKS 数据集字段映射：原来是 problem 现在是 quiz, 原来是 solution 现在是 solution_text
    problem_text = data_row.get("quiz", "")
    solution_text = data_row.get("solution_text", "")
    
    if isinstance(solution_text, list):
        solution_text = " ".join([str(x) for x in solution_text])
    else:
        solution_text = str(solution_text)
    
    print(f"\n=============================================")
    print(f"🚀 [KKS-{index}] Running Task...")
    print(f"   MOCK_EEG Status: OFF [PROMPT-ONLY MODE]")
    print(f"=============================================")
    
    # 随机模拟一下该任务中人类监督者的状态 (测试其影响)
    mock_fatigue = index % 2 != 0 if USE_MOCK_EEG else False
    eeg_sensor_instance.set_mock_human_fatigue(mock_fatigue)
    time.sleep(1) # 预留点时间生成样本梯度
    
    # 初始化控制器并运行
    controller = MAS_Controller(api_key=API_KEY, model_id=MODEL_ID, base_url=BASE_URL)
    result = await controller.run_collaboration(task=problem_text, max_turns=3)
    
    # 评判准确性
    is_correct = evaluate_ground_truth(result["final_answer"], solution_text)
    
    # 获取末状态电波梯度
    p_eeg_grad = eeg_sensor_instance.get_attention_gradient(window=5)
    
    # 计算 Reward
    d_sem_avg = 0.5 # 未完全打通 controller 层，暂用常数占位
    R = compute_physio_reward(
        is_correct=is_correct,
        interventions=result["curator_interventions"],
        turns_used=result["turns"],
        d_sem_avg=d_sem_avg,
        p_eeg_avg=p_eeg_grad,
        total_tokens=result["tokens_used"],
        prompt_text=problem_text
    )
    
    # 评估少数派抗压 (Minority Correction Asymmetry)
    # 本实验简化定义：如果在 Turn >= 2 的情况下产生了正确的结果说明辩论产生了更深的收益
    minority_correction = is_correct and result["turns"] >= 2
    
    status_node_dropout = result["status"] == "CONVERGED_AND_DROPOUT"
    
    print(f"✅ Accuracy Check: {'PASSED' if is_correct else 'FAILED'}")
    print(f"⚡ Status: {result['status']} | Turns: {result['turns']} | Tokens: {result['tokens_used']}")
    print(f"💰 Reward (R): {R:.2f} | Dropout: {status_node_dropout}")
    
    return {
        "id": index,
        "is_correct": is_correct,
        "tokens": result["tokens_used"],
        "turns": result["turns"],
        "reward": R,
        "dropout": status_node_dropout,
        "minority_correction": minority_correction,
        "interventions": result["curator_interventions"],
        "human_fatigue_mocked": mock_fatigue
    }

def generate_reports_and_plots(df: pd.DataFrame):
    """
    基于收集的 DataFrame 制图并导出 CSV
    """
    # 1. 导出 CSV
    filename_csv = "kks_results.csv"
    df.to_csv(filename_csv, index=False)
    print(f"\n📊 结果数据已导出至 {filename_csv}")
    
    # 2. 绘制 Cost-Effectiveness Pareto Front
    plt.figure(figsize=(10, 6))
    sns.scatterplot(
        data=df, 
        x="tokens", 
        y="reward", 
        hue="is_correct", 
        style="dropout",
        palette="viridis",
        s=100
    )
    plt.title("Cost-Effectiveness Pareto Front (Token vs Reward)")
    plt.xlabel("Token Cost")
    plt.ylabel("Computed Total Reward (R)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.savefig("pareto_front.png", dpi=300)
    print("📈 Pareto Front 图表已保存为 pareto_front.png")
    
    # 3. 统计汇总并生成 Markdown 报告
    accuracy = df["is_correct"].mean() * 100
    avg_tokens = df["tokens"].mean()
    avg_reward = df["reward"].mean()
    dropout_rate = df["dropout"].mean() * 100
    correction_rate = df["minority_correction"].mean() * 100
    
    markdown_content = f"""# KKS 数据集多智能体基准测试报告

**测试配置**
- 采样总数： {len(df)} 题
- EEG 干预模式 (MOCK_EEG)：{'开启' if USE_MOCK_EEG else '关闭'}

## 核心指标 (Core Metrics)
- **总体准确率 (Accuracy)**: {accuracy:.2f}%
- **平均 Token 消耗 (Avg Token Cost)**: {avg_tokens:.0f}
- **平均收益值 (Avg R Score)**: {avg_reward:.2f}
- **节点自动剪枝率 (Node Dropout Rate)**: {dropout_rate:.2f}%
- **少数派弱势正确反推率 (Minority Correction Asymmetry)**: {correction_rate:.2f}%

## 结论分析
(基于散点图与数据可见)
"""
    with open("kks_report.md", "w") as f:
        f.write(markdown_content)
    print("📝 最终分析报告已生成: kks_report.md")

async def main():
    print("⏳ [PROMPT-ONLY MODE] 跳过 EEG 硬件检测，专注于模型 Prompt 表现...")
    eeg_sensor_instance.start_sampling()
    
    try:
        # 使用国内镜像防止下载受阻
        import os
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        
        # 下载测试集 (K-and-K dataset 这份数据极其特殊：它的 config_name 是 'train'，但对应的 split_name 是 '3ppl')
        dataset = load_dataset("K-and-K/knights-and-knaves", "train", split="3ppl") 


        
        # 为了节约资源和保护限额，抽样
        dataset = dataset.shuffle(seed=42).select(range(min(SAMPLE_SIZE, len(dataset))))
        
        results = []
        for i, example in enumerate(dataset):
            row = await run_single_kks(i, example)
            results.append(row)
            
        print("\n\n" + "="*50)
        print("🎯 BATCH TESTING COMPLETE")
        print("="*50)
        
        df = pd.DataFrame(results)
        generate_reports_and_plots(df)
        
    except Exception as e:
        print(f"❌ 运行过程中发生严重错误: {e}")
        
    finally:
        eeg_sensor_instance.stop_sampling()

if __name__ == "__main__":
    asyncio.run(main())
