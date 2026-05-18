from __future__ import annotations

import json
import re
import hashlib
from typing import Any

from .schemas import (
    DEFAULT_DESIRED_FEEDBACK,
    DEFAULT_MECHANISM,
    DEFAULT_RESPONSE_BY_STRATEGY,
    DEFAULT_RISK_ASSESSMENT,
    DEFAULT_SPEAKER_INTENTION,
    DEFAULT_STRATEGY,
    MAX_WORDS,
    OVERPRAISE_TERMS,
    RISK_LABELS,
)


SUSPICIOUS_PATTERNS = [
    re.compile(r"<think>|</think>", re.IGNORECASE),
    re.compile(r"\bchain of thought\b", re.IGNORECASE),
    re.compile(r"\bstep by step\b", re.IGNORECASE),
    re.compile(r"\b(reasoning|analysis|scratchpad)\s*:", re.IGNORECASE),
    re.compile(r"^(system|assistant|user)\s*:", re.IGNORECASE),
    re.compile(r"\b(option|candidate)\s*[12]\b", re.IGNORECASE),
]

CODE_FENCE_RE = re.compile(r"```(?:json|text|markdown)?\s*|\s*```", re.IGNORECASE)
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
PREFIX_RE = re.compile(r"^\s*(assistant|response|answer|analysis|reasoning)\s*:\s*", re.IGNORECASE)
WORD_RE = re.compile(r"\b[\w'-]+\b")

EVALUATOR_RISK_KEYWORDS = {
    "sycophancy": (
        "sycophancy",
        "sycophantic",
        "overpraise",
        "over-praise",
        "excessive praise",
        "blind validation",
        "flattery",
    ),
    "preachiness": (
        "preach",
        "preachy",
        "moralize",
        "moralizing",
        "lecture",
        "judgmental",
    ),
    "misrecognition": (
        "misrecognition",
        "misread",
        "misinterpret",
        "false assumption",
        "assume expertise",
        "unsupported assumption",
    ),
    "strategy_inconsistency": (
        "strategy inconsistency",
        "inconsistent strategy",
        "mismatch",
        "does not match the strategy",
    ),
    "context_insensitivity": (
        "context insensitivity",
        "context insensitive",
        "ignore the context",
        "miss the context",
        "audience",
        "setting",
    ),
    "over_coldness": (
        "over cold",
        "over-cold",
        "too cold",
        "dismissive",
        "curt",
        "coldness",
    ),
}

RISK_RENDER_ORDER = (
    "misrecognition",
    "context_insensitivity",
    "sycophancy",
    "preachiness",
    "strategy_inconsistency",
    "over_coldness",
)

CONSTRAINED_PLATFORMS = {"workplace_channel", "academic_forum", "public_social_media"}
CONSTRAINED_RELATIONSHIPS = {"supervisor", "stranger"}
PUBLIC_PLATFORMS = {"public_social_media", "community_forum", "academic_forum", "workplace_channel"}
WARM_RELATIONSHIPS = {"close_friend", "friend", "family_member", "romantic_partner"}

THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "achievement": (
        "award", "accepted", "published", "promotion", "raise", "grade",
        "score", "school", "class", "job", "work", "sales", "sold",
        "finished", "completed", "certification", "review",
    ),
    "skill": (
        "skill", "talent", "learned", "quickly", "read", "write",
        "game", "play", "solve", "handled", "built", "fixed",
    ),
    "affiliation": (
        "friend", "network", "contact", "invited", "met", "know",
        "connection", "family", "mentor", "organizer",
    ),
    "attention": ("attention", "notifications", "viral", "followers", "quoted"),
    "resilience": ("injury", "rough", "tough", "despite", "struggle", "failure"),
    "possession": ("car", "house", "home", "seat", "preview", "access"),
}

THEME_PHRASES = {
    "achievement": "the accomplishment",
    "skill": "the skill",
    "affiliation": "the connection",
    "attention": "the attention",
    "resilience": "the progress",
    "possession": "the experience",
    "scarcity": "the rare moment",
    "superiority": "the comparison",
    "other": "the point",
}

