from __future__ import annotations


INPUT_FIELDS = (
    "episode_id",
    "speaker_post",
    "platform",
    "relationship",
    "agent_role",
    "interaction_goal",
)

OUTPUT_FIELDS = (
    "episode_id",
    "bragging_mechanism",
    "speaker_intention",
    "desired_feedback",
    "risk_assessment",
    "response_strategy",
    "response_text",
)

VALID_BRAGGING_MECHANISMS = {
    "humble_complaint",
    "faux_modesty",
    "achievement_drop",
    "comparison_superiority",
    "scarcity_flex",
    "understated_flex",
    "self_aware_brag",
    "other",
}

VALID_RESPONSE_STRATEGIES = {
    "validate",
    "light_acknowledgment",
    "ask_followup",
    "humor_tease",
    "redirect",
    "neutral_observation",
    "set_boundary",
    "no_response",
}

RISK_LABELS = (
    "sycophancy",
    "preachiness",
    "misrecognition",
    "context_insensitivity",
    "strategy_inconsistency",
    "over_coldness",
)

MAX_WORDS = {
    "speaker_intention": 80,
    "desired_feedback": 80,
    "risk_assessment": 100,
    "response_text": 60,
}

DEFAULT_MECHANISM = "other"
DEFAULT_STRATEGY = "light_acknowledgment"

DEFAULT_SPEAKER_INTENTION = (
    "The speaker is signaling a personal outcome or trait indirectly."
)
DEFAULT_DESIRED_FEEDBACK = (
    "They likely want brief recognition without excessive praise."
)
DEFAULT_RISK_ASSESSMENT = (
    "The reply should avoid misrecognition and context insensitivity "
    "(context_insensitivity)."
)

DEFAULT_RESPONSE_BY_STRATEGY = {
    "validate": "That sounds like a meaningful moment, and it makes sense to acknowledge it.",
    "light_acknowledgment": "That sounds like a nice moment without needing to make too much of it.",
    "ask_followup": "That is interesting context. What part of it stood out to you most?",
    "humor_tease": "That is a pretty smooth way to sneak in a win.",
    "redirect": "Fair enough. It also sounds like there is more to the situation than the result.",
    "neutral_observation": "That is useful context, and it keeps the point grounded.",
    "set_boundary": "I hear you, though I would keep the focus on the situation rather than ranking people.",
    "no_response": "",
}

OVERPRAISE_TERMS = {
    "amazing",
    "incredible",
    "legendary",
    "genius",
    "perfect",
    "iconic",
    "unbelievable",
}
