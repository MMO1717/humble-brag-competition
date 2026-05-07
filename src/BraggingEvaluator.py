"""
BraggingEvaluator.py
利用 LLM-as-Judge 进行自我评估。
提供 4 个维度的 1-10 评分及建议。
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

EVALUATOR_PROMPT = """
你是一个客观、严格、专业的社交互动分析评委。我们需要你评估一个 AI Agent 生成的针对“凡尔赛”（低调炫耀）言论的回应质量。

请根据以下 4 个维度给 Agent 的表现打分（每项 1-10 分），并附上一句话理由。

【评估维度】
1. 状态理解质量 (State Understanding):
   - Agent 输出的 bragging_mechanism（炫耀机制分析）和 speaker_intention（意图分析）是否准确、深刻？是否看破了发帖人的“弦外之音”？
2. 策略选择合理性 (Strategy Reasonableness):
   - Agent 选择的 response_strategy 是否适合当前的发言上下文？是否规避了 risk_assessment 中提到的坑？
3. 回复自然度与真实性 (Naturalness & Authenticity):
   - response_text 是否自然口语化？也就是看起来像真人说的，不生硬、不爹味、“不油腻”。
4. 策略与内容一致性 (Strategy-Content Alignment):
   - 生成的 response_text 是否切实贯彻了其所选的策略要求？（例如选择了 humor_tease，真的有幽默感吗？）

【输入信息格式】
[原文]：发帖人的凡尔赛原文。
[Agent 输出]：包含 mechanism, intention, feedback, risk, strategy, text的完整分析过程。

【输出格式】
严格输出 JSON 格式（包含在 ```json 块中），字段如下：
```json
{
  "understanding_score": 1-10,
  "understanding_reason": "简评",
  "strategy_score": 1-10,
  "strategy_reason": "简评",
  "naturalness_score": 1-10,
  "naturalness_reason": "简评",
  "alignment_score": 1-10,
  "alignment_reason": "简评",
  "overall_comment": "总体一句话评价"
}
```
"""

@dataclass
class EvaluationResult:
    understanding_score: int
    understanding_reason: str
    strategy_score: int
    strategy_reason: str
    naturalness_score: int
    naturalness_reason: str
    alignment_score: int
    alignment_reason: str
    overall_comment: str

    @property
    def average_score(self) -> float:
        return (self.understanding_score + self.strategy_score + self.naturalness_score + self.alignment_score) / 4.0


class BraggingEvaluator:
    def __init__(self, model: str = "qwen-max"):
        self.model = os.getenv("EVALUATOR_MODEL", model) # 默认尝试用高推理能力的 qwen-max
        api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def aevaluate(self, original_post: str, agent_output: dict) -> EvaluationResult:
        user_content = f"""
[原文]：
{original_post}

[Agent 输出]：
{json.dumps(agent_output, ensure_ascii=False, indent=2)}
"""
        messages = [
            {"role": "system", "content": EVALUATOR_PROMPT},
            {"role": "user", "content": user_content}
        ]

        try:
            response = await self._async_client.chat.completions.create(
                model=self.model,
                messages=messages, # type: ignore
                temperature=0.1, # 裁判必须冷静
                max_tokens=600
            )
            raw = response.choices[0].message.content or ""
            
            # Extract JSON
            m = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.IGNORECASE | re.DOTALL)
            if m:
                payload = m.group(1)
            else:
                payload = re.search(r"\{[\s\S]*\}", raw).group(0) # type: ignore

            data = json.loads(payload)
            return EvaluationResult(
                understanding_score=int(data.get("understanding_score", 0)),
                understanding_reason=data.get("understanding_reason", ""),
                strategy_score=int(data.get("strategy_score", 0)),
                strategy_reason=data.get("strategy_reason", ""),
                naturalness_score=int(data.get("naturalness_score", 0)),
                naturalness_reason=data.get("naturalness_reason", ""),
                alignment_score=int(data.get("alignment_score", 0)),
                alignment_reason=data.get("alignment_reason", ""),
                overall_comment=data.get("overall_comment", "")
            )
        except Exception as e:
            logger.error(f"评估失败: {e}")
            return EvaluationResult(0, f"Error: {e}", 0, "", 0, "", 0, "", "")
