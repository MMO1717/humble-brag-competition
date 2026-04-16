"""
curator.py
Curator (Agent Gamma) 的核心决策逻辑：
  - check_lazy_agreement: 防懒惰校验 (Level 1 关键词规则)
  - dynamic_edge_pruning: 调用 Gamma Agent 进行动态剪枝决策
"""

import json
import re
from google import genai
from google.genai import types
from agents import get_agent_config

# ============================================================
# 懒惰判定：关键词规则 (Level 1)
# ============================================================
# 命中以下任意规则，即判定为"虚假共识 / 懒惰回复"
_LAZY_KEYWORDS = [
    "我同意", "同意", "我赞同", "赞同", "说得对", "没错",
    "正确", "完全正确", "非常正确", "你说得对", "LGTM",
    "i agree", "correct", "exactly", "agreed", "well said"
]
# Beta 回复字数低于此阈值且命中关键词，则判定为懒惰（以字符计）
_LAZY_LENGTH_THRESHOLD = 80


def check_lazy_agreement(response_alpha: str, response_beta: str) -> bool:
    """
    Level 1 防懒惰校验（关键词规则）。
    逻辑：Beta 回复过短 AND 包含附和关键词 → 判定为懒惰。
    Args:
        response_alpha: Alpha 的完整回复文本
        response_beta:  Beta 的完整回复文本
    Returns:
        True  表示检测到懒惰/虚假共识，需要 Curator 强制干预
        False 表示质量合格
    """
    beta_lower = response_beta.lower()
    is_short = len(response_beta.strip()) < _LAZY_LENGTH_THRESHOLD
    has_lazy_keyword = any(kw in beta_lower for kw in _LAZY_KEYWORDS)

    if is_short and has_lazy_keyword:
        return True

    # 附加检测：如果 Beta 回复中没有出现 <Rationale> 标签，视为格式不合规（懒惰）
    if "<Rationale>" not in response_beta and "<rationale>" not in beta_lower:
        # 短回复且无 Rationale 标签：直接判定懒惰
        if is_short:
            return True

    return False


def parse_curator_signal(raw: str) -> dict:
    """
    解析 Gamma 输出的 JSON 决策信号，带 fallback 保护。
    """
    try:
        # 优先直接解析
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        # Fallback：用正则从文本中提取 JSON 块
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    # 兜底：返回 CONTINUE，避免系统崩溃
    return {
        "status": "CONTINUE",
        "reason": "Curator output could not be parsed, defaulting to CONTINUE.",
        "consensus_score": 0.5
    }


async def dynamic_edge_pruning(client: genai.Client, model_id: str,
                               task: str,
                               response_alpha: str,
                               response_beta: str) -> dict:
    """
    调用 Gamma Agent 评估当前对话质量，返回决策信号。
    Args:
        client:         genai.Client 实例
        model_id:       使用的 Gemini 模型 ID
        task:           原始任务描述
        response_alpha: Alpha 本轮回复
        response_beta:  Beta 本轮回复
    Returns:
        dict: {"status": ..., "reason": ..., "consensus_score": ...}
    """
    gamma_config = get_agent_config("Gamma")

    # 构建 Curator 的输入：完整的对话快照
    curator_input = f"""[TASK]: {task}

[Agent Alpha's Response]:
{response_alpha}

[Agent Beta's Response]:
{response_beta}

Please evaluate the above exchange and output your decision signal in JSON format only."""

    contents = [
        types.Content(role="user", parts=[types.Part(text=curator_input)])
    ]

    response = await client.aio.models.generate_content(
        model=model_id,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=gamma_config["system_prompt"],
            temperature=0.2,        # 低温度，保证 Curator 决策稳定
            response_mime_type="application/json",
        )
    )

    raw_output = response.text
    signal = parse_curator_signal(raw_output)
    return signal, response.usage_metadata
