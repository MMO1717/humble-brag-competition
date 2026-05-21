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
    "\U0001f602",
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


# --- Legacy wrapper for non-SkillFlow path ---

def apply_strategy_rules(
    row: dict[str, Any],
    candidate: dict[str, Any],
    rule_version: str = "none"
) -> tuple[dict[str, Any], dict[str, Any]]:
    strat_before = candidate.get("response_strategy", "neutral_observation")

    rule_trace = {
        "strategy_rule_version": rule_version,
        "strategy_rule_applied": False,
        "strategy_before": strat_before,
        "strategy_after": strat_before,
        "strategy_rule_reason": None
    }

    if rule_version == "none":
        return candidate, rule_trace

    if rule_version == "v1":
        new_candidate = dict(candidate)

        post = row.get("speaker_post", "").lower()
        platform = row.get("platform", "")
        relationship = row.get("relationship", "")
        interaction_goal = row.get("interaction_goal", "")

        if strat_before == "humor_tease" and relationship in ["acquaintance", "online_peer"] and platform == "direct_message":
            if interaction_goal == "avoid_sycophancy":
                new_strat = "ask_followup"
                reason = "dm_non_close_friend_no_humor_tease_avoid_sycophancy"
            else:
                new_strat = "light_acknowledgment"
                reason = "dm_non_close_friend_no_humor_tease_default"

            new_candidate["response_strategy"] = new_strat
            rule_trace.update({
                "strategy_rule_applied": True,
                "strategy_after": new_strat,
                "strategy_rule_reason": reason
            })
            return new_candidate, rule_trace

        absurd_keywords = ["dog", "pug", "pet", "vegetables", "absurd", "shocked", "obviously", "somehow", "true skill"]
        is_absurd = any(kw in post for kw in absurd_keywords)
        if interaction_goal == "deescalate_awkwardness" and strat_before in ["neutral_observation", "light_acknowledgment"] and is_absurd:
            if relationship == "close_friend" or platform in ["group_chat", "public_social_media", "social_media", "community_forum"]:
                new_strat = "humor_tease"
                reason = "deescalate_awkwardness_absurd_post_tease"
            else:
                new_strat = "redirect"
                reason = "deescalate_awkwardness_absurd_post_redirect"

            new_candidate["response_strategy"] = new_strat
            rule_trace.update({
                "strategy_rule_applied": True,
                "strategy_after": new_strat,
                "strategy_rule_reason": reason
            })
            return new_candidate, rule_trace

        achievement_keywords = ["forgot what it's like to be good", "finally", "asking me for help", "finished a thing", "grade", "score", "finished", "class", "exam", "built"]
        has_validation_cue = any(kw in post for kw in achievement_keywords)
        if relationship == "close_friend" and strat_before in ["humor_tease", "neutral_observation"] and has_validation_cue and interaction_goal != "avoid_sycophancy":
            new_strat = "validate"
            new_candidate["response_strategy"] = new_strat
            rule_trace.update({
                "strategy_rule_applied": True,
                "strategy_after": new_strat,
                "strategy_rule_reason": "close_friend_genuine_achievement_support"
            })
            return new_candidate, rule_trace

        aspiration_keywords = ["going viral", "famous", "talented and", "this year", "future", "career"]
        has_aspiration_cue = any(kw in post for kw in aspiration_keywords)
        if relationship == "close_friend" and platform == "direct_message" and strat_before == "humor_tease" and has_aspiration_cue:
            new_strat = "ask_followup"
            new_candidate["response_strategy"] = new_strat
            rule_trace.update({
                "strategy_rule_applied": True,
                "strategy_after": new_strat,
                "strategy_rule_reason": "close_friend_future_aspiration_followup"
            })
            return new_candidate, rule_trace

        family_keywords = ["family", "argue", "parents", "thread", "gathering"]
        has_private_cue = any(kw in post for kw in family_keywords)
        if relationship in ["acquaintance", "online_peer"] and platform in ["public_social_media", "social_media", "group_chat", "community_forum"] and strat_before in ["light_acknowledgment", "validate"] and has_private_cue:
            new_strat = "neutral_observation"
            new_candidate["response_strategy"] = new_strat
            rule_trace.update({
                "strategy_rule_applied": True,
                "strategy_after": new_strat,
                "strategy_rule_reason": "public_acquaintance_private_topic_neutral"
            })
            return new_candidate, rule_trace

        substantive_keywords = ["project", "work", "score", "exam", "research", "game", "finished", "built", "training", "run", "read", "made", "learned", "wrote"]
        has_substantive_cue = any(kw in post for kw in substantive_keywords)
        if interaction_goal == "avoid_sycophancy" and (relationship == "acquaintance" or platform == "direct_message") and strat_before in ["neutral_observation", "light_acknowledgment"] and has_substantive_cue:
            if not is_absurd:
                new_strat = "ask_followup"
                new_candidate["response_strategy"] = new_strat
                rule_trace.update({
                    "strategy_rule_applied": True,
                    "strategy_after": new_strat,
                    "strategy_rule_reason": "avoid_sycophancy_substantive_followup"
                })
                return new_candidate, rule_trace

    return candidate, rule_trace
