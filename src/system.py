"""
system.py
组装完整 System Prompt 的入口函数。
"""

from .system_prompt_sections import (
    ROLE_AND_OBJECTIVE,
    BRAGGING_MECHANISM_TAXONOMY,
    RESPONSE_STRATEGIES,
    NEGATIVE_CONSTRAINTS,
    FEW_SHOT_EXAMPLES,
    OUTPUT_FORMAT,
)

# 比赛官方 response_strategy 枚举（8种，全小写）
VALID_STRATEGIES = {
    "validate",
    "light_acknowledgment",
    "ask_followup",
    "humor_tease",
    "redirect",
    "neutral_observation",
    "set_boundary",
    "no_response",
}

# BRAG-Agent v6 官方 bragging_mechanism 枚举（8种）
VALID_MECHANISMS = {
    "humble_complaint",
    "faux_modesty",
    "achievement_drop",
    "comparison_superiority",
    "scarcity_flex",
    "understated_flex",
    "self_aware_brag",
    "other",
}

# 已废弃：旧版自然语言描述黑名单，保留仅作向后兼容参考
MECHANISM_BLACKLIST: set[str] = set()


def build_system_prompt() -> str:
    """
    组装完整的 System Prompt。
    各模块顺序：角色 → 机制分类 → 策略 → 约束 → Few-shot → 输出格式。
    输出格式放最后，确保 Qwen 在长上下文中对格式要求的注意力最强。
    """
    sections = [
        ROLE_AND_OBJECTIVE,
        BRAGGING_MECHANISM_TAXONOMY,
        RESPONSE_STRATEGIES,
        NEGATIVE_CONSTRAINTS,
        FEW_SHOT_EXAMPLES,
        OUTPUT_FORMAT,
    ]
    return "\n\n".join(sections)


def build_user_prompt(
    speaker_post: str,
    platform: str = "微信朋友圈",
    relationship: str = "普通朋友",
    agent_role: str = "旁观者",
    interaction_goal: str = "维持友好关系",
) -> str:
    """
    构造 User Prompt，将场景上下文结构化注入。
    """
    return f"""请对以下凡尔赛言论进行分析并生成最佳回应：

<input>
  <platform>{platform}</platform>
  <relationship>{relationship}</relationship>
  <agent_role>{agent_role}</agent_role>
  <interaction_goal>{interaction_goal}</interaction_goal>
  <statement>{speaker_post}</statement>
</input>""".strip()
