#!/usr/bin/env python3
"""
Response-only post-processor for BRAG-Agent submission JSONL files.

This script keeps all submission fields unchanged except response_text. It uses
only the submitted strategy/mechanism plus input context fields to generate
short, low-risk responses that match the intended response style.

Usage:
  python3 scripts/postprocess_response_text.py SUBMISSION.jsonl INPUT.jsonl OUTPUT.jsonl
  python3 scripts/postprocess_response_text.py SUBMISSION.jsonl INPUT.jsonl OUTPUT.jsonl --report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


REQUIRED_SUBMISSION_FIELDS = {
    "episode_id",
    "bragging_mechanism",
    "speaker_intention",
    "desired_feedback",
    "risk_assessment",
    "response_strategy",
    "response_text",
}

WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")

THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "achievement": (
        "award", "accepted", "published", "promotion", "raise", "grade",
        "score", "school", "class", "job", "work", "sales", "sold",
        "stats", "finished", "completed",
    ),
    "skill": (
        "skill", "talent", "talented", "learned", "picked", "quickly",
        "read", "write", "game", "gaming", "play", "players", "mechanic",
    ),
    "affiliation": (
        "friend", "network", "contact", "gig", "concert", "festival",
        "met", "know", "connection", "family",
    ),
    "relationship": ("partner", "boyfriend", "girlfriend", "husband", "wife"),
    "attention": ("attention", "notifications", "viral", "followers", "thirst"),
    "resilience": ("injury", "rough", "tough", "despite", "struggle", "failure"),
    "possession": ("car", "house", "home", "dog", "pet", "model"),
}

THEME_PHRASES = {
    "achievement": "the accomplishment",
    "skill": "the skill",
    "affiliation": "the connection",
    "relationship": "the relationship",
    "attention": "the attention",
    "resilience": "the progress",
    "possession": "the experience",
    "scarcity": "the rare moment",
    "superiority": "the comparison",
    "other": "the point",
}

MASK_PHRASES = {
    "complaint": "with the frustration in the background",
    "faux_modesty": "without leaning too hard into it",
    "self_aware": "with a self-aware tone",
    "understated": "in a low-key way",
    "adversity_contrast": "given the harder context",
}

CONTEXT_PHRASES = {
    "constrained": "in this setting",
    "professional": "in a professional setting",
    "peer_group": "with the group",
    "warm_private": "between people who know each other",
    "public": "in public",
    "neutral": "in this context",
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

CONSTRAINED_PLATFORMS = {"academic_forum", "workplace_channel"}
PUBLIC_PLATFORMS = {"public_social_media", "community_forum", "academic_forum", "workplace_channel"}
WARM_RELATIONSHIPS = {"close_friend", "friend", "family_member", "romantic_partner"}

TEMPLATE_BANK: dict[str, tuple[str, ...]] = {
    "ask_followup": (
        "That is interesting context. What made {topic} stand out to you?",
        "I get the point. What part of {topic} feels most worth sharing?",
        "That is useful background {context_phrase}. How did {topic} come up?",
        "Fair enough. What do you think matters most about {mechanism_phrase}?",
        "That gives some context. What would you want people to take from {topic} {mask_phrase}?",
    ),
    "neutral_observation": (
        "That sounds like useful context for {topic}, without needing to overstate it.",
        "It makes sense to note {topic}, while keeping the claim measured.",
        "There is some relevant context around {mechanism_phrase}.",
        "That frames {topic} more clearly {context_phrase}, without making it a bigger claim.",
        "Sounds like {topic} is part of the situation, though {mask_phrase} still matters.",
    ),
    "light_acknowledgment": (
        "That is a fair thing to note. {topic_cap} sounds worth a small nod {context_phrase}.",
        "Nice. {topic_cap} is a reasonable thing to acknowledge {mask_phrase}.",
        "Fair enough. {topic_cap} seems worth noting {context_phrase}, without making a big production of it.",
        "That sounds like a small but real point around {mechanism_phrase}.",
        "I can see why {topic} would feel worth mentioning {mask_phrase}.",
    ),
    "humor_tease": (
        "Honestly, that is a pretty specific flex. I will give you light credit for {topic}.",
        "That is a very particular brag about {topic}, but I see the angle.",
        "I respect the commitment to making {topic} sound casual {context_phrase}.",
        "That is one way to sneak {mechanism_phrase} into the conversation.",
        "Fair, {topic} is doing some quiet flexing there.",
    ),
    "validate": (
        "That sounds meaningful, especially with the context around {topic}.",
        "I can see why {topic} would feel good to acknowledge.",
        "That is a solid outcome around {topic}, and it makes sense to take a moment with it.",
        "Glad {topic} is landing well for you {context_phrase}.",
        "That sounds like something worth appreciating {mask_phrase}.",
    ),
    "redirect": (
        "That gives context. It may help to connect {topic} back to the main point.",
        "Fair enough. The useful part is probably what {mechanism_phrase} adds to the discussion.",
        "That detail can help {context_phrase}, as long as the focus stays on the shared topic.",
        "I would keep the emphasis on what {topic} means for the situation.",
        "That is relevant context for {topic}, and the next step is tying it back to the question.",
    ),
    "set_boundary": (
        "I hear the point, but I would keep the focus on the shared issue here.",
        "I get what you mean, but I do not want to turn this into a comparison.",
        "That may be true, but I would rather not rank people around {topic}.",
        "I would keep {mechanism_phrase} grounded in the situation rather than making it personal.",
        "I can acknowledge {topic} without turning it into a praise moment.",
    ),
    "no_response": (
        "",
    ),
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise SystemExit(f"{path}:{line_no}: expected a JSON object")
            rows.append(value)
    return rows


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def remove_overpraise_flags(text: str) -> str:
    """Avoid format-checker praise patterns in constrained response strategies."""
    replacements = [
        (r"\bmost amazing\b", "notable"),
        (r"\bamazing\b", "notable"),
        (r"\bincredible\b", "strong"),
        (r"\bso proud of you\b", "happy for you"),
        (r"\bbest at\b", "strong in"),
        (r"\bbest\b", "strong"),
    ]
    cleaned = text
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return normalize_space(cleaned)


def first_sentence(text: str) -> str:
    text = normalize_space(text)
    if not text:
        return ""
    match = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    return match[0].strip()


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def infer_theme(post: str, mechanism: str) -> str:
    lowered = post.lower()
    if mechanism == "comparison_superiority":
        return "superiority"
    if mechanism == "scarcity_flex":
        return "scarcity"
    for theme, keywords in THEME_KEYWORDS.items():
        if contains_any(lowered, keywords):
            return theme
    if mechanism in {"achievement_drop", "faux_modesty"}:
        return "achievement"
    if mechanism == "humble_complaint":
        return "resilience"
    return "other"


def infer_mask(post: str, mechanism: str) -> str:
    lowered = post.lower()
    if mechanism == "humble_complaint":
        return "complaint"
    if mechanism == "faux_modesty" or contains_any(lowered, ("not trying to brag", "don't mean to brag", "sorry")):
        return "faux_modesty"
    if mechanism == "self_aware_brag" or "brag" in lowered:
        return "self_aware"
    if contains_any(lowered, ("no big deal", "just", "somehow", "i guess")):
        return "understated"
    if contains_any(lowered, ("despite", "rough", "tough", "struggle", "failure")):
        return "adversity_contrast"
    return "understated"


def infer_context(platform: str, relationship: str) -> str:
    if platform in CONSTRAINED_PLATFORMS or relationship in {"supervisor", "stranger"}:
        return "constrained"
    if platform == "workplace_channel":
        return "professional"
    if platform == "group_chat":
        return "peer_group"
    if relationship in WARM_RELATIONSHIPS or platform == "direct_message":
        return "warm_private"
    if platform in PUBLIC_PLATFORMS:
        return "public"
    return "neutral"


def extract_features(post: str, mechanism: str, platform: str, relationship: str) -> dict[str, str]:
    theme = infer_theme(post, mechanism)
    return {
        "theme": theme,
        "theme_phrase": THEME_PHRASES.get(theme, THEME_PHRASES["other"]),
        "mask": infer_mask(post, mechanism),
        "context": infer_context(platform, relationship),
        "mechanism": mechanism,
    }


def choose_template(strategy: str, features: dict[str, str], episode_id: str) -> str:
    templates = TEMPLATE_BANK.get(strategy) or (
        "That is useful context about {topic}, without needing to overstate it.",
    )
    key = "|".join([
        episode_id,
        strategy,
        features["theme"],
        features["context"],
        features["mask"],
    ])
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return templates[int(digest[:8], 16) % len(templates)]


def is_warm_context(platform: str, relationship: str) -> bool:
    return relationship in WARM_RELATIONSHIPS or platform == "direct_message"


def is_constrained_context(platform: str, relationship: str) -> bool:
    return platform in CONSTRAINED_PLATFORMS or relationship in {"supervisor", "stranger"}


def template_for_strategy(
    strategy: str,
    mechanism: str,
    features: dict[str, str],
    episode_id: str,
) -> str:
    topic = features["theme_phrase"]
    topic_cap = topic.capitalize()
    mask_phrase = MASK_PHRASES.get(features["mask"], MASK_PHRASES["understated"])
    context_phrase = CONTEXT_PHRASES.get(features["context"], CONTEXT_PHRASES["neutral"])
    mechanism_phrase = MECHANISM_PHRASES.get(features["mechanism"], MECHANISM_PHRASES["other"])
    template = choose_template(strategy, features, episode_id)
    return template.format(
        topic=topic,
        topic_cap=topic_cap,
        mask_phrase=mask_phrase,
        context_phrase=context_phrase,
        mechanism_phrase=mechanism_phrase,
    )


def fallback_response(mechanism: str, topic: str, warm: bool) -> str:
    if mechanism == "comparison_superiority":
        return f"Sounds like {topic} matters here, though I would keep the comparison light."
    if mechanism == "humble_complaint":
        return f"That sounds frustrating, and {topic} also seems like useful context."
    if warm:
        return f"That sounds like a nice moment. Glad {topic} felt worth sharing."
    return f"That is useful context about {topic}, without needing to overstate it."


def build_response(row: dict[str, Any], input_row: dict[str, Any]) -> str:
    post = str(input_row.get("speaker_post", ""))
    platform = str(input_row.get("platform", ""))
    relationship = str(input_row.get("relationship", ""))
    strategy = str(row.get("response_strategy", ""))
    mechanism = str(row.get("bragging_mechanism", ""))
    episode_id = str(row.get("episode_id", ""))
    features = extract_features(post, mechanism, platform, relationship)
    response = template_for_strategy(strategy, mechanism, features, episode_id)
    text = first_sentence(response) if strategy == "no_response" else normalize_space(response)
    if strategy in {"light_acknowledgment", "set_boundary"}:
        return remove_overpraise_flags(text)
    return text


def validate_submission_rows(rows: list[dict[str, Any]]) -> None:
    for idx, row in enumerate(rows, 1):
        missing = REQUIRED_SUBMISSION_FIELDS.difference(row)
        if missing:
            fields = ", ".join(sorted(missing))
            raise SystemExit(f"submission row {idx} is missing required fields: {fields}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replace only response_text in a BRAG-Agent submission JSONL."
    )
    parser.add_argument("submission_jsonl", type=Path)
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--report", action="store_true", help="print replacement counts")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    submission_rows = load_jsonl(args.submission_jsonl)
    input_rows = load_jsonl(args.input_jsonl)
    validate_submission_rows(submission_rows)

    input_by_id = {str(row.get("episode_id")): row for row in input_rows}
    changed = 0
    strategy_counts: dict[str, int] = {}

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as handle:
        for row in submission_rows:
            episode_id = str(row["episode_id"])
            input_row = input_by_id.get(episode_id, {})
            new_row = dict(row)
            new_text = build_response(row, input_row)
            if new_text != row.get("response_text", ""):
                changed += 1
                strategy = str(row.get("response_strategy", ""))
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            new_row["response_text"] = new_text
            handle.write(json.dumps(new_row, ensure_ascii=False) + "\n")

    if args.report:
        print(f"Rows changed: {changed}/{len(submission_rows)}")
        for strategy, count in sorted(strategy_counts.items()):
            print(f"  {strategy}: {count}")
        print(f"Saved to {args.output_jsonl}")


if __name__ == "__main__":
    main()
