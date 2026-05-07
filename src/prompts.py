"""
prompts.py
便捷调用入口 + 批量处理函数。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Optional

from .BraggingResponseAgent import BraggingResponseAgent, AgentInput, AgentOutput

logger = logging.getLogger(__name__)

# 模块级单例（懒初始化，首次调用时创建）
_agent: BraggingResponseAgent | None = None


def _get_agent() -> BraggingResponseAgent:
    global _agent
    if _agent is None:
        _agent = BraggingResponseAgent()
    return _agent


def run_bragging_agent(
    speaker_post: str,
    episode_id: str = "manual_test",
    platform: str = "微信朋友圈",
    relationship: str = "普通朋友",
    agent_role: str = "旁观者",
    interaction_goal: str = "维持友好关系",
    *,
    agent: Optional[BraggingResponseAgent] = None,
) -> AgentOutput:
    """
    单条凡尔赛言论的便捷调用函数。

    Args:
        speaker_post:     凡尔赛原文
        episode_id:       用于日志追踪（对应数据集 episode_id 字段）
        platform:         社交平台（微信朋友圈 / 微博 / 职场群 / 私聊）
        relationship:     与对方的关系（普通朋友 / 职场同事 / 闺蜜 / 网友）
        agent_role:       回应方角色（旁观者 / 朋友 / 同事）
        interaction_goal: 互动目标（维持友好关系 / 委婉拒绝 / 表达共鸣）
        agent:            可传入自定义 Agent 实例（测试时复用）

    Returns:
        AgentOutput dataclass，包含完整分析结果和回应文本
    """
    runner = agent or _get_agent()
    inp = AgentInput(
        episode_id=episode_id,
        speaker_post=speaker_post,
        platform=platform,
        relationship=relationship,
        agent_role=agent_role,
        interaction_goal=interaction_goal,
    )
    return runner.run(inp)


def run_batch(
    episodes: list[dict],
    *,
    agent: Optional[BraggingResponseAgent] = None,
    fail_fast: bool = False,
) -> list[dict]:
    """
    批量处理数据集中的多条 episode。

    Args:
        episodes:   每条是包含 episode_id + speaker_post（及可选上下文字段）的 dict
        agent:      可传入自定义 Agent 实例
        fail_fast:  True 时遇错立即抛出，False 时记录错误并继续

    Returns:
        包含 AgentOutput 字段的 dict 列表
    """
    runner = agent or _get_agent()
    results: list[dict] = []

    for ep in episodes:
        eid = ep.get("episode_id", "unknown")
        try:
            out = run_bragging_agent(
                speaker_post=ep["speaker_post"],
                episode_id=eid,
                platform=ep.get("platform", "微信朋友圈"),
                relationship=ep.get("relationship", "普通朋友"),
                agent_role=ep.get("agent_role", "旁观者"),
                interaction_goal=ep.get("interaction_goal", "维持友好关系"),
                agent=runner,
            )
            results.append(asdict(out))
            logger.info("[episode=%s] ✓ strategy=%s", eid, out.response_strategy)
        except Exception as e:
            logger.error("[episode=%s] ✗ 失败: %s", eid, e)
            if fail_fast:
                raise
            results.append({"episode_id": eid, "error": str(e)})

    return results
