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

SOCIAL_PUBLIC_PLATFORMS = {
    "public_social_media",
    "community_forum",
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

VISIBILITY_CUES = (
    "going viral",
    "not exposed",
    "not been exposed",
    "ain't been exposed",
    "undiscovered",
    "unrecognized",
    "not noticed",
    "waiting to be seen",
)

LOW_KEY_MECHANISMS = {
    "faux_modesty",
    "understated_flex",
    "achievement_drop",
    "scarcity_flex",
}

LOW_RISK_SHARING_MECHANISMS = LOW_KEY_MECHANISMS | {
    "self_aware_brag",
}

WARMTH_COMPATIBLE_GOALS = {
    "respond_without_moralizing",
    "respond_politely_without_overpraising",
    "be_supportive",
    "be_supportive_without_overpraising",
}

NO_RESPONSE_CUES = (
    "no_response",
    "no response",
    "do not engage",
    "don't engage",
    "decline to engage",
    "avoid engaging",
    "choose not to respond",
)

BOUNDARY_CUES = (
    "set_boundary",
    "set boundary",
    "decline the request",
    "reject the demand",
    "refuse pressure",
    "draw a boundary",
)


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


def _has_public_social_value(
    platform: str,
    relationship: str,
    goal: str,
    mechanism: str,
) -> bool:
    """判断公开交流是否适合保留基本温度，而非机械地保持中性。"""
    social_warmth = (
        platform in SOCIAL_PUBLIC_PLATFORMS
        and relationship not in {"stranger", "supervisor"}
        and goal in WARMTH_COMPATIBLE_GOALS
    )
    conversation_value = mechanism in LOW_RISK_SHARING_MECHANISMS
    return social_warmth and conversation_value


def choose_strategy_with_trace(
    row: dict[str, Any],
    mechanism: str,
    understanding: dict[str, Any],
) -> dict[str, Any]:
    """基于 platform / relationship / goal / mechanism 的通用策略矩阵。"""
    platform = str(row.get("platform", "")).strip()
    relationship = str(row.get("relationship", "")).strip()
    goal = str(row.get("interaction_goal", "")).strip()
    goal_lower = goal.lower()
    speaker_post = str(row.get("speaker_post", "")).lower()

    restrained = _is_restrained(platform, relationship, goal)
    warm_private = _is_warm_private(platform, relationship)
    distant = relationship in DISTANT_RELATIONSHIPS
    self_aware = mechanism == "self_aware_brag" or _contains_any(speaker_post, SELF_AWARE_CUES)
    playful = self_aware or _contains_any(speaker_post, PLAYFUL_CUES)

    def finish(strategy: str, rule: str, *evidence: str) -> dict[str, Any]:
        return {
            "strategy": strategy,
            "strategy_trace": {
                "rule_strategy": strategy,
                "final_strategy": strategy,
                "rule": rule,
                "evidence": [item for item in evidence if item],
            },
        }

    if _contains_any(goal_lower, NO_RESPONSE_CUES):
        return finish("no_response", "explicit_disengagement", goal)

    if _contains_any(goal_lower, BOUNDARY_CUES):
        return finish("set_boundary", "explicit_boundary", goal)

    if goal == "stay_neutral":
        if mechanism == "comparison_superiority" and relationship in {"stranger", "online_peer"}:
            return finish("redirect", "stay_neutral_distant_comparison", relationship)
        return finish("neutral_observation", "stay_neutral", goal)

    if (
        "professional" in goal
        and platform == "group_chat"
        and relationship == "coworker"
        and mechanism != "comparison_superiority"
    ):
        return finish("light_acknowledgment", "semi_professional_peer_group", platform, relationship)

    if "professional" in goal or goal == "maintain_professionalism" or platform in PROFESSIONAL_PLATFORMS:
        if mechanism == "comparison_superiority":
            return finish("redirect", "professional_comparison", platform, mechanism)
        return finish("neutral_observation", "professional_context", platform, goal)

    if "avoid_sycophancy" in goal:
        if mechanism == "comparison_superiority":
            if platform in {"group_chat", "community_forum"}:
                return finish("humor_tease", "avoid_sycophancy_peer_comparison", platform)
            return finish("redirect", "avoid_sycophancy_comparison", mechanism)
        if warm_private and mechanism in LOW_KEY_MECHANISMS:
            return finish("humor_tease", "avoid_sycophancy_warm_low_key", platform, relationship)
        if (
            platform in {"direct_message", "group_chat"}
            and relationship in {"acquaintance", "classmate", "coworker", "online_peer"}
            and mechanism in LOW_KEY_MECHANISMS
        ):
            return finish("ask_followup", "avoid_sycophancy_low_key", platform, relationship)
        strategy = "neutral_observation" if restrained else "light_acknowledgment"
        return finish(strategy, "avoid_sycophancy_default", goal)

    if goal == "respond_without_moralizing":
        if mechanism == "comparison_superiority":
            if platform == "community_forum" and relationship == "stranger":
                return finish("neutral_observation", "non_moralizing_forum_stranger_comparison", platform, relationship)
            return finish("redirect", "non_moralizing_comparison", mechanism)
        if _has_public_social_value(platform, relationship, goal, mechanism):
            return finish(
                "light_acknowledgment",
                "non_moralizing_public_warmth",
                platform,
                relationship,
                mechanism,
            )
        if restrained:
            return finish("neutral_observation", "non_moralizing_restrained", platform)
        strategy = "neutral_observation" if distant else "light_acknowledgment"
        return finish(strategy, "non_moralizing_default", relationship)

    if goal == "deescalate_awkwardness":
        if mechanism == "comparison_superiority":
            return finish("redirect", "deescalate_comparison", mechanism)
        if platform == "group_chat" and relationship == "acquaintance" and mechanism == "faux_modesty":
            return finish("neutral_observation", "deescalate_acquaintance_modesty", platform, relationship)
        if platform in {"group_chat", "community_forum"} and mechanism in {"understated_flex", "self_aware_brag"}:
            return finish("humor_tease", "deescalate_peer_playful", platform, mechanism)
        if warm_private and (playful or mechanism in {"understated_flex", "faux_modesty"}):
            return finish("humor_tease", "deescalate_warm_private", relationship, mechanism)
        strategy = "light_acknowledgment" if not restrained else "neutral_observation"
        return finish(strategy, "deescalate_default", platform, relationship)

    if goal in {"be_supportive", "be_supportive_without_overpraising"}:
        if (
            platform in {"group_chat", "direct_message"}
            and relationship in {"close_friend", "acquaintance"}
            and (
                mechanism == "scarcity_flex"
                or _contains_any(
                    speaker_post,
                    (
                        "happy birthday",
                        "i was there",
                        "live off this story",
                        "private",
                    ),
                )
            )
        ):
            return finish("ask_followup", "supportive_personal_access_story", platform, relationship)
        if mechanism == "comparison_superiority":
            if platform == "direct_message" and relationship == "close_friend":
                return finish("humor_tease", "supportive_close_comparison", relationship)
            strategy = "light_acknowledgment" if warm_private else "redirect"
            return finish(strategy, "supportive_comparison", platform, relationship)
        if warm_private and (playful or mechanism == "self_aware_brag"):
            return finish("humor_tease", "supportive_playful", relationship, mechanism)
        if platform in {"direct_message", "group_chat"} and relationship == "classmate" and mechanism in LOW_KEY_MECHANISMS:
            return finish("ask_followup", "supportive_classmate_low_key", mechanism)
        if (
            platform == "direct_message"
            and relationship == "close_friend"
            and mechanism == "understated_flex"
            and _contains_any(speaker_post, VISIBILITY_CUES)
        ):
            return finish("ask_followup", "supportive_close_visibility_flex", mechanism)
        if platform == "direct_message" and relationship == "close_friend" and mechanism == "faux_modesty":
            return finish("light_acknowledgment", "supportive_close_faux_modesty", mechanism)
        if platform == "direct_message" and relationship == "close_friend" and mechanism in {
            "understated_flex",
            "faux_modesty",
            "achievement_drop",
            "scarcity_flex",
        }:
            return finish("validate", "supportive_close_achievement", mechanism)
        if _has_public_social_value(platform, relationship, goal, mechanism):
            return finish(
                "light_acknowledgment",
                "supportive_public_warmth",
                platform,
                relationship,
                mechanism,
            )
        if restrained:
            return finish("neutral_observation", "supportive_restrained", platform)
        return finish("light_acknowledgment", "supportive_default", relationship)

    if goal == "respond_politely_without_overpraising":
        if mechanism == "comparison_superiority":
            if platform == "public_social_media" and relationship == "acquaintance":
                return finish("neutral_observation", "polite_public_acquaintance_comparison", platform, relationship)
            return finish("redirect", "polite_comparison", mechanism)
        if (
            platform == "public_social_media"
            and relationship == "online_peer"
            and mechanism == "understated_flex"
            and _contains_any(speaker_post, VISIBILITY_CUES)
        ):
            return finish("neutral_observation", "polite_public_visibility_flex", platform, relationship)
        if (
            platform == "public_social_media"
            and relationship == "acquaintance"
            and mechanism == "faux_modesty"
        ):
            return finish("neutral_observation", "polite_public_acquaintance_modesty", platform, relationship)
        if (
            platform == "direct_message"
            and relationship in {"classmate", "online_peer"}
            and mechanism in LOW_KEY_MECHANISMS
        ):
            return finish("ask_followup", "polite_private_peer_low_key", platform, relationship)
        if _has_public_social_value(platform, relationship, goal, mechanism):
            return finish(
                "light_acknowledgment",
                "polite_public_warmth",
                platform,
                relationship,
                mechanism,
            )
        if restrained:
            return finish("neutral_observation", "polite_restrained", platform)
        return finish("light_acknowledgment", "polite_default", relationship)

    if mechanism == "comparison_superiority":
        return finish("redirect", "default_comparison", mechanism)
    if warm_private and playful:
        return finish("humor_tease", "default_warm_playful", relationship)
    if restrained:
        return finish("neutral_observation", "default_restrained", platform, relationship)

    return finish(DEFAULT_STRATEGY, "default", platform, relationship)


def choose_strategy(
    row: dict[str, Any],
    mechanism: str,
    understanding: dict[str, Any],
) -> str:
    """返回策略矩阵的最终策略。"""
    return choose_strategy_with_trace(row, mechanism, understanding)["strategy"]
