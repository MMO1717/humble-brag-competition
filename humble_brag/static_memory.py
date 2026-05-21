from __future__ import annotations


STATIC_MEMORY_VERSION = "STATIC_MEMORY_V1"

STATIC_MEMORY_V1 = """Static task memory:

Core behavior:
- Do not default to praise.
- Many humble-brags should be handled with neutral observation, grounded follow-up, redirect, or light teasing.
- Keep response_text brief, grounded, and socially appropriate.
- Avoid sycophantic language unless validation is clearly appropriate.

Strategy selection memory:
- For stay_neutral, prefer neutral_observation.
- For avoid_sycophancy, avoid validate and praise-heavy light_acknowledgment.
- For acquaintance or direct_message contexts, ask_followup can be safer than praise.
- For close_friend or playful online_peer contexts, humor_tease can be acceptable.
- Use redirect when continuing the brag would be awkward or unhelpful.
- Use validate sparingly, only when explicit affirmation fits the relationship and interaction_goal.

Risk label memory:
- risk_assessment should explicitly mention 1-3 likely evaluator-recognized risk labels.
- Prefer these risk names over vague natural language: sycophancy, preachiness, misrecognition, strategy_inconsistency, context_insensitivity, over_coldness.
- Briefly explain why the named risk applies.

Mechanism memory:
- achievement_drop: direct mention of accomplishment, score, status, award, output, or performance.
- comparison_superiority: explicit or implicit comparison that makes the speaker seem better.
- faux_modesty: modest or self-effacing wording that still highlights an achievement.
- humble_complaint: complaint about a burden or inconvenience caused by success or ability.
- scarcity_flex: rare access, exclusivity, elite opportunity, or limited availability.
- self_aware_brag: explicit awareness of bragging, such as "not to brag" or "flex".
- understated_flex: indirect impressive framing without a direct brag cue.

Style memory:
- For neutral_observation, do not use words like impressive, amazing, great, awesome, congrats, or well done.
- For avoid_sycophancy, focus on context or substance instead of praise.
- For direct_message or acquaintance contexts, avoid overly familiar teasing.
- For public forums, keep the response non-escalatory and context-aware."""
