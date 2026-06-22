from __future__ import annotations

import json
from typing import Any

from .memory import format_memory_snippets


THINKING_MODEL_SUFFIX = {
    "mechanism": (
        "\n\nOutput requirements:\n"
        "- Return ONLY the JSON object.\n"
        "- Do NOT explain your reasoning.\n"
        "- Do NOT use bullet points or analysis.\n"
        "- Do NOT include any text before or after the JSON.\n"
        "- The output must start with { and end with }."
    ),
    "mechanism_review": (
        "\n\nOutput requirements:\n"
        "- Return ONLY the JSON object.\n"
        "- Do NOT explain your reasoning.\n"
        "- The output must start with { and end with }."
    ),
    "understanding": (
        "\n\nOutput requirements:\n"
        "- Return ONLY the JSON object.\n"
        "- Do NOT explain your reasoning.\n"
        "- Do NOT use bullet points or analysis.\n"
        "- The output must start with { and end with }."
    ),
    "response": (
        "\n\nOutput requirements:\n"
        "- Return ONLY the reply text.\n"
        "- Do NOT explain, analyze, or reason.\n"
        "- Do NOT mention strategy, mechanism, or labels.\n"
        "- Maximum 25 words.\n"
        "- One or two sentences only."
    ),
}


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
- A comparison counts only when it elevates the speaker or their ability over other people. Comparing two unrelated things is not comparison_superiority.
- A direct, concrete announcement is achievement_drop; an incidental discovery or side comment is understated_flex.
- Gratitude alone is not faux_modesty. It needs apology, self-downplaying, or a contrast that packages self-promotion as modesty.
- A story about ability, identity, connections, possessions, or third-party reactions is usually understated_flex unless it names a completed achievement.

Balanced examples:
- "I somehow became the person everyone asks for spreadsheet help." -> understated_flex
- "I was promoted to team lead today." -> achievement_drop
- "I'm no expert, but my draft became the department template." -> faux_modesty
- "I hate that winning keeps adding more interviews to my calendar." -> humble_complaint
- "Only twelve people received access to the private preview." -> scarcity_flex
- "Most people needed three attempts; I finished in one." -> comparison_superiority
- "Tiny brag: I finally solved it." -> self_aware_brag
- "The meeting starts at nine tomorrow." -> other
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
        elif task == "strategy":
            lines.append(f"bragging_mechanism: {example.get('bragging_mechanism', '')}")
            lines.append(f"response_strategy: {example.get('response_strategy', '')}")
        elif task == "response":
            lines.append(f"bragging_mechanism: {example.get('bragging_mechanism', '')}")
            lines.append(f"response_strategy: {example.get('response_strategy', '')}")
            lines.append(f"response_text: {example.get('response_text', '')}")
        lines.append("")
    return "\n".join(lines).strip()


def format_memory_by_type(
    memories: list[dict[str, Any]],
    max_chars: int = 2400,
) -> str:
    if not memories:
        return ""
    groups: dict[str, list[dict[str, Any]]] = {}
    for memory in memories:
        memory_type = str(memory.get("memory_type") or "memory")
        groups.setdefault(memory_type, []).append(memory)

    parts: list[str] = []
    used = 0
    for memory_type, items in groups.items():
        block = f"### {memory_type}\n{format_memory_snippets(items, max_chars=max_chars)}"
        if parts and used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


def _format_mechanism_knowledge(
    memories: list[dict[str, Any]],
    max_chars: int = 6000,
) -> str:
    """将机制卡和混淆卡压缩成稳定的分类知识。"""
    lines: list[str] = []
    for memory in memories:
        labels = "/".join(memory.get("target_labels", []))
        content = " ".join(str(memory.get("content", "")).split())[:420]
        line = f"- {memory.get('memory_id')} [{labels}]: {content}"
        if lines and len("\n".join(lines + [line])) > max_chars:
            break
        lines.append(line)
    return "\n".join(lines)


