"""验证 JSON 提取逻辑的简单烟雾测试。"""
import sys
sys.path.insert(0, ".")

from src.BraggingResponseAgent import _extract_json, _validate_output

MOCK = (
    "好的，这是分析：\n"
    "```json\n"
    '{"bragging_mechanism": "Understated_Flex", "speaker_intention": "test", '
    '"desired_feedback": "test", "risk_assessment": "test", '
    '"response_strategy": "Curious_Inquiry", "response_text": "太可以了！"}\n'
    "```\n"
)

data = _extract_json(MOCK)
_validate_output(data)
print("✅ JSON 提取 & 校验逻辑正常")
print(f"   response_strategy = {data['response_strategy']}")
print(f"   response_text      = {data['response_text']}")
