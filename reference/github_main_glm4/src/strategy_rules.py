from __future__ import annotations

from typing import Any

from .schemas import DEFAULT_STRATEGY


RESTRAINED_PLATFORMS = {
    "workplace_channel",
    "academic_forum",
    "public_social_media",
}

PROFESSIONAL_PLATFORMS = {
    "workplace_channel",
    "academic_forum",
}

PRIVATE_OR_WARM_PLATFORMS = {
    "private_chat",
    "direct_message",
    "group_chat",
}

WARM_RELATIONSHIPS = {
    "close_friend",
    "friend",
    "family_member",
    "romantic_partner",
}

DISTANT_RELATIONSHIPS = {
    "stranger",
    "online_peer",
    "acquaintance",
    "supervisor",
}

SELF_AWARE_CUES = (
    "not to brag",
    "do not mean to brag",
    "don't mean to brag",
    "do n't mean to brag",
    "humblebrag",
    "tiny brag",
    "small brag",
    "bragging",
    "small flex",
    "flex",
    "showing off",
)

PLAYFUL_CUES = (
    "lol",
    "haha",
    "joking",
    "kidding",
    "😂",
    ":face_with_tears_of_joy:",
)

LOW_KEY_MECHANISMS = {
    "faux_modesty",
    "understated_flex",
    "achievement_drop",
    "scarcity_flex",
}


def _contains_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def _is_warm_private(platform: str, relationship: str) -> bool:
    return platform in PRIVATE_OR_WARM_PLATFORMS and relationship in WARM_RELATIONSHIPS


def _is_restrained(platform: str, relationship: str, goal: str) -> bool:
    return (
        platform in RESTRAINED_PLATFORMS
        or relationship in {"stranger", "supervisor"}
        or "professional" in goal
        or "neutral" in goal
    )


def choose_strategy(
    row: dict[str, Any],
    mechanism: str,
    understanding: dict[str, Any],
) -> str:
    """基于 platform / relationship / goal / mechanism 的通用策略矩阵。"""
    platform = str(row.get("platform", "")).strip()
    relationship = str(row.get("relationship", "")).strip()
    goal = str(row.get("interaction_goal", "")).strip()
    speaker_post = str(row.get("speaker_post", "")).lower()

    restrained = _is_restrained(platform, relationship, goal)
    warm_private = _is_warm_private(platform, relationship)
    distant = relationship in DISTANT_RELATIONSHIPS
    self_aware = mechanism == "self_aware_brag" or _contains_any(speaker_post, SELF_AWARE_CUES)
    playful = self_aware or _contains_any(speaker_post, PLAYFUL_CUES)

    if goal == "stay_neutral":
        return "neutral_observation"

    if "professional" in goal or goal == "maintain_professionalism" or platform in PROFESSIONAL_PLATFORMS:
        if mechanism == "comparison_superiority":
            return "redirect"
        return "neutral_observation"

    if "avoid_sycophancy" in goal:
        if mechanism == "comparison_superiority":
            if platform in {"group_chat", "community_forum"}:
                return "humor_tease"
            return "redirect"
        if (
            platform in {"direct_message", "group_chat"}
            and relationship in {"acquaintance", "classmate", "coworker", "online_peer"}
            and mechanism in LOW_KEY_MECHANISMS
        ):
            return "ask_followup"
        return "neutral_observation" if restrained else "light_acknowledgment"

    if goal == "respond_without_moralizing":
        if mechanism == "comparison_superiority":
            return "redirect"
        if restrained:
            return "neutral_observation"
        return "neutral_observation" if distant else "light_acknowledgment"

    if goal == "deescalate_awkwardness":
        if mechanism == "comparison_superiority":
            return "redirect"
        if platform in {"group_chat", "community_forum"} and mechanism in {"understated_flex", "self_aware_brag"}:
            return "humor_tease"
        if warm_private and (playful or mechanism in {"understated_flex", "faux_modesty"}):
            return "humor_tease"
        return "light_acknowledgment" if not restrained else "neutral_observation"

    if goal in {"be_supportive", "be_supportive_without_overpraising"}:
        if mechanism == "comparison_superiority":
            if platform == "direct_message" and relationship == "close_friend":
                return "humor_tease"
            return "light_acknowledgment" if warm_private else "redirect"
        if warm_private and (playful or mechanism == "self_aware_brag"):
            return "humor_tease"
        if platform in {"direct_message", "group_chat"} and relationship == "classmate" and mechanism in LOW_KEY_MECHANISMS:
            return "ask_followup"
        if platform == "direct_message" and relationship == "close_friend" and mechanism == "faux_modesty":
            return "light_acknowledgment"
        if platform == "direct_message" and relationship == "close_friend" and mechanism in {
            "understated_flex",
            "faux_modesty",
            "achievement_drop",
            "scarcity_flex",
        }:
            return "validate"
        if restrained:
            return "neutral_observation"
        return "light_acknowledgment"

    if goal == "respond_politely_without_overpraising":
        if mechanism == "comparison_superiority":
            return "redirect"
        if restrained:
            return "neutral_observation"
        return "light_acknowledgment"

    if mechanism == "comparison_superiority":
        return "redirect"
    if warm_private and playful:
        return "humor_tease"
    if restrained:
        return "neutral_observation"

    return DEFAULT_STRATEGY
