"""
evaluator.py
多维度奖励评分函数测算模块（FORGE 进化框架理论集成）。
计算后续指导 MASS 的标量响应参数 R。

基于 FORGE 理论实现难度感知奖励函数：
1. 动态 α 参数：高难题答对奖励更高
2. 动态 δ 参数：高难题的大量 Token 惩罚弱化
3. 难度系数 diff_factor ∈ [1.0, 2.0]
"""

import math

def _estimate_difficulty(prompt_text: str) -> float:
    """
    基于逻辑分支词和长度估算任务难度系数 [1.0, 2.0]。
    """
    import re
    # 增加逻辑联结项的权重
    logic_words = len(re.findall(r'\b(if|then|else|xor|knave|knight|spy|knight-knave|statement|truth)\b', prompt_text, re.IGNORECASE))
    logic_factor = min(1.0, logic_words * 0.15)
    length_factor = min(1.0, len(prompt_text) / 1000.0)
    
    return 1.0 + (logic_factor * 0.7) + (length_factor * 0.3)


def compute_physio_reward(
    is_correct: bool,
    interventions: int,
    turns_used: int,
    d_sem_avg: float,
    p_eeg_avg: float,
    total_tokens: int,
    prompt_text: str = ""
) -> float:
    """
    FORGE 奖励函数：回归以准确率为核心的评分逻辑。
    """
    diff_factor = _estimate_difficulty(prompt_text)

    # 强化 Acc 权重，弱化 Token 惩罚（因为控制器已拦截，不再会出现 2w+ 的极端情况）
    BASE_ALPHA = 120.0  # 提高 Acc 基础分
    BASE_DELTA = 0.004  # 降低 Token 基础惩罚项力度

    ALPHA = BASE_ALPHA * (diff_factor ** 1.5)
    DELTA = BASE_DELTA / diff_factor

    BETA  = 10.0
    GAMMA = 0.0
    acc_score = 1.0 if is_correct else 0.0
    e_eff = (interventions * 0.5) + max(0, (5 - turns_used) * 0.2)
    physio_score = 1.0 / (1.0 + math.exp(-p_eeg_avg))
    token_penalty = total_tokens * DELTA

    R = (ALPHA * acc_score) + (BETA * e_eff) + (GAMMA * physio_score) - token_penalty

    # 输出调试信息（可选）
    print(f"[FORGE Reward] diff_factor={diff_factor:.2f}, α={ALPHA:.1f}, δ={DELTA:.6f}, tokens={total_tokens}, penalty={token_penalty:.1f}")

    return float(R)

def evaluate_ground_truth(final_response: str, expected_solution: str) -> bool:
    """
    KKS 逻辑题判别：通过抽取 solution 中的关键身份映射（如 A is a knight）判断其在最终响应中是否闭环匹配。
    """
    msg = final_response.lower()
    sol_lower = expected_solution.lower()
    
    # 抽取 "a is a knight" 这种核心声明片段
    import re
    # 假设 KKS 大多是 "X is a knight/knave/spy"
    matches = re.finditer(r'([a-z]+) is a (knight|knave|spy)', sol_lower)
    expected_statements = [m.group(0) for m in matches]
    
    if not expected_statements:
        # 如果不是标准声明格式，转为全文关键词容错比对
        # 简单回退：检查 expected 的几个唯一核心词是否都在回复中
        core_kws = [w for w in set(re.findall(r'\b[a-z]+\b', sol_lower)) if w in ['knight', 'knave', 'spy', 'a', 'b', 'c', 'd']]
        if not core_kws:
            return expected_solution.strip().lower() in msg
        for kw in core_kws:
            if kw not in msg:
                 return False
        return True
        
    for statement in expected_statements:
        # e.g., 'a is a knight'
        # 我们寻找等效语义，或者强匹配
        if statement not in msg:
            # 放宽一下：有时模型会说 'a is the knight'
            relaxed = statement.replace("a knight", "knight").replace("a knave", "knave").replace("a spy", "spy")
            if relaxed not in msg:
                return False
    return True