MECHANISM_PHRASES = {
    "humble_complaint": "the mixed complaint and flex",
    "faux_modesty": "the modest framing",
    "achievement_drop": "the achievement note",
    "comparison_superiority": "the comparison",
    "scarcity_flex": "the rare-moment flex",
    "understated_flex": "the understated flex",
    "self_aware_brag": "the self-aware brag",
    "other": "the point",
}

CONTEXT_PHRASES = {
    "professional": "in a professional setting",
    "constrained": "in this setting",
    "warm_private": "between people who know each other",
    "peer_group": "with the group",
    "public": "in public",
    "neutral": "in this context",
}

TONE_PHRASES = {
    "professional": "with the setting in mind",
    "neutral": "in a measured way",
    "warm": "with a little warmth",
    "playful": "lightly",
}

GENERALIZED_TEMPLATE_BANK: dict[str, tuple[str, ...]] = {
    "ask_followup": (
        "Interesting context. What part of {topic} felt most worth mentioning?",
        "I get the point. How did {topic} come up?",
        "That gives some useful background. What do you want people to take from it?",
        "Fair enough. What matters most about {mechanism_phrase} here?",
        "That is a specific angle. What made it stand out?",
        "Makes sense. Was the main point {topic}, or the context around it?",
    ),
    "neutral_observation": (
        "That is useful context, and it works well when the point stays measured.",
        "It makes sense to note {topic}, without making it a bigger claim.",
        "There is relevant context around {mechanism_phrase}.",
        "That frames the situation more clearly {context_phrase}.",
        "I can see the point, though the tone should stay grounded.",
        "The context is relevant, even if it does not need much emphasis.",
    ),
    "light_acknowledgment": (
        "Fair enough. That seems worth a small nod.",
        "I can see why that would feel worth mentioning.",
        "A measured nod fits {context_phrase}.",
        "That is a reasonable thing to acknowledge {tone_phrase}.",
        "There is a small but real point around {mechanism_phrase}.",
        "That can be noted while keeping the reaction modest.",
    ),
    "humor_tease": (
        "Fair, that is a careful way to slip the point in.",
        "I see the angle, and I will keep the reaction modest.",
        "That is one way to make {topic} sound casual.",
        "There is a little quiet flexing in there.",
        "Point taken, with the reaction kept low-key.",
        "I see what is happening there, and I will keep it light.",
    ),
    "validate": (
        "That sounds meaningful, especially with the context around it.",
        "I can see why {topic} would feel good to acknowledge.",
        "It makes sense to take a small moment with that.",
        "That sounds like a solid outcome, kept in perspective.",
        "That is worth recognizing in a measured way.",
        "That sounds good, and a low-key response fits it.",
    ),
    "redirect": (
        "That gives context. I would connect it back to the main point.",
        "Fair enough. The useful part is what it adds to the discussion.",
        "That detail can help, as long as the focus stays on the shared topic.",
        "I would keep the emphasis on what it means for the situation.",
        "Point taken. I would bring it back to what the group is discussing.",
        "Useful context, but I would keep the conversation moving toward the core point.",
    ),
    "set_boundary": (
        "I hear the point, but I would keep the focus on the shared issue here.",
        "I get what you mean, but I do not want to turn this into a comparison.",
        "That may be true, but I would rather not rank people around {topic}.",
        "I can acknowledge {topic} without turning it into a praise moment.",
        "That is noted, though I would keep the response focused and fair.",
        "I would rather keep this about the situation than about personal standing.",
    ),
    "no_response": ("",),
}

CONSTRAINED_HUMOR_TEMPLATES = (
    "I see the light joke there, but I would keep the response measured.",
    "There is a playful angle, though the setting calls for a restrained reply.",
    "That can be acknowledged lightly without leaning into the tease.",
    "The joke lands cleanly if the reaction stays low-key.",
)

SELF_AWARE_MECHANISM_RE = re.compile(
    r"\b(not to brag|do not mean to brag|don't mean to brag|humblebrag|tiny brag|small brag|small flex)\b",
    re.I,
)

