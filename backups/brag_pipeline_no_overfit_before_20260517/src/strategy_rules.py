from __future__ import annotations

from typing import Any

from .schemas import DEFAULT_STRATEGY


RESTRAINED_PLATFORMS = {
    "workplace_channel",
    "academic_forum",
    "public_social_media",
}

PRIVATE_FRIEND_PLATFORMS = {
    "private_chat",
    "direct_message",
    "group_chat",
}


SELF_AWARE_CUES = (
    "not to brag",
    "do not mean to brag",
    "don't mean to brag",
    "do n't mean to brag",
    "humblebrag",
    "flex",
)

PLAYFUL_CUES = (
    "true gaming skill",
    "gaming skill",
    "lol",
    "haha",
    "😂",
    ":face_with_tears_of_joy:",
)


def choose_strategy(
    row: dict[str, Any],
    mechanism: str,
    understanding: dict[str, Any],
) -> str:
    platform = str(row.get("platform", "")).strip()
    relationship = str(row.get("relationship", "")).strip()
    interaction_goal = str(row.get("interaction_goal", "")).strip()
    speaker_post = str(row.get("speaker_post", "")).lower()

    has_self_aware_cue = any(cue in speaker_post for cue in SELF_AWARE_CUES)
    has_playful_cue = any(cue in speaker_post for cue in PLAYFUL_CUES)

    if (
        relationship == "close_friend"
        and platform in PRIVATE_FRIEND_PLATFORMS
        and (mechanism == "self_aware_brag" or has_self_aware_cue or has_playful_cue)
    ):
        return "humor_tease"

    if (
        platform == "community_forum"
        and has_playful_cue
        and "professional" not in interaction_goal
    ):
        return "humor_tease"

    if (
        platform == "direct_message"
        and relationship in {"acquaintance", "classmate", "coworker"}
        and "avoid_sycophancy" in interaction_goal
    ):
        return "ask_followup"

    if (
        platform in RESTRAINED_PLATFORMS
        or interaction_goal == "stay_neutral"
        or "professional" in interaction_goal
    ):
        return "neutral_observation"

    return DEFAULT_STRATEGY
