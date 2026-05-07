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

# bragging_mechanism 现在是自然语言描述（不再是枚举）。
# 以下黑名单用于检测模型是否仍输出了旧枚举标签，若命中则触发重试。
MECHANISM_BLACKLIST = {
    "Humble_Brag", "Understated_Flex", "Burden_of_Excess",
    "Reluctant_Reveal", "Comparative_Drop", "Proxy_Validation",
    "The Humble Brag", "The Professional Showcase",
    "The Understated Flex", "The Enthusiastic Share",
    "Soft_Landing", "Gravitational_Field", "Information_Leakage",
}


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