COMPARISON_MECHANISM_RE = re.compile(
    r"\b("
    r"most people|other people|others?|everyone else|some people|"
    r"better than|faster than|smarter than|stronger than|more skilled than|"
    r"way better|true .{0,30}skill|real .{0,30}skill|"
    r"yalls? post|people around me started asking me|"
    r"(two|three|four|five) of (these|the) exact"
    r")\b",
    re.I,
)

SCARCITY_MECHANISM_RE = re.compile(
    r"\b("
    r"invitation-only|invite-only|private preview|closed beta|limited|restricted|"
    r"rare access|direct access|only got one seat|one seat|private session|closed group"
    r")\b",
    re.I,
)

FAUX_MODESTY_MECHANISM_RE = re.compile(
    r"\b("
    r"not sure how|somehow|i guess|apparently|i don't think i did anything special|"
    r"sorry[, ]+such|sorry for|feel blessed|feeling grateful|pretty rare|feels rare"
    r")\b",
    re.I,
)

ACHIEVEMENT_MECHANISM_RE = re.compile(
    r"\b("
    r"award|accepted|published|promotion|promoted|raise|certification|client win|"
    r"good grades|top grades|4\\.0|sold|sales|finished|completed|i was there when|"
    r"became the example|became the template"
    r")\b",
    re.I,
)

HUMBLE_COMPLAINT_RE = re.compile(
    r"\b("
    r"tired|exhausted|barely rested|wish|annoying|awkward|too many|kept asking|"
    r"inbox|notifications|urgent request|more work|burden|hard to keep up"
    r")\b",
    re.I,
)


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def truncate_words(text: str, max_words: int) -> str:
    words = WORD_RE.findall(text)
    if len(words) <= max_words:
        return text
    kept = words[:max_words]
    return " ".join(kept).rstrip(" ,;:") + "."


