from __future__ import annotations

import json
from typing import Any


MECHANISM_DEFINITIONS = """
Choose exactly one bragging mechanism:
- humble_complaint: complaint-like wording that highlights an advantage through inconvenience, burden, fatigue, notifications, or difficulty.
- faux_modesty: explicit modesty, self-deprecation, or disclaimer that draws attention to success. Use it only when the modesty cue is obvious.
- achievement_drop: casually mentioning an achievement, status, opportunity, or named accomplishment.
- comparison_superiority: implying being better, faster, smarter, more skilled, or more efficient than others.
- scarcity_flex: highlighting rare access, privilege, or limited opportunity.
- understated_flex: low-key framing of a positive outcome or ability without explicit modesty. Prefer this over faux_modesty when the speaker is simply understated.
- self_aware_brag: openly joking about bragging or flexing, e.g. "not to brag", "don't mean to brag", "humblebrag", or "flex".
- other: edge case that does not fit the above.

Tie-breakers:
- Do not overuse faux_modesty. If there is no clear modesty/disclaimer cue, choose understated_flex or achievement_drop.
- If the post says "not to brag" or "don't mean to brag", choose self_aware_brag.
- If the post turns a complaint into proof of status or ability, choose humble_complaint.

Examples:
Post: "I do not mean to brag, but my quick draft became the team template."
Label: self_aware_brag
Post: "I only followed my usual process, but the result landed ahead of schedule."
Label: understated_flex
Post: "Most people needed a long process, but I solved it in one pass."
Label: comparison_superiority
""".strip()


def _row_context(row: dict[str, Any]) -> str:
    keys = [
        "speaker_post",
        "platform",
        "relationship",
        "agent_role",
        "interaction_goal",
    ]
    return json.dumps({key: row.get(key, "") for key in keys}, ensure_ascii=False)


def mechanism_classifier_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You classify subtle bragging mechanisms. Return only one label. "
                "Do not return JSON, markdown, explanations, or extra text."
            ),
        },
        {
            "role": "user",
            "content": f"{MECHANISM_DEFINITIONS}\n\nInput:\n{_row_context(row)}",
        },
    ]


def understanding_messages(row: dict[str, Any], mechanism: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Infer concise social-understanding fields for a BRAG-Agent row. "
                "Return a compact JSON object only. Do not include hidden reasoning."
            ),
        },
        {
            "role": "user",
            "content": (
                "Input:\n"
                f"{_row_context(row)}\n\n"
                f"Normalized bragging_mechanism: {mechanism}\n\n"
                "Risk guidance:\n"
                "- Name only one or two likely risks, not every possible risk.\n"
                "- Most cases should mention misrecognition, and formal/public contexts may add context insensitivity.\n"
                "- Mention sycophancy only when the interaction goal or context clearly warns against overpraise.\n"
                "- Mention preachiness only when moralizing or lecturing is a concrete risk.\n"
                "- Mention strategy inconsistency only when the reply could easily mismatch the chosen social goal.\n"
                "- Mention over-coldness only when a terse response would likely feel dismissive.\n\n"
                "Return exactly this JSON shape:\n"
                "{"
                '"speaker_intention":"one concise English sentence",'
                '"desired_feedback":"one concise English sentence",'
                '"risk_assessment":"one concise English sentence naming only the most likely risk keywords"'
                "}"
            ),
        },
    ]


def response_messages(
    row: dict[str, Any],
    mechanism: str,
    understanding: dict[str, Any],
    strategy: str,
) -> list[dict[str, str]]:
    response_rules = """
Write one short natural English reply to the speaker.
Do not expose labels, JSON, analysis, or policy language.
Do not say "the speaker is bragging" or otherwise call out bragging.
Avoid excessive praise, moralizing, and cold dismissal.
Match the chosen response_strategy.
Use one concrete detail from the post when possible.
Avoid generic replies such as "That's cool", "Keep it up", "Well done", or "pretty impressive".
If response_strategy is ask_followup, ask exactly one grounded question.
If response_strategy is humor_tease, keep it light and friendly, not mean.
If response_strategy is neutral_observation, make a restrained observation without praise.
If response_strategy is validate, acknowledge the feeling or effort without exaggerating.
For workplace, academic, public, or neutral settings, stay restrained.
""".strip()
    payload = {
        "input": {
            "speaker_post": row.get("speaker_post", ""),
            "platform": row.get("platform", ""),
            "relationship": row.get("relationship", ""),
            "agent_role": row.get("agent_role", ""),
            "interaction_goal": row.get("interaction_goal", ""),
        },
        "bragging_mechanism": mechanism,
        "understanding": understanding,
        "response_strategy": strategy,
    }
    return [
        {
            "role": "system",
            "content": (
                "You write socially appropriate short replies. Return only the reply text."
            ),
        },
        {
            "role": "user",
            "content": f"{response_rules}\n\nContext:\n{json.dumps(payload, ensure_ascii=False)}",
        },
    ]
