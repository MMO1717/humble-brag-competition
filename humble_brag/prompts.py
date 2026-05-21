from __future__ import annotations

from typing import Any, Dict
from .contract import ALLOWED_MECHANISMS, ALLOWED_STRATEGIES
from .static_memory import STATIC_MEMORY_V1, STATIC_MEMORY_VERSION


SUPPORTED_PROMPT_VERSIONS = {
    "llm_a_minimal_v1",
    "llm_b_label_definition_v1",
    "llm_c_static_memory_v1",
}


def build_minimal_prompt_v1(row: Dict[str, Any]) -> str:
    """构建极简 zero-shot Prompt (llm_a_minimal_v1)"""
    mechanisms_str = ", ".join(sorted(list(ALLOWED_MECHANISMS)))
    strategies_str = ", ".join(sorted(list(ALLOWED_STRATEGIES)))

    prompt = f"""You are generating a valid JSON response for a humble-brag response task.

Given one social interaction, classify the bragging mechanism and choose a response strategy.

Allowed bragging_mechanism labels:
{mechanisms_str}

Allowed response_strategy labels:
{strategies_str}

Constraints:
1. Do not reveal reasoning. Do not include chain-of-thought, think block, reasoning, scratchpad or explanations.
2. Return ONLY one JSON object. No Markdown code fences, no extra text outside the JSON.
3. Word count limits for output text fields:
   - speaker_intention: maximum 80 words.
   - desired_feedback: maximum 80 words.
   - risk_assessment: maximum 100 words.
   - response_text: maximum 60 words.
4. If response_strategy is 'no_response', response_text MUST be empty.

Input:
speaker_post: {row.get('speaker_post', '')}
platform: {row.get('platform', '')}
relationship: {row.get('relationship', '')}
agent_role: {row.get('agent_role', '')}
interaction_goal: {row.get('interaction_goal', '')}

Return JSON with exactly these fields:
{{
  "bragging_mechanism": "one of the allowed bragging_mechanism labels",
  "speaker_intention": "brief description of speaker intention (max 80 words)",
  "desired_feedback": "brief description of desired feedback (max 80 words)",
  "risk_assessment": "brief description of potential response risks (max 100 words)",
  "response_strategy": "one of the allowed response_strategy labels",
  "response_text": "response text to the speaker (max 60 words, empty if no_response)"
}}"""
    return prompt


MECHANISM_DEFINITIONS = {
    "achievement_drop": "directly mentions an accomplishment, score, status, output, award, or performance.",
    "comparison_superiority": "frames the speaker as better than others or contrasts their achievement with others.",
    "faux_modesty": "uses modest or self-effacing wording while still highlighting an achievement.",
    "humble_complaint": "complains about a burden, inconvenience, or problem caused by success or high ability.",
    "scarcity_flex": "highlights rare access, exclusivity, elite opportunity, or limited availability.",
    "self_aware_brag": "explicitly signals awareness of bragging, such as 'not to brag', 'humblebrag', or 'flex'.",
    "understated_flex": "indirectly makes the speaker look impressive without a direct brag cue.",
    "other": "use only when none of the other mechanism labels fits.",
}

STRATEGY_DEFINITIONS = {
    "neutral_observation": "acknowledge the situation or context without praise, validation, or follow-up.",
    "light_acknowledgment": "brief, low-intensity acknowledgment without strong praise.",
    "ask_followup": "ask a grounded follow-up question that shifts toward substance.",
    "humor_tease": "use light playful teasing only when relationship and platform make it safe.",
    "validate": "explicitly affirm the achievement; use sparingly when validation is appropriate.",
    "redirect": "move the conversation away from the brag or toward a practical topic.",
    "set_boundary": "politely limit engagement when the brag is socially uncomfortable or inappropriate.",
    "no_response": "choose silence only when responding would likely be harmful or unnecessary.",
}

RISK_LABELS = [
    "misrecognition",
    "context_insensitivity",
    "sycophancy",
    "preachiness",
    "strategy_inconsistency",
    "over_coldness",
    "overvalidation",
    "relationship_mismatch",
    "tone_mismatch",
    "escalation_risk",
    "awkwardness",
    "dismissiveness",
]


def _format_definitions(definitions: dict[str, str]) -> str:
    return "\n".join(f"- {label}: {definitions[label]}" for label in sorted(definitions))


