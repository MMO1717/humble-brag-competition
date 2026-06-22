from __future__ import annotations

import re
from typing import Any

from .postprocess import clean_field_text
from .schemas import DEFAULT_DESIRED_FEEDBACK, DEFAULT_SPEAKER_INTENTION, MAX_WORDS


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def infer_understanding_theme(input_row: dict[str, Any], mechanism: str) -> str:
    post = str(input_row.get("speaker_post", "")).lower()
    if _contains_any(post, ("screen", "score", "reading", "conditions", "harder", "slower")):
        return "the harder performance context"
    if _contains_any(post, ("game", "gaming", "min-max", "gamer", "optimization", "build")):
        return "the gaming joke"
    if _contains_any(post, ("vegg", "healthy", "habit", "workout", "gym", "run")):
        return "the personal progress"
    if _contains_any(post, ("concert", "music", "band", "birthday", "private", "invite", "preview", "access")):
        return "the rare experience"
    if _contains_any(post, ("work", "client", "project", "team", "boss", "manager")):
        return "the work achievement"
    if mechanism == "comparison_superiority" or re.search(r"\b(better|more than|most people|everyone else)\b", post):
        return "the comparison"
    if mechanism == "scarcity_flex":
        return "the rare access"
    return "the moment"


def build_understanding_templates(
    input_row: dict[str, Any],
    mechanism: str,
    strategy: str | None = None,
) -> dict[str, str]:
    strategy = str(strategy or "")
    theme = infer_understanding_theme(input_row, mechanism)

    if mechanism == "comparison_superiority":
        intention = f"They are framing {theme} as stronger than others while trying to keep the point socially acceptable."
    elif mechanism == "scarcity_flex":
        intention = f"They are signaling rare access or a special experience while trying to sound casual."
    elif mechanism == "humble_complaint":
        intention = f"They are presenting a complaint while also signaling an achievement or status advantage."
    elif mechanism == "faux_modesty":
        intention = f"They are downplaying {theme} while still inviting recognition for it."
    elif mechanism == "self_aware_brag":
        intention = f"They are jokingly acknowledging the brag while still wanting recognition for {theme}."
    elif mechanism == "achievement_drop":
        intention = f"They are sharing {theme} as an achievement and looking for measured acknowledgment."
    else:
        intention = f"They are sharing {theme} in a casual way while hoping it is noticed."

    if strategy == "ask_followup":
        feedback = "They likely want curious engagement that keeps the conversation going without overpraise."
    elif strategy == "humor_tease":
        feedback = "They likely want amused recognition that gets the joke without making the moment too serious."
    elif strategy == "redirect":
        feedback = "They likely want the context acknowledged while keeping the conversation focused on the main point."
    elif strategy == "neutral_observation":
        feedback = "They likely want measured acknowledgment without turning it into personal praise."
    elif strategy == "validate":
        feedback = "They likely want warm recognition that feels supportive without exaggeration."
    elif strategy == "set_boundary":
        feedback = "They likely need a response that acknowledges the point without amplifying the comparison or flex."
    else:
        feedback = "They likely want brief acknowledgment without advice, judgment, or excessive praise."

    return {
        "speaker_intention": intention,
        "desired_feedback": feedback,
    }


def repair_understanding_fields(
    state: dict[str, Any],
    input_row: dict[str, Any],
    fields: set[str],
) -> dict[str, str]:
    templates = build_understanding_templates(
        input_row,
        str(state.get("bragging_mechanism") or "other"),
        state.get("response_strategy"),
    )
    if "speaker_intention" in fields:
        state["speaker_intention"] = clean_field_text(
            templates["speaker_intention"],
            DEFAULT_SPEAKER_INTENTION,
            MAX_WORDS["speaker_intention"],
        )
    if "desired_feedback" in fields:
        state["desired_feedback"] = clean_field_text(
            templates["desired_feedback"],
            DEFAULT_DESIRED_FEEDBACK,
            MAX_WORDS["desired_feedback"],
        )
    state["understanding_template_repair"] = {
        "enabled": True,
        "fields": sorted(fields),
        "templates": templates,
    }
    return templates
