from __future__ import annotations

import json
import re
from typing import Any, Dict


def extract_and_parse_json(text: str) -> Dict[str, Any]:
    """从模型输出文本中提取并解析首个 JSON 对象字典，若彻底失败则抛出异常"""
    cleaned = text.strip()

    # 1. 尝试匹配 ```json ... ``` 块或 ``` ... ``` 块
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if code_block_match:
        cleaned = code_block_match.group(1).strip()

    # 2. 如果直接 json.loads 成功则直接返回
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 3. 定位文本中的首个 '{' 和最后一个 '}'
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 4. 做基础的 JSON 格式修复（去除末尾多余逗号）
        candidate_fixed = re.sub(r",\s*\}", "}", candidate)
        candidate_fixed = re.sub(r",\s*\]", "]", candidate_fixed)
        try:
            parsed = json.loads(candidate_fixed)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract or parse a valid JSON dictionary from model response.")
