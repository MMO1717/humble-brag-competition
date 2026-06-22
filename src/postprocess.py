from __future__ import annotations

import json
import re
import hashlib
from typing import Any

from .schemas import (
    DEFAULT_MECHANISM,
    DEFAULT_RESPONSE_BY_STRATEGY,
    DEFAULT_STRATEGY,
    MAX_WORDS,
    OVERPRAISE_TERMS,
    RISK_LABELS,
    VALID_BRAGGING_MECHANISMS,
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

SELF_AWARE_MECHANISM_RE = re.compile(
    r"\b(not to brag|do not mean to brag|don't mean to brag|humblebrag|tiny brag|small brag|small flex)\b",
    re.I,
)
UNDERSTATED_CONTEXT_RE = re.compile(
    r"\b(no big deal|not a big deal|casual(?:ly)?|somehow|kind of|still kind of|"
    r"would be tasteless|felt weird to mention|forgot what it'?s like|"
    r"surprised this came up|didn'?t mean to make it a thing)\b",
    re.I,
)
UNDISCOVERED_TALENT_RE = re.compile(
    r"\b(talent(?:ed)?|skill(?:ed)?|ability)\b.{0,120}"
    r"\b(not exposed|not been exposed|ain'?t been exposed|undiscovered|unrecognized|"
    r"not noticed|not seen yet|waiting to be seen)\b|"
    r"\b(not exposed|not been exposed|ain'?t been exposed|undiscovered|unrecognized|"
    r"not noticed|not seen yet|waiting to be seen)\b.{0,120}"
    r"\b(talent(?:ed)?|skill(?:ed)?|ability)\b",
    re.I,
)
SCARCITY_MECHANISM_RE = re.compile(
    r"\b(invitation-only|invite-only|private preview|closed beta|limited access|restricted access|"
    r"rare access|direct access|only got one seat|one seat|private session|closed group|"
    r"backstage|vip|sang happy birthday|sing happy birthday|singing happy birthday|"
    r"private birthday surprise)\b",
    re.I,
)
STRONG_COMPLAINT_RE = re.compile(
    r"\b(tired|exhausted|barely rested|wish|annoying|too many|kept asking|"
    r"urgent requests?|more work|burden|hard to keep up|running out of|ugh|hate)\b",
    re.I,
)
POSITIVE_PAYOFF_RE = re.compile(
    r"\b(success|reliable|attention|asked|requests?|trusted|won|finished|"
    r"completed|promoted|accepted|published|sold|ahead|top|best|result|client|"
    r"grade|score|4\.0)\b",
    re.I,
)
SPECIFIC_COMPARISON_RE = re.compile(
    r"\b(true|real)\s+.{0,30}skill\b|"
    r"\byalls?\s+posts?\b|"
    r"\b(two|three|four|five)\s+of\s+(these|the)\s+exact\b|"
    r"\blooking\s+at\s+(other|some|your)\s+people'?s?\s+posts?\b",
    re.I,
)
DIRECT_PERSON_COMPARISON_RE = re.compile(
    r"\b(most people|other people|everyone else|some people|unlike most people)\b"
    r".{0,100}\b(i|i'm|i am|my|we|our)\b|"
    r"\b(i|i'm|i am|my|we|our)\b.{0,100}"
    r"\b(better|faster|smarter|stronger|more skilled|ahead of)\b.{0,50}"
    r"\b(people|others|them|coworkers|classmates|friends|peers)\b",
    re.I,
)
APOLOGETIC_MODESTY_RE = re.compile(
    r"\b(sorry(?: for|[, ]+such)?|i know this sounds|i'm no expert|"
    r"i am no expert|not sure how)\b",
    re.I,
)
GRATITUDE_CONTRAST_RE = re.compile(
    r"\b(blessed|grateful|thankful|appreciate)\b.{0,180}"
    r"\b(rare|instead of|other people|others|popular|trending|narrative)\b|"
    r"\b(rare|instead of|other people|others|popular|trending|narrative)\b"
    r".{0,180}\b(blessed|grateful|thankful|appreciate)\b",
    re.I,
)
POSITIVE_CLAIM_RE = re.compile(
    r"\b(happy|positive|proud|best|top|won|finished|score|grade|pb|pbs|"
    r"accepted|promoted|template|rare|constructive|facts|help|asked)\b",
    re.I,
)
ADVERSITY_RE = re.compile(
    r"\b(despite|shit show|rough year|chaos|lockdown|injury troubles|"
    r"pandemic|barely any support|moving countries)\b",
    re.I,
)
CONCRETE_ACHIEVEMENT_RE = re.compile(
    r"\b(got|won|landed|earned|sold|scored|ranked|accepted|promoted|"
    r"selected|featured|funded|closed|hit|made|finished|completed|"
    r"published|received|crushed|qualified|passed|graduated|ran)\b|"
    r"\b(award|promotion|raise|quota|leaderboard|dean'?s list|"
    r"downloads?|marathons?|certification|presentation|publication|"
    r"stats?|tackles?|interceptions?|grades?|score|4\.0|top \d|"
    r"\d+(?:\.\d+)?%|\d+\s+(cars?|wins?|pbs?|deals?))\b|"
    r"\bi was there when\b",
    re.I,
)
INCIDENTAL_RECOGNITION_RE = re.compile(
    r"\b(forgot what it'?s like|didn'?t realize|did not realize|apparently|"
    r"somehow|ended up)\b.{0,220}"
    r"\b(asked me|asking me|people keep|everyone|manager|team|audience|"
    r"shocked|telling me|used my|became the template)\b",
    re.I,
)

MECHANISM_CONFUSION_PAIRS = {
    frozenset(("understated_flex", "achievement_drop")),
    frozenset(("faux_modesty", "understated_flex")),
    frozenset(("faux_modesty", "humble_complaint")),
    frozenset(("humble_complaint", "achievement_drop")),
    frozenset(("scarcity_flex", "achievement_drop")),
    frozenset(("comparison_superiority", "understated_flex")),
    frozenset(("self_aware_brag", "comparison_superiority")),
}

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
    # Only do substring/boundary matching if text is short (likely a direct label).
    # Long text (e.g. thinking output) may mention multiple labels ambiguously.
    is_short = len(raw) <= 80
    if is_short:
        for label in valid_labels:
            if label in raw:
                return label
            if re.search(rf"\b{re.escape(label)}\b", raw):
                return label
    return default


def normalize_mechanism_post(value: Any) -> str:
    """生成只依赖原文的机制缓存键。"""
    return re.sub(r"\s+", " ", compact_text(value).lower()).strip()


def parse_mechanism_classification(raw: Any) -> dict[str, Any]:
    """解析结构化机制结果；旧式单标签输出会安全降级为低置信结果。"""
    parsed = parse_json_object(str(raw or ""))
    if parsed:
        label = safe_mechanism(
            parsed.get("label"),
            VALID_BRAGGING_MECHANISMS,
        )
        runner_up = safe_mechanism(
            parsed.get("runner_up"),
            VALID_BRAGGING_MECHANISMS,
        )
        confidence = str(parsed.get("confidence", "low")).strip().lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"
        cue_codes = parsed.get("cue_codes", [])
        if not isinstance(cue_codes, list):
            cue_codes = [cue_codes]
        cue_codes = [
            compact_text(value)[:64]
            for value in cue_codes
            if compact_text(value)
        ][:8]
        structured = True
    else:
        label = safe_mechanism(raw, VALID_BRAGGING_MECHANISMS)
        runner_up = DEFAULT_MECHANISM
        confidence = "low"
        cue_codes = ["legacy_or_invalid_output"]
        structured = False

    if runner_up == label:
        runner_up = DEFAULT_MECHANISM
    if label == DEFAULT_MECHANISM and runner_up == DEFAULT_MECHANISM:
        runner_up = "understated_flex"
    return {
        "label": label,
        "runner_up": runner_up,
        "confidence": confidence,
        "cue_codes": cue_codes,
        "structured": structured,
    }


def parse_mechanism_review(
    raw: Any,
    candidate_a: str,
    candidate_b: str,
) -> dict[str, Any]:
    """解析二选一复核，并兼容模型返回 candidate_a/candidate_b。"""
    parsed = parse_json_object(str(raw or "")) or {}
    aliases = {
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
    }
    raw_label = str(parsed.get("label", "")).strip()
    raw_runner_up = str(parsed.get("runner_up", "")).strip()
    if raw_label in aliases:
        parsed["label"] = aliases[raw_label]
    if raw_runner_up in aliases:
        parsed["runner_up"] = aliases[raw_runner_up]
    return parse_mechanism_classification(
        json.dumps(parsed, ensure_ascii=False) if parsed else raw
    )


def assess_mechanism_rules(
    input_row: dict[str, Any],
    predicted: str,
) -> dict[str, Any]:
    """返回高精度规则建议和中置信混淆提示。"""
    post = compact_text(input_row.get("speaker_post", ""))
    evidence: list[str] = []
    suggested = predicted
    strength = "none"
    override_allowed = False

    def choose(
        label: str,
        code: str,
        level: str = "high",
        allowed_initial: set[str] | None = None,
    ) -> None:
        nonlocal suggested, strength, override_allowed
        suggested = label
        strength = level
        override_allowed = (
            allowed_initial is None
            or predicted in allowed_initial
        )
        evidence.append(code)

    if SELF_AWARE_MECHANISM_RE.search(post):
        choose("self_aware_brag", "explicit_self_aware_brag")
    elif (
        predicted == "self_aware_brag"
        and UNDERSTATED_CONTEXT_RE.search(post)
    ):
        choose(
            "understated_flex",
            "low_key_context_without_explicit_brag_label",
            allowed_initial={"self_aware_brag", "achievement_drop", "other"},
        )
    elif UNDISCOVERED_TALENT_RE.search(post):
        choose(
            "understated_flex",
            "undiscovered_talent_framing",
            allowed_initial={
                "achievement_drop",
                "faux_modesty",
                "humble_complaint",
                "understated_flex",
            },
        )
    elif SCARCITY_MECHANISM_RE.search(post) and not STRONG_COMPLAINT_RE.search(post):
        choose("scarcity_flex", "explicit_scarce_access")
    elif SPECIFIC_COMPARISON_RE.search(post) or DIRECT_PERSON_COMPARISON_RE.search(post):
        choose(
            "comparison_superiority",
            "speaker_elevating_comparison",
            allowed_initial={
                "other",
                "achievement_drop",
                "understated_flex",
                "faux_modesty",
                "humble_complaint",
                "scarcity_flex",
                "comparison_superiority",
            },
        )
    elif (
        STRONG_COMPLAINT_RE.search(post)
        and POSITIVE_PAYOFF_RE.search(post)
    ):
        choose(
            "humble_complaint",
            "complaint_carries_payoff",
            allowed_initial={
                "achievement_drop",
                "understated_flex",
                "faux_modesty",
                "humble_complaint",
            },
        )
    elif (
        ADVERSITY_RE.search(post)
        and (
            POSITIVE_PAYOFF_RE.search(post)
            or CONCRETE_ACHIEVEMENT_RE.search(post)
        )
    ):
        choose(
            "humble_complaint",
            "adversity_plus_payoff",
            "medium",
            allowed_initial={
                "achievement_drop",
                "understated_flex",
                "faux_modesty",
                "humble_complaint",
            },
        )
    elif (
        APOLOGETIC_MODESTY_RE.search(post)
        and POSITIVE_CLAIM_RE.search(post)
        and not SELF_AWARE_MECHANISM_RE.search(post)
    ) or (
        GRATITUDE_CONTRAST_RE.search(post)
        and not CONCRETE_ACHIEVEMENT_RE.search(post)
    ):
        choose(
            "faux_modesty",
            "modesty_wrapper_around_positive_claim",
            allowed_initial={
                "other",
                "achievement_drop",
                "understated_flex",
                "humble_complaint",
                "faux_modesty",
            },
        )
    elif INCIDENTAL_RECOGNITION_RE.search(post):
        choose(
            "understated_flex",
            "incidental_third_party_recognition",
            allowed_initial={
                "achievement_drop",
                "comparison_superiority",
                "humble_complaint",
                "understated_flex",
            },
        )
    elif predicted == "achievement_drop" and not CONCRETE_ACHIEVEMENT_RE.search(post):
        choose("understated_flex", "no_concrete_completed_achievement", "medium")

    return {
        "suggested_label": suggested,
        "strength": strength,
        "evidence": evidence,
        "conflict": suggested != predicted,
        "override_allowed": override_allowed,
    }


def mechanism_review_reason(
    classification: dict[str, Any],
    rule_assessment: dict[str, Any],
) -> list[str]:
    """判断是否需要执行一次短机制复核。"""
    reasons: list[str] = []
    label = classification["label"]
    runner_up = classification["runner_up"]
    confidence = classification["confidence"]
    if label == DEFAULT_MECHANISM:
        reasons.append("initial_other")
    if confidence == "low":
        reasons.append("low_confidence")
    if (
        confidence == "medium"
        and frozenset((label, runner_up)) in MECHANISM_CONFUSION_PAIRS
    ):
        reasons.append("medium_confusion_pair")
    if (
        rule_assessment["conflict"]
        and rule_assessment["override_allowed"]
    ):
        reasons.append(
            f"rule_conflict:{rule_assessment['suggested_label']}"
        )
    return reasons


def calibrate_mechanism_with_evidence(
    input_row: dict[str, Any],
    predicted: str,
    memory_snippets: list[dict[str, Any]] | None = None,
    *,
    runner_up: str = DEFAULT_MECHANISM,
    model_confidence: str = "medium",
    review_label: str | None = None,
    review_confidence: str | None = None,
    review_reason: list[str] | None = None,
) -> dict[str, Any]:
    """融合模型、规则和可选复核结果，返回可审计的最终标签。"""
    del memory_snippets
    rule = assess_mechanism_rules(input_row, predicted)
    final = predicted
    decision = "model_accept"

    if (
        rule["strength"] == "high"
        and rule["conflict"]
        and rule["override_allowed"]
    ):
        final = rule["suggested_label"]
        decision = "rule_override"
    elif review_label in VALID_BRAGGING_MECHANISMS:
        final = str(review_label)
        decision = (
            "review_confirm"
            if final == predicted
            else "review_override"
        )

    return {
        "label": final,
        "initial_label": predicted,
        "runner_up": runner_up,
        "model_confidence": model_confidence,
        "review_label": review_label,
        "review_confidence": review_confidence,
        "review_reason": review_reason or [],
        "changed": final != predicted,
        "decision": decision,
        "rule_suggestion": rule["suggested_label"],
        "rule_strength": rule["strength"],
        "evidence": rule["evidence"],
        "memory_evidence": [],
    }


def has_suspicious_text(text: str) -> bool:
    return any(pattern.search(text) for pattern in SUSPICIOUS_PATTERNS)


_REASONING_LEAK_PATTERNS = [
    "post content:",
    "key elements:",
    "analysis:",
    "reasoning:",
    "bragging mechanism",
    "speaker intention",
    "desired feedback",
    "risk assessment",
    "response strategy",
    "the speaker is",
    "the user wants",
    "the user is",
    "constraint 1:",
    "constraint 2:",
    "*   input",
    "*   post",
    "*   the",
]


def contains_reasoning_leak(text: str) -> bool:
    """Detect if text contains thinking/analysis artifacts that should not be in final output."""
    if not isinstance(text, str):
        return False
    lower = text.lower()
    return any(pattern in lower for pattern in _REASONING_LEAK_PATTERNS)


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


def infer_contextual_risk_labels(
    input_row: dict[str, Any] | None,
    strategy: str | None,
    mechanism: str | None = None,
) -> set[str]:
    if not input_row:
        return {"misrecognition", "context_insensitivity"}

    goal = str(input_row.get("interaction_goal", ""))
    platform = str(input_row.get("platform", ""))
    relationship = str(input_row.get("relationship", ""))
    strategy = str(strategy or "")
    mechanism = str(mechanism or "")
    labels = {"misrecognition"}

    formal_or_distant = (
        platform in {"academic_forum", "workplace_channel"}
        or relationship in {"stranger", "supervisor"}
        or "professional" in goal
        or goal == "stay_neutral"
    )
    public_sensitive = (
        platform in {"public_social_media", "community_forum"}
        and (
            relationship in {"stranger", "online_peer"}
            or mechanism in {"comparison_superiority", "faux_modesty"}
            or strategy in {"redirect", "neutral_observation"}
        )
    )
    group_mismatch = (
        platform == "group_chat"
        and (
            relationship in {"coworker", "acquaintance"}
            or strategy in {"redirect", "neutral_observation", "validate"}
            or "professional" in goal
        )
    )
    if formal_or_distant or public_sensitive or group_mismatch:
        labels.add("context_insensitivity")

    if (
        "avoid_sycophancy" in goal
        or (
            mechanism == "understated_flex"
            and strategy in {"validate", "neutral_observation", "ask_followup"}
            and goal in {
                "be_supportive_without_overpraising",
                "respond_politely_without_overpraising",
            }
        )
    ):
        labels.add("sycophancy")

    if (
        strategy == "humor_tease"
        and goal in {"be_supportive", "be_supportive_without_overpraising"}
        and relationship not in {"close_friend", "friend"}
    ) or (
        strategy == "validate"
        and goal == "be_supportive_without_overpraising"
        and mechanism == "understated_flex"
    ):
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
        or contains_reasoning_leak(cleaned)
        or "{" in cleaned
        or "}" in cleaned
        or "<think" in cleaned.lower()
    ):
        cleaned = DEFAULT_RESPONSE_BY_STRATEGY.get(strategy, DEFAULT_RESPONSE_BY_STRATEGY[DEFAULT_STRATEGY])
    if strategy in {"light_acknowledgment", "neutral_observation"} and contains_overpraise(cleaned):
        cleaned = DEFAULT_RESPONSE_BY_STRATEGY[strategy]
    return truncate_words(cleaned, MAX_WORDS["response_text"])


def has_valid_risk_assessment(value: Any) -> bool:
    text = compact_text(value)
    labels = _extract_risk_keywords(text)
    return bool(text) and 1 <= len(labels) <= 3 and word_count(text) <= MAX_WORDS["risk_assessment"]


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
    return template.format(
        topic=topic,
        mechanism_phrase=mechanism_phrase,
        context_phrase=context_phrase,
        tone_phrase=tone_phrase,
    )


def safe_mechanism(text: Any, valid_labels: set[str]) -> str:
    return normalize_label(text, valid_labels, DEFAULT_MECHANISM)


def safe_strategy(text: Any, valid_labels: set[str]) -> str:
    return normalize_label(text, valid_labels, DEFAULT_STRATEGY)
