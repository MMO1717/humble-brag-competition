"""
BraggingResponseAgent.py
凡尔赛回应 Agent 的核心 Runner / Orchestrator。
支持同步 (run) 和异步 (arun) 两种模式，具备自动解析 JSON 和重试逻辑。
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

from .system import build_system_prompt, build_user_prompt, VALID_STRATEGIES, MECHANISM_BLACKLIST

load_dotenv()

logger = logging.getLogger(__name__)


# ── 数据结构 ──────────────────────────────────────────────────────────────────

@dataclass
class AgentInput:
    episode_id: str
    speaker_post: str
    platform: str = "微信朋友圈"
    relationship: str = "普通朋友"
    agent_role: str = "旁观者"
    interaction_goal: str = "维持友好关系"


@dataclass
class AgentOutput:
    episode_id: str
    bragging_mechanism: str      # 6 种机制之一
    speaker_intention: str
    desired_feedback: str
    risk_assessment: str
    response_strategy: str       # 8 种策略之一
    response_text: str


# ── 解析工具 ──────────────────────────────────────────────────────────────────

_JSON_BLOCK_RE = re.compile(r"```json\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _extract_json(raw: str) -> dict:
    """从模型输出中提取 JSON，支持代码块匹配及宽松匹配。"""
    m = _JSON_BLOCK_RE.search(raw)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    m2 = re.search(r"\{[\s\S]*\}", raw)
    if m2:
        try:
            return json.loads(m2.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"模型输出中未找到合法 JSON:\n{raw[:300]}")


def _validate_output(data: dict) -> None:
    """校验字段合法性，并对策略名进行标准化。"""
    required = ["bragging_mechanism", "speaker_intention", "desired_feedback", "risk_assessment", "response_strategy", "response_text"]
    for field in required:
        if field not in data or not data[field]:
            raise ValueError(f"缺少必填字段: {field}")

    # 标准化策略名：转小写，下划线统一
    raw_strategy = data["response_strategy"]
    norm_strategy = str(raw_strategy).lower().replace("-", "_").replace(" ", "_").strip()
    if norm_strategy in VALID_STRATEGIES:
        data["response_strategy"] = norm_strategy
    else:
        raise ValueError(f"非法策略名: {raw_strategy}，合法值: {sorted(VALID_STRATEGIES)}")

    # bragging_mechanism 是自然语言描述，用黑名单检测是否输出了旧枚举标签
    mechanism_val = data["bragging_mechanism"]
    if mechanism_val.strip() in MECHANISM_BLACKLIST:
        raise ValueError(
            f"bragging_mechanism 输出了枚举标签 '{mechanism_val}'，"
            "请改为自然语言描述（如：用疲惫感做软着陆，将频繁飞欧洲开会这个炫耀点柔和包装）。"
        )
    if len(mechanism_val.strip()) < 10:
        raise ValueError(f"bragging_mechanism 描述过短（少于10字）: '{mechanism_val}'")


# ── Agent 主体 ────────────────────────────────────────────────────────────────

class BraggingResponseAgent:
    """凡尔赛回应 Agent，支持并发调用。"""

    MAX_RETRIES = 2
    DEFAULT_MODEL = "qwen3.6-27b"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        base_url = base_url or os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = model or os.getenv("QWEN_MODEL", self.DEFAULT_MODEL)
        
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._system_prompt = build_system_prompt()

    # ── 同步运行 ──────────────────────────────────────────────────────────────

    def run(self, inp: AgentInput) -> AgentOutput:
        user_prompt = build_user_prompt(inp.speaker_post, inp.platform, inp.relationship, inp.agent_role, inp.interaction_goal)
        messages = [{"role": "system", "content": self._system_prompt}, {"role": "user", "content": user_prompt}]
        
        raw_output = ""
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            if attempt > 0:
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({"role": "user", "content": f"上次输出错误 ({last_error})，请重新输出仅包含 JSON 的内容。"})

            try:
                response = self._client.chat.completions.create(
                    model=self.model, messages=messages, temperature=0.6, max_tokens=384
                )
                raw_output = response.choices[0].message.content or ""
                data = _extract_json(raw_output)
                _validate_output(data)

                return AgentOutput(
                    episode_id=inp.episode_id,
                    bragging_mechanism=data["bragging_mechanism"],
                    speaker_intention=data["speaker_intention"],
                    desired_feedback=data["desired_feedback"],
                    risk_assessment=data["risk_assessment"],
                    response_strategy=data["response_strategy"],
                    response_text=data["response_text"]
                )
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(f"解析失败 ({inp.episode_id}): {last_error}")

    # ── 异步运行 ──────────────────────────────────────────────────────────────

    async def arun(self, inp: AgentInput) -> AgentOutput:
        user_prompt = build_user_prompt(inp.speaker_post, inp.platform, inp.relationship, inp.agent_role, inp.interaction_goal)
        messages = [{"role": "system", "content": self._system_prompt}, {"role": "user", "content": user_prompt}]
        
        raw_output = ""
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            if attempt > 0:
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({"role": "user", "content": f"上次输出错误 ({last_error})，请重新输出仅包含 JSON 的内容。"})

            try:
                response = await self._async_client.chat.completions.create(
                    model=self.model, messages=messages, temperature=0.6, max_tokens=384
                )
                raw_output = response.choices[0].message.content or ""
                data = _extract_json(raw_output)
                _validate_output(data)

                return AgentOutput(
                    episode_id=inp.episode_id,
                    bragging_mechanism=data["bragging_mechanism"],
                    speaker_intention=data["speaker_intention"],
                    desired_feedback=data["desired_feedback"],
                    risk_assessment=data["risk_assessment"],
                    response_strategy=data["response_strategy"],
                    response_text=data["response_text"]
                )
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(f"异步解析失败 ({inp.episode_id}): {last_error}")
