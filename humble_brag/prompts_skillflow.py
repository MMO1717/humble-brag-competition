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
- If the speaker says a result is "especially impressive" because conditions were harder, choose understated_flex unless they directly rank themselves above other people.
- If the post uses a formula like "True X skill is..." to define the speaker's behavior as superior skill, choose comparison_superiority.

Calibration examples:
Post: "The screen version is slower, so my score is especially impressive."
Label: understated_flex
Post: "True gaming skill is finishing one mission while already playing another game."
Label: comparison_superiority
Post: "I do not mean to brag, but I finished it early."
Label: self_aware_brag
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


def format_memory_snippets(snippets: list[dict[str, Any]]) -> str:
    if not snippets:
        return ""
    lines: list[str] = []
    for i, item in enumerate(snippets, start=1):
        text = item.get("text") or item.get("content") or item.get("rule") or ""
        if text:
            lines.append(f"{i}. {text}")
    return "\n".join(lines)


def format_fewshot_examples(
    examples: list[dict[str, Any]],
    task: str,
    include_fields: bool = True,
) -> str:
    if not examples:
        return ""

    lines: list[str] = []
    for index, example in enumerate(examples, start=1):
        input_payload = {"speaker_post": example.get("speaker_post", "")}
        if include_fields:
            for key in ("platform", "relationship", "agent_role", "interaction_goal"):
                if key in example:
                    input_payload[key] = example.get(key, "")

        lines.append(f"Example {index}:")
        lines.append(f"Input: {json.dumps(input_payload, ensure_ascii=False)}")
        if task == "mechanism":
            lines.append(f"bragging_mechanism: {example.get('bragging_mechanism', '')}")
        elif task == "response":
            lines.append(f"bragging_mechanism: {example.get('bragging_mechanism', '')}")
            lines.append(f"response_strategy: {example.get('response_strategy', '')}")
            lines.append(f"response_text: {example.get('response_text', '')}")
        lines.append("")
    return "\n".join(lines).strip()


def build_mechanism_prompt(
    row: dict[str, Any],
    wiki: dict[str, str],
    fewshot_examples: list[dict[str, Any]],
    memory_snippets: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    fewshot_text = format_fewshot_examples(fewshot_examples, "mechanism")
    memory_text = format_memory_snippets(memory_snippets or [])
    user_parts = [MECHANISM_DEFINITIONS]
    if memory_text:
        user_parts.append(f"Relevant memory:\n{memory_text}")
    if fewshot_text:
        user_parts.append(f"Few-shot examples:\n{fewshot_text}")
    user_parts.append(f"Input:\n{_row_context(row)}")
    return [
        {
            "role": "system",
            "content": (
                "You classify subtle bragging mechanisms. Return only one label. "
                "Do not return JSON, markdown, explanations, or extra text."
            ),
        },
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def build_understanding_prompt(
    row: dict[str, Any],
    mechanism: str,
    wiki: dict[str, str],
    memory_snippets: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    memory_text = format_memory_snippets(memory_snippets or [])
    user_parts = [
        "Infer concise social-understanding fields for this BRAG-Agent row.",
        f"Input:\n{_row_context(row)}",
        f"Normalized bragging_mechanism: {mechanism}",
    ]
    if memory_text:
        user_parts.append(f"Relevant memory:\n{memory_text}")
    user_parts.append(
        "Return exactly this compact JSON shape and nothing else:\n"
        '{"speaker_intention":"one concise English sentence",'
        '"desired_feedback":"one concise English sentence"}'
    )
    return [
        {
            "role": "system",
            "content": (
                "You infer concise social understanding. Return a compact JSON object only. "
                "Do not include hidden reasoning."
            ),
        },
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def build_response_prompt(
    row: dict[str, Any],
    state: dict[str, Any],
    wiki: dict[str, str],
    fewshot_examples: list[dict[str, Any]],
    memory_snippets: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    response_rules = """
Write one short natural English reply to the speaker.
Do not expose labels, JSON, analysis, policy language, risk labels, or hidden reasoning.
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
If the post claims a score or result is more impressive because the conditions were harder, mention the condition and result in neutral terms.
If asking a follow-up about a score, ask about the benchmark, measure, or whether it accounts for the harder condition.
If the post is about gaming optimization or multitasking, a light gaming phrase such as "min-maxing" or "gamer move" can fit humor_tease.
""".strip()
    fewshot_text = format_fewshot_examples(fewshot_examples, "response")
    memory_text = format_memory_snippets(memory_snippets or [])
    payload = {
        "input": {
            "speaker_post": row.get("speaker_post", ""),
            "platform": row.get("platform", ""),
            "relationship": row.get("relationship", ""),
            "agent_role": row.get("agent_role", ""),
            "interaction_goal": row.get("interaction_goal", ""),
        },
        "bragging_mechanism": state.get("bragging_mechanism", ""),
        "speaker_intention": state.get("speaker_intention", ""),
        "desired_feedback": state.get("desired_feedback", ""),
        "risk_guidance": state.get("risk_assessment", ""),
        "response_strategy": state.get("response_strategy", ""),
    }

    user_parts = [response_rules]
    if memory_text:
        user_parts.append(f"Relevant memory:\n{memory_text}")
    if fewshot_text:
        user_parts.append(f"Few-shot examples:\n{fewshot_text}")
    user_parts.append(f"Context:\n{json.dumps(payload, ensure_ascii=False)}")
    return [
        {
            "role": "system",
            "content": "You write socially appropriate short replies. Return only the reply text.",
        },
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]
