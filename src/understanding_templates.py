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
    if _contains_any(post, ("birthday", "happy birthday", "turning a year older")):
        return "the birthday surprise"
    if _contains_any(post, ("gig", "concert", "lollapalooza", "band", "music", "song")):
        return "the music story"
    if _contains_any(post, ("school", "class", "grades", "4.0", "assignment")):
        return "the school moment"
    if _contains_any(post, ("dog", "pug", "ralph", "baby talk")):
        return "the dog story"
    if _contains_any(post, ("sold over", "sold", "client", "project", "team", "boss", "manager")):
        return "the work achievement"
    if _contains_any(post, ("tackles", "interception", "season", "defense")):
        return "the sports performance"
    if _contains_any(post, ("family", "thread", "disagreement", "facts", "constructive")):
        return "the family discussion"
    if _contains_any(post, ("partner", "man i have", "thankful for the type of man")):
        return "the relationship appreciation"
    if _contains_any(post, ("car", "cars", "collection")):
        return "the car collection"
    if _contains_any(post, ("political art", "english", "studies")):
        return "the class topic"
    if _contains_any(post, ("screen", "score", "reading", "conditions", "harder", "slower")):
        return "the harder performance context"
    if _contains_any(post, ("game", "gaming", "min-max", "gamer", "optimization", "build")):
        return "the gaming joke"
    if _contains_any(post, ("vegg", "healthy", "habit", "workout", "gym", "run", "running", "injury")):
        return "the personal progress"
    if _contains_any(post, ("private", "invite", "preview", "access")):
        return "the rare experience"
    if _contains_any(post, ("work",)):
        return "the work achievement"
    if _contains_any(post, ("snapchat", "notifications", "thirst")):
        return "the social attention"
    if _contains_any(post, ("viral", "talent", "talented", "exposed")):
        return "the confidence about being noticed"
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
        feedback = f"They likely want curious engagement with {theme} that keeps the conversation going without overpraise."
    elif strategy == "humor_tease":
        feedback = f"They likely want amused recognition of {theme} without making it too serious."
    elif strategy == "redirect":
        feedback = f"They likely want {theme} acknowledged while keeping the conversation focused on the main point."
    elif strategy == "neutral_observation":
        feedback = f"They likely want measured acknowledgment of {theme} without turning it into personal praise."
    elif strategy == "validate":
        feedback = f"They likely want warm recognition of {theme} that feels supportive without exaggeration."
    elif strategy == "set_boundary":
        feedback = f"They likely need {theme} acknowledged without amplifying the comparison or flex."
    else:
        feedback = f"They likely want brief acknowledgment of {theme} without advice, judgment, or excessive praise."

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