def build_label_definition_prompt_v1(row: Dict[str, Any]) -> str:
    """构建带标签定义和策略规则的 Prompt (llm_b_label_definition_v1)"""
    mechanisms_str = _format_definitions(MECHANISM_DEFINITIONS)
    strategies_str = _format_definitions(STRATEGY_DEFINITIONS)
    risk_labels_str = ", ".join(RISK_LABELS)

    prompt = f"""You are generating a valid JSON response for a humble-brag response task.

Given one social interaction, classify the bragging mechanism, choose a response strategy, and write a short response.

Do not reveal reasoning.
Do not include chain-of-thought, think blocks, scratchpad, hidden analysis, or explanations.
Return ONLY one JSON object. No Markdown code fences, no text outside JSON.

Allowed bragging_mechanism labels and definitions:
{mechanisms_str}

Allowed response_strategy labels and definitions:
{strategies_str}

Strategy selection rules:
- If interaction_goal is stay_neutral, prefer neutral_observation unless a warmer response is clearly required.
- If interaction_goal is avoid_sycophancy, avoid validate and avoid praise-heavy light_acknowledgment.
- If the relationship is acquaintance or the platform is direct_message, ask_followup can be safer than praise.
- If the relationship is close_friend or online_peer and the tone is playful, humor_tease can be acceptable.
- If the post creates awkwardness or the best response is to move on, use redirect.
- Do not default to light_acknowledgment for every case.
- Do not use validate unless the interaction_goal and relationship clearly support explicit affirmation.
- Do not use praise-heavy words such as impressive, amazing, great, awesome, congrats, or well done.

Risk assessment rule:
In risk_assessment, explicitly name 1-3 likely risk types from this list and briefly explain them:
{risk_labels_str}.

Constraints:
1. Output text field limits:
   - speaker_intention: maximum 80 words.
   - desired_feedback: maximum 80 words.
   - risk_assessment: maximum 100 words.
   - response_text: maximum 60 words.
2. If response_strategy is 'no_response', response_text MUST be empty.
3. Keep response_text grounded, neutral, and socially appropriate.

Input:
speaker_post: {row.get('speaker_post', '')}
platform: {row.get('platform', '')}
relationship: {row.get('relationship', '')}
agent_role: {row.get('agent_role', '')}
interaction_goal: {row.get('interaction_goal', '')}

Return JSON with exactly these fields:
{{
  "bragging_mechanism": "one of the allowed bragging_mechanism labels",
  "speaker_intention": "brief description of speaker intention (max 80 words)",
  "desired_feedback": "brief description of desired feedback (max 80 words)",
  "risk_assessment": "include 1-3 explicit risk labels from the list, with a brief explanation (max 100 words)",
  "response_strategy": "one of the allowed response_strategy labels",
  "response_text": "response text to the speaker (max 60 words, empty if no_response)"
}}"""
    return prompt


def build_static_memory_prompt_v1(row: Dict[str, Any]) -> str:
    """构建带固定任务记忆的 Prompt (llm_c_static_memory_v1)"""
    mechanisms_str = _format_definitions(MECHANISM_DEFINITIONS)
    strategies_str = _format_definitions(STRATEGY_DEFINITIONS)
    risk_labels_str = ", ".join(RISK_LABELS)

    prompt = f"""You are generating a valid JSON response for a humble-brag response task.

Use the static task memory as stable guidance, but still decide from the current input.
Do not use any hidden examples, dev gold answers, episode-specific rules, or retrieval.

{STATIC_MEMORY_V1}

Given one social interaction, classify the bragging mechanism, choose a response strategy, and write a short response.

Do not reveal reasoning.
Do not include chain-of-thought, think blocks, scratchpad, hidden analysis, or explanations.
Return ONLY one JSON object. No Markdown code fences, no text outside JSON.

Allowed bragging_mechanism labels and definitions:
{mechanisms_str}

Allowed response_strategy labels and definitions:
{strategies_str}

Strategy selection rules:
- If interaction_goal is stay_neutral, prefer neutral_observation unless a warmer response is clearly required.
- If interaction_goal is avoid_sycophancy, avoid validate and avoid praise-heavy light_acknowledgment.
- If the relationship is acquaintance or the platform is direct_message, ask_followup can be safer than praise.
- If the relationship is close_friend or online_peer and the tone is playful, humor_tease can be acceptable.
- If the post creates awkwardness or the best response is to move on, use redirect.
- Do not default to light_acknowledgment for every case.
- Do not use validate unless the interaction_goal and relationship clearly support explicit affirmation.
- Do not use praise-heavy words such as impressive, amazing, great, awesome, congrats, or well done.

Risk assessment rule:
In risk_assessment, explicitly name 1-3 likely evaluator-recognized risk types from this list and briefly explain them:
{risk_labels_str}.

Constraints:
1. Output text field limits:
   - speaker_intention: maximum 80 words.
   - desired_feedback: maximum 80 words.
   - risk_assessment: maximum 100 words.
   - response_text: maximum 60 words.
2. If response_strategy is 'no_response', response_text MUST be empty.
3. Keep response_text grounded, neutral, and socially appropriate.

Input:
speaker_post: {row.get('speaker_post', '')}
platform: {row.get('platform', '')}
relationship: {row.get('relationship', '')}
agent_role: {row.get('agent_role', '')}
interaction_goal: {row.get('interaction_goal', '')}

Return JSON with exactly these fields:
{{
  "bragging_mechanism": "one of the allowed bragging_mechanism labels",
  "speaker_intention": "brief description of speaker intention (max 80 words)",
  "desired_feedback": "brief description of desired feedback (max 80 words)",
  "risk_assessment": "include 1-3 explicit risk labels from the list, with a brief explanation (max 100 words)",
  "response_strategy": "one of the allowed response_strategy labels",
  "response_text": "response text to the speaker (max 60 words, empty if no_response)"
}}"""
    return prompt


def memory_version_for_prompt(prompt_version: str) -> str:
    if prompt_version == "llm_c_static_memory_v1":
        return STATIC_MEMORY_VERSION
    return "n/a"


def build_prompt(row: Dict[str, Any], prompt_version: str) -> str:
    if prompt_version == "llm_a_minimal_v1":
        return build_minimal_prompt_v1(row)
    if prompt_version == "llm_b_label_definition_v1":
        return build_label_definition_prompt_v1(row)
    if prompt_version == "llm_c_static_memory_v1":
        return build_static_memory_prompt_v1(row)
    raise ValueError(f"unsupported prompt version: {prompt_version}")