def build_mechanism_prompt(
    row: dict[str, Any],
    mechanism_knowledge: list[dict[str, Any]] | None = None,
    *,
    thinking_model: bool = False,
) -> list[dict[str, str]]:
    memory_text = _format_mechanism_knowledge(mechanism_knowledge or [])
    user_parts = [MECHANISM_DEFINITIONS]
    if memory_text:
        user_parts.append(f"Mechanism knowledge:\n{memory_text}")
    user_parts.append(
        "Return exactly one compact JSON object with this shape:\n"
        '{"label":"one valid label","runner_up":"one different valid label",'
        '"confidence":"high|medium|low","cue_codes":["short_code"]}'
    )
    user_parts.append(
        "Input:\n"
        + json.dumps(
            {"speaker_post": row.get("speaker_post", "")},
            ensure_ascii=False,
        )
    )
    if thinking_model:
        user_parts.append(THINKING_MODEL_SUFFIX["mechanism"])
    return [
        {
            "role": "system",
            "content": (
                "You classify subtle bragging mechanisms from speaker_post only. "
                "Return compact JSON only. Do not use platform, relationship, role, "
                "or response goal to change the mechanism."
            ),
        },
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def build_mechanism_review_prompt(
    row: dict[str, Any],
    candidate_a: str,
    candidate_b: str,
    trigger_evidence: list[str],
    *,
    thinking_model: bool = False,
) -> list[dict[str, str]]:
    """构造只比较两个候选标签的短复核提示。"""
    payload = {
        "speaker_post": row.get("speaker_post", ""),
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
        "trigger_evidence": trigger_evidence,
    }
    user_content = (
        "Choose the better candidate. A concrete completed event favors "
        "achievement_drop; an incidental ability, identity, connection, "
        "possession, or third-party reaction favors understated_flex. "
        "A complaint carrying the positive status favors humble_complaint. "
        "Apology or self-downplaying that packages a positive claim favors "
        "faux_modesty. Comparison must elevate the speaker or an associated "
        "person over others.\n\n"
        "Return exactly:\n"
        f'{{"label":"{candidate_a} or {candidate_b}",'
        f'"runner_up":"the other label",'
        '"confidence":"high|medium|low","cue_codes":["short_code"]}\n\n'
        f"Input:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    if thinking_model:
        user_content += THINKING_MODEL_SUFFIX["mechanism_review"]
    return [
        {
            "role": "system",
            "content": (
                "Review a subtle bragging mechanism classification. Compare only "
                "the two supplied labels using the speaker_post. Return compact JSON only."
            ),
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]

def build_understanding_prompt(
    row: dict[str, Any],
    mechanism: str,
    memory_snippets: list[dict[str, Any]] | None = None,
    *,
    thinking_model: bool = False,
) -> list[dict[str, str]]:
    memory_text = format_memory_by_type(memory_snippets or [], 1200)
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
    if thinking_model:
        user_parts.append(THINKING_MODEL_SUFFIX["understanding"])
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
    fewshot_examples: list[dict[str, Any]],
    memory_snippets: list[dict[str, Any]] | None = None,
    *,
    thinking_model: bool = False,
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
    memory_text = format_memory_by_type(memory_snippets or [], 2400)
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
        "risk_control_plan": state.get("risk_control_plan", {}),
        "response_strategy": state.get("response_strategy", ""),
    }

    user_parts = [response_rules]
    if memory_text:
        user_parts.append(f"Relevant memory:\n{memory_text}")
    if fewshot_text:
        user_parts.append(f"Few-shot examples:\n{fewshot_text}")
    user_parts.append(f"Context:\n{json.dumps(payload, ensure_ascii=False)}")
    if thinking_model:
        user_parts.append(THINKING_MODEL_SUFFIX["response"])
    return [
        {
            "role": "system",
            "content": "You write socially appropriate short replies. Return only the reply text.",
        },
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]
