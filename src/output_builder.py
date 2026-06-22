from __future__ import annotations

from typing import Any

from .postprocess import (
    clean_field_text,
    clean_response_text,
    has_valid_risk_assessment,
    render_risk_assessment,
    safe_mechanism,
    safe_strategy,
)
from .schemas import (
    DEFAULT_DESIRED_FEEDBACK,
    DEFAULT_MECHANISM,
    DEFAULT_RESPONSE_BY_STRATEGY,
    DEFAULT_RISK_ASSESSMENT,
    DEFAULT_SPEAKER_INTENTION,
    DEFAULT_STRATEGY,
    MAX_WORDS,
    OUTPUT_FIELDS,
    VALID_BRAGGING_MECHANISMS,
    VALID_RESPONSE_STRATEGIES,
)


def build_output_row(input_row: dict[str, Any], state: dict[str, Any]) -> dict[str, str]:
    """从 state 组装官方 7 字段输出，禁止透传模型生成的整行 JSON。"""
    mechanism = safe_mechanism(
        state.get("bragging_mechanism", DEFAULT_MECHANISM),
        VALID_BRAGGING_MECHANISMS,
    )
    strategy = safe_strategy(
        state.get("response_strategy", DEFAULT_STRATEGY),
        VALID_RESPONSE_STRATEGIES,
    )

    # 仅保留包含合法风险词且长度合规的 assessment。
    risk_labels = state.get("risk_labels", [])
    state_risk = state.get("risk_assessment", "")
    if has_valid_risk_assessment(state_risk):
        risk_assessment = clean_field_text(
            state_risk,
            DEFAULT_RISK_ASSESSMENT,
            MAX_WORDS["risk_assessment"],
        )
    elif risk_labels:
        risk_assessment = render_risk_assessment(set(risk_labels))
    else:
        risk_assessment = DEFAULT_RISK_ASSESSMENT

    row = {
        "episode_id": str(input_row["episode_id"]),
        "bragging_mechanism": mechanism,
        "speaker_intention": clean_field_text(
            state.get("speaker_intention"),
            DEFAULT_SPEAKER_INTENTION,
            MAX_WORDS["speaker_intention"],
        ),
        "desired_feedback": clean_field_text(
            state.get("desired_feedback"),
            DEFAULT_DESIRED_FEEDBACK,
            MAX_WORDS["desired_feedback"],
        ),
        "risk_assessment": risk_assessment,
        "response_strategy": strategy,
        "response_text": clean_response_text(state.get("response_text"), strategy),
    }
    return {field: row[field] for field in OUTPUT_FIELDS}


def build_fallback_row(input_row: dict[str, Any]) -> dict[str, str]:
    platform = input_row.get("platform")
    strategy = (
        "neutral_observation"
        if platform in {"workplace_channel", "academic_forum", "public_social_media"}
        else DEFAULT_STRATEGY
    )
    return {
        "episode_id": str(input_row["episode_id"]),
        "bragging_mechanism": DEFAULT_MECHANISM,
        "speaker_intention": DEFAULT_SPEAKER_INTENTION,
        "desired_feedback": DEFAULT_DESIRED_FEEDBACK,
        "risk_assessment": DEFAULT_RISK_ASSESSMENT,
        "response_strategy": strategy,
        "response_text": DEFAULT_RESPONSE_BY_STRATEGY[strategy],
    }