def compact_text(text: Any) -> str:
    if isinstance(text, list):
        text = "; ".join(str(item) for item in text if item is not None)
    elif text is None:
        text = ""
    else:
        text = str(text)
    text = THINK_BLOCK_RE.sub("", text)
    text = CODE_FENCE_RE.sub("", text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = PREFIX_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip("`\"' ")


def parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = compact_text(text)
    candidates = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def normalize_label(text: Any, valid_labels: set[str], default: str) -> str:
    raw = compact_text(text).lower()
    raw = raw.replace("-", "_").replace(" ", "_")
    raw = re.sub(r"[^a-z0-9_]", "", raw)
    if raw in valid_labels:
        return raw
    for label in valid_labels:
        if label in raw:
            return label
        if re.search(rf"\b{re.escape(label)}\b", raw):
            return label
    return default


def calibrate_mechanism(input_row: dict[str, Any], predicted: str) -> str:
    """General cue-based mechanism calibration after the model classifier."""

    post = compact_text(input_row.get("speaker_post", ""))
    lowered = post.lower()

    if SELF_AWARE_MECHANISM_RE.search(post):
        return "self_aware_brag"

    if COMPARISON_MECHANISM_RE.search(post):
        return "comparison_superiority"

    if (
        predicted == "humble_complaint"
        and re.search(r"\b(score|result|performance)\b", lowered)
        and re.search(r"\b(impressive|strong|better|ahead)\b", lowered)
    ):
        return "understated_flex"

    if FAUX_MODESTY_MECHANISM_RE.search(post):
        return "faux_modesty"

    if SCARCITY_MECHANISM_RE.search(post):
        return "scarcity_flex"

    if ACHIEVEMENT_MECHANISM_RE.search(post):
        return "achievement_drop"

    if HUMBLE_COMPLAINT_RE.search(post) and re.search(
        r"\b(success|reliable|attention|asked|requests?|work|handled|result|won|finished)\b",
        lowered,
    ):
        return "humble_complaint"

    return predicted


def has_suspicious_text(text: str) -> bool:
    return any(pattern.search(text) for pattern in SUSPICIOUS_PATTERNS)


def clean_field_text(value: Any, fallback: str, max_words: int) -> str:
    cleaned = compact_text(value)
    if not cleaned or has_suspicious_text(cleaned):
        cleaned = fallback
    return truncate_words(cleaned, max_words)


def _extract_response_from_json(text: str) -> str:
    parsed = parse_json_object(text)
    if not parsed:
        return text
    for key in ("response_text", "response", "reply", "text"):
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def contains_overpraise(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in OVERPRAISE_TERMS)


def _extract_risk_keywords(text: str) -> set[str]:
    lowered = text.lower()
    labels: set[str] = set()
    for label in RISK_LABELS:
        if label in lowered:
            labels.add(label)
    for label, keywords in EVALUATOR_RISK_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            labels.add(label)
    return labels


def _infer_contextual_risk_labels(
    input_row: dict[str, Any] | None,
    strategy: str | None,
) -> set[str]:
    if not input_row:
        return {"misrecognition", "context_insensitivity"}

    goal = str(input_row.get("interaction_goal", ""))
    platform = str(input_row.get("platform", ""))
    labels = {"misrecognition"}

    if (
        platform in {"academic_forum", "public_social_media", "community_forum"}
        or "professional" in goal
        or goal in {
            "stay_neutral",
            "respond_politely_without_overpraising",
            "deescalate_awkwardness",
        }
    ):
        labels.add("context_insensitivity")

    if strategy == "humor_tease" and goal in {"be_supportive", "be_supportive_without_overpraising"}:
        labels.add("strategy_inconsistency")

    return labels


def render_risk_assessment(labels: set[str]) -> str:
    selected = [label for label in RISK_RENDER_ORDER if label in labels][:3]
    if not selected:
        selected = ["misrecognition", "context_insensitivity"]

    parts = []
    if "misrecognition" in selected:
        parts.append("The main risk is misrecognition: the self-presentation could be misread.")
    if "context_insensitivity" in selected:
        parts.append("Context_insensitivity is possible if the reply ignores the audience or setting.")
    if "sycophancy" in selected:
        parts.append("Sycophancy could occur through overpraise or flattery.")
    if "preachiness" in selected:
        parts.append("Preachiness could make the reply feel moralizing.")
    if "strategy_inconsistency" in selected:
        parts.append("Strategy_inconsistency is a risk if the reply does not match the strategy or context.")
    if "over_coldness" in selected:
        parts.append("Over_coldness could make the reply too cold or dismissive.")
    return " ".join(parts)


def clean_response_text(value: Any, strategy: str) -> str:
    raw = compact_text(_extract_response_from_json(str(value or "")))
    cleaned = raw
    if (
        not cleaned
        or has_suspicious_text(cleaned)
        or "{" in cleaned
        or "}" in cleaned
        or "<think" in cleaned.lower()
    ):
        cleaned = DEFAULT_RESPONSE_BY_STRATEGY.get(strategy, DEFAULT_RESPONSE_BY_STRATEGY[DEFAULT_STRATEGY])
    if strategy in {"light_acknowledgment", "neutral_observation"} and contains_overpraise(cleaned):
        cleaned = DEFAULT_RESPONSE_BY_STRATEGY[strategy]
    return truncate_words(cleaned, MAX_WORDS["response_text"])


def clean_understanding(parsed: dict[str, Any] | None) -> dict[str, str]:
    parsed = parsed or {}
    speaker_intention = clean_field_text(
        parsed.get("speaker_intention"),
        DEFAULT_SPEAKER_INTENTION,
        MAX_WORDS["speaker_intention"],
    )
    desired_feedback = clean_field_text(
        parsed.get("desired_feedback"),
        DEFAULT_DESIRED_FEEDBACK,
        MAX_WORDS["desired_feedback"],
    )
    risk_assessment = ensure_risk_assessment(parsed.get("risk_assessment"))
    return {
        "speaker_intention": speaker_intention,
        "desired_feedback": desired_feedback,
        "risk_assessment": risk_assessment,
    }


def ensure_risk_assessment(value: Any) -> str:
    text = clean_field_text(value, DEFAULT_RISK_ASSESSMENT, MAX_WORDS["risk_assessment"])
    risk_keywords = _extract_risk_keywords(text)
    if not risk_keywords or len(risk_keywords) > 3:
        text = render_risk_assessment({"misrecognition", "context_insensitivity"})
    return truncate_words(text, MAX_WORDS["risk_assessment"])


def normalize_risk_assessment(
    value: Any,
    input_row: dict[str, Any] | None = None,
    strategy: str | None = None,
) -> str:
    labels = _infer_contextual_risk_labels(input_row, strategy)
    return truncate_words(render_risk_assessment(labels), MAX_WORDS["risk_assessment"])


def _stable_index(key: str, size: int) -> int:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % max(1, size)


def _infer_theme(input_row: dict[str, Any], mechanism: str) -> str:
    if mechanism == "comparison_superiority":
        return "superiority"
    if mechanism == "scarcity_flex":
        return "scarcity"

    post = str(input_row.get("speaker_post", "")).lower()
    scores = {
        theme: sum(1 for keyword in keywords if keyword in post)
        for theme, keywords in THEME_KEYWORDS.items()
    }
    best_theme, best_score = max(scores.items(), key=lambda item: item[1])
    return best_theme if best_score > 0 else "other"


def _infer_context(input_row: dict[str, Any]) -> str:
    platform = str(input_row.get("platform", ""))
    relationship = str(input_row.get("relationship", ""))
    goal = str(input_row.get("interaction_goal", ""))

    if platform in {"workplace_channel", "academic_forum"} or "professional" in goal:
        return "professional"
    if platform in CONSTRAINED_PLATFORMS or relationship in CONSTRAINED_RELATIONSHIPS:
        return "constrained"
    if relationship in WARM_RELATIONSHIPS and platform in {"direct_message", "private_chat", "group_chat"}:
        return "warm_private"
    if platform == "group_chat":
        return "peer_group"
    if platform in PUBLIC_PLATFORMS:
        return "public"
    return "neutral"


def _infer_tone(strategy: str, context: str) -> str:
    if context == "professional":
        return "professional"
    if strategy == "humor_tease":
        return "playful"
    if context == "warm_private":
        return "warm"
    return "neutral"


def _format_generalized_template(
    template: str,
    *,
    topic: str,
    mechanism_phrase: str,
    context_phrase: str,
    tone_phrase: str,
) -> str:
    return template.format(
        topic=topic,
        mechanism_phrase=mechanism_phrase,
        context_phrase=context_phrase,
        tone_phrase=tone_phrase,
    )


def abstract_response_fallback(strategy: str, mechanism: str, input_row: dict[str, Any]) -> str:
    if strategy == "no_response":
        return ""

    theme = _infer_theme(input_row, mechanism)
    context = _infer_context(input_row)
    tone = _infer_tone(strategy, context)
    topic = THEME_PHRASES.get(theme, THEME_PHRASES["other"])
    mechanism_phrase = MECHANISM_PHRASES.get(mechanism, MECHANISM_PHRASES["other"])
    context_phrase = CONTEXT_PHRASES.get(context, CONTEXT_PHRASES["neutral"])
    tone_phrase = TONE_PHRASES.get(tone, TONE_PHRASES["neutral"])

    if strategy == "humor_tease" and context in {"professional", "constrained", "public"}:
        choices = CONSTRAINED_HUMOR_TEMPLATES
    else:
        choices = GENERALIZED_TEMPLATE_BANK.get(
            strategy,
            GENERALIZED_TEMPLATE_BANK["light_acknowledgment"],
        )

    key = "|".join(
        (
            str(input_row.get("episode_id", "")),
            strategy,
            mechanism,
            theme,
            context,
            tone,
        )
    )
    template = choices[_stable_index(key, len(choices))]
    return _format_generalized_template(
        template,
        topic=topic,
        mechanism_phrase=mechanism_phrase,
        context_phrase=context_phrase,
        tone_phrase=tone_phrase,
    )


def safe_mechanism(text: Any, valid_labels: set[str]) -> str:
    return normalize_label(text, valid_labels, DEFAULT_MECHANISM)


def safe_strategy(text: Any, valid_labels: set[str]) -> str:
    return normalize_label(text, valid_labels, DEFAULT_STRATEGY)
