"""根据最终回复、策略和场景复查社交风险。"""
from __future__ import annotations
import re
from typing import Any

from ..postprocess import abstract_response_fallback, clean_response_text
from ..social_rubric import judge_row
from .base import Skill

WARM_RELATIONSHIPS = {"close_friend", "friend", "family_member", "romantic_partner"}
PROFESSIONAL_PLATFORMS = {"workplace_channel", "academic_forum"}
PUBLIC_PLATFORMS = {"public_social_media", "community_forum"}

OVERPRAISE_RE = re.compile(
    r"\b(amazing|incredible|legendary|genius|perfect|iconic|unbelievable|so proud|great job|impressive)\b",
    re.I,
)
PREACHY_RE = re.compile(
    r"\b(you should|you need to|you have to|stop (bragging|showing off)|be humble|not healthy|that's arrogant)\b",
    re.I,
)
STRONG_PRAISE_RE = re.compile(
    r"\b(congratulations|congrats|great work|wonderful|excellent|fantastic)\b", re.I,
)


class ResponseRiskReviewSkill(Skill):
    name = "ResponseRiskReviewSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        row = state["input_row"]
        response_text = str(state.get("response_text", "")).strip()
        strategy = str(state.get("response_strategy", ""))
        mechanism = str(state.get("bragging_mechanism", ""))
        platform = str(row.get("platform", ""))
        relationship = str(row.get("relationship", ""))

        warnings: list[str] = []
        rewrite_required = False

        # 检查过誉。
        if OVERPRAISE_RE.search(response_text) or STRONG_PRAISE_RE.search(response_text):
            if strategy in ("neutral_observation", "light_acknowledgment", "redirect"):
                warnings.append("overpraise: restrained strategy contains strong praise")
                rewrite_required = True

        # 检查说教。
        if PREACHY_RE.search(response_text):
            warnings.append("preachiness: moralizing language detected")
            rewrite_required = True

        # 检查回复是否真正落实所选策略。
        if strategy == "ask_followup" and "?" not in response_text:
            warnings.append("strategy_inconsistency: ask_followup without question")
            rewrite_required = True
        if strategy == "set_boundary" and not re.search(
            r"\b(but|rather|keep|not|without|prefer|focus)\b",
            response_text,
            re.I,
        ):
            warnings.append("strategy_inconsistency: set_boundary without boundary language")
            rewrite_required = True
        if strategy == "redirect" and not re.search(
            r"\b(focus|back|main|shared|next|discussion|instead|"
            r"what about|how about|what do you|what did you|what was|what's)\b",
            response_text,
            re.I,
        ):
            warnings.append("strategy_inconsistency: redirect is not explicit")
        if strategy == "no_response" and len(response_text.split()) > 8:
            warnings.append("strategy_inconsistency: no_response is not empty")
            rewrite_required = True
        if strategy == "neutral_observation" and (
            OVERPRAISE_RE.search(response_text) or STRONG_PRAISE_RE.search(response_text)
        ):
            warnings.append("strategy_inconsistency: neutral response contains strong praise")
            rewrite_required = True

        # 亲密关系中的过冷回复需要额外标记。
        if relationship in WARM_RELATIONSHIPS:
            cold_patterns = ["Ok.", "Noted.", "Sure.", "Cool.", "Interesting."]
            if any(response_text.strip().rstrip(".") == p.rstrip(".") for p in cold_patterns):
                warnings.append("over_coldness: terse response to close relationship")
                rewrite_required = True

        # 专业或公开场景不应使用过度随意、亲密的语气。
        if platform in PROFESSIONAL_PLATFORMS or platform in PUBLIC_PLATFORMS:
            if re.search(r"\b(haha|lol|bro|dude|mate)\b", response_text, re.I):
                warnings.append("context_insensitivity: casual language in professional/public context")
                rewrite_required = True
            if relationship not in WARM_RELATIONSHIPS and re.search(r"\b(love|adore|proud|miss you)\b", response_text, re.I):
                warnings.append("context_insensitivity: overly familiar language for relationship")
                rewrite_required = True

        rewritten = False
        if rewrite_required:
            candidate = clean_response_text(
                abstract_response_fallback(strategy, mechanism, row),
                strategy,
            )
            judgment = judge_row(
                input_row=row,
                output_row={
                    "response_strategy": strategy,
                    "response_text": candidate,
                },
            )
            if not judgment.get("hard_issues"):
                state["response_text"] = candidate
                state["response_risk_review_judgment"] = judgment
                rewritten = candidate != response_text
                if rewritten:
                    print(
                        f"[WARN] {state.get('episode_id', 'unknown')} 回复风险复查发现 "
                        f"{', '.join(warnings)}，已自动改写回复。",
                        flush=True,
                    )

        # 风险标签由 RiskSkill 独立决定，回复审查不得追加标签。
        state["response_risk_review_added"] = []
        state["response_risk_review_warnings"] = warnings
        state["response_risk_review_rewritten"] = rewritten
        state["risk_labels_after_response"] = list(state.get("risk_labels", []))

        return state
