"""
curator.py
多模态判决层 (Physio-Curator / Qwen 版本)
融合本文语义特征 (D_sem) 与 物理人类注意力波动特征 (P_eeg) 执行联合判定。
使用 OpenAI 兼容模式调用 DashScope 向量计算接口。

基于 iMAD (2026) 实现半自适应动态阈值：
1. 消除固定 0.85 相似度“一刀切”问题
2. 结合输出长度、轮次、注意力梯度多因素判断
3. 实现阈值退火策略：早期轮次更宽容，后期更严格
"""

import json
import re
import numpy as np
from typing import Tuple
from openai import AsyncOpenAI
from eeg_sensor import eeg_sensor_instance

# iMAD 半自适应阈值配置
SIMILARITY_THRESHOLD_BASE = 0.82  # 下调基准，增加对“低质量重复”的敏感度
EEG_ATTENTION_DROP_THRESHOLD = -5.0 

# 阈值退火参数
TURN_ANNEALING_FACTOR = 0.015  # 减缓退火速度
MAX_TURN_FOR_ANNEALING = 6

def _compute_adaptive_threshold(turn_index: int, response_length: int, d_sem_history: list = None) -> float:
    """
    计算自适应阈值：结合轮次退火、输出长度、历史相似度模式
    """
    # 1. 轮次退火因子
    turn_factor = min(turn_index * TURN_ANNEALING_FACTOR, MAX_TURN_FOR_ANNEALING * TURN_ANNEALING_FACTOR)

    # 2. 长度因子 (针对短回复严苛)
    length_factor = -0.05 if response_length < 80 else 0.0

    # 3. 逻辑死锁检测：如果最近两轮相似度波动极小 (<0.01) 且都在 0.7 以上，说明在原地踏步
    stagnation_factor = 0.0
    if d_sem_history and len(d_sem_history) >= 2:
        diff = abs(d_sem_history[-1] - d_sem_history[-2])
        if diff < 0.01 and d_sem_history[-1] > 0.70:
            stagnation_factor = -0.05  # 大幅降低阈值，强制触发重置

    # 综合阈值计算
    base_threshold = SIMILARITY_THRESHOLD_BASE
    adaptive_threshold = base_threshold + turn_factor + length_factor + stagnation_factor

    return max(0.75, min(0.92, adaptive_threshold))

async def get_cosine_similarity(client: AsyncOpenAI, text1: str, text2: str) -> float:
    """使用 DashScope 兼容的 Embedding 接口计算余弦相似度"""
    try:
        # DashScope 推荐向量模型: text-embedding-v2
        response = await client.embeddings.create(
            model='text-embedding-v2',
            input=[text1, text2]
        )
        vec1 = response.data[0].embedding
        vec2 = response.data[1].embedding
        
        # 计算余弦相似度 = dot(A,B)/(norm(A)*norm(B))
        dot_product = sum(a*b for a, b in zip(vec1, vec2))
        norm1 = sum(a*a for a in vec1) ** 0.5
        norm2 = sum(b*b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    except Exception as e:
        print(f"⚠️ DashScope Embedding API 调用失败: {e}")
        return 0.9 if len(text2) < 50 else 0.5

async def check_physio_lazy_agreement(
    client: AsyncOpenAI,
    response_alpha: str,
    response_beta: str,
    turn_index: int = 0,
    d_sem_history: list = None
) -> Tuple[bool, str, float, float]:
    """
    判断系统是否需要强制打断 Beta 进入 [Skeptical] 或 [Aggressive]。
    融合文本语义与生理信号，使用 iMAD 半自适应动态阈值。
    """
    def extract_response(text):
        if "<Response>" in text and "</Response>" in text:
            return text.split("<Response>")[1].split("</Response>")[0].strip()
        return text.strip()

    alpha_clean = extract_response(response_alpha)
    beta_clean = extract_response(response_beta)

    # 获取 D_sem (语义相似度)
    d_sem = await get_cosine_similarity(client, alpha_clean, beta_clean)

    # 获取 P_eeg (人类专注度梯度)
    p_eeg_gradient = eeg_sensor_instance.get_attention_gradient(window=5)

    import os
    # [PROMPT-ONLY MODE] 强制跳过生理信号判定，仅使用语义相似度
    # use_mock_eeg = os.getenv("MOCK_EEG", "false").lower() == "true"
    use_mock_eeg = False

    # 极短回复拦截 (仅针对低于 10 字符的无意义回复)
    if len(beta_clean) < 10:
        return True, "Response essentially empty ( < 10 chars).", d_sem, p_eeg_gradient

    # 计算 iMAD 自适应阈值
    adaptive_threshold = _compute_adaptive_threshold(turn_index, len(beta_clean), d_sem_history)

    if use_mock_eeg:
        # iMAD 半自适应条件：需要同时满足语义相似度 + 注意力下降 + 非早期轮次
        # 早期轮次（turn_index < 2）更宽容，允许一定程度的相似探索
        trigger_conditions = [
            turn_index >= 2,  # 避免早期轮次误杀
            d_sem > adaptive_threshold,
            p_eeg_gradient < EEG_ATTENTION_DROP_THRESHOLD
        ]

        if all(trigger_conditions):
            return True, (
                f"[iMAD Turn {turn_index}] High similarity ({d_sem:.3f} > {adaptive_threshold:.3f}) "
                f"+ Attention drop ({p_eeg_gradient:.1f}). Lazy agreement detected."
            ), d_sem, p_eeg_gradient
    else:
        # 降级模式：仅依赖自适应相似度阈值，但考虑轮次因素
        # 早期轮次（前2轮）更宽容
        early_turn_factor = 0.05 if turn_index < 2 else 0.0
        early_threshold = adaptive_threshold + early_turn_factor

        if d_sem > early_threshold:
            return True, (
                f"High semantic similarity ({d_sem:.3f} > {early_threshold:.3f}). "
                f"Forced critical thinking (iMAD adaptive threshold)."
            ), d_sem, p_eeg_gradient

    # 极端相似度兜底（不受自适应阈值限制，但考虑轮次）
    extreme_threshold = 0.92 if turn_index >= 2 else 0.95  # 早期轮次更严格
    if d_sem > extreme_threshold:
        return True, f"Extreme semantic similarity detected ({d_sem:.3f} > {extreme_threshold:.3f}).", d_sem, p_eeg_gradient

    return False, "Quality OK.", d_sem, p_eeg_gradient
