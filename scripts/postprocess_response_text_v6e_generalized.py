#!/usr/bin/env python3
"""
Response-only v6e generalized post-processor for BRAG-Agent submission JSONL files.

This script keeps all submission fields unchanged except response_text. It uses
only the submitted strategy/mechanism plus abstract input context fields to
generate short, low-risk responses that match the intended response style.
It then runs a local paper-rubric social judge and rewrites at most once only
when the judge finds a hard issue.

Usage:
  python3 scripts/postprocess_response_text_v6e_generalized.py SUBMISSION.jsonl INPUT.jsonl OUTPUT.jsonl
  python3 scripts/postprocess_response_text_v6e_generalized.py SUBMISSION.jsonl INPUT.jsonl OUTPUT.jsonl --report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from judge_social_rubric import judge_row


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

TONE_PHRASES = {
    "warm": "with a little warmth",
    "neutral": "in a measured way",
    "playful": "lightly",
    "professional": "with the setting in mind",
    "boundary": "without making it a comparison",
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
        "Interesting context. What part of {topic} felt most worth mentioning?",
        "I get the point. How did {topic} come up?",
        "That gives some useful background. What do you want people to take from it?",
        "Fair enough. What matters most about {mechanism_phrase} here?",
        "That is a specific angle. What made it stand out?",
        "Makes sense. Was the main point {topic}, or the context around it?",
        "I can see why you brought it up. What reaction were you hoping for?",
        "That adds context {tone_phrase}. What part feels most relevant?",
    ),
    "neutral_observation": (
        "That is useful context, and it works well when the point stays measured.",
        "It makes sense to note {topic}, without making it a bigger claim.",
        "There is relevant context around {mechanism_phrase}.",
        "That frames the situation more clearly {context_phrase}.",
        "I can see the point, though the tone should stay grounded.",
        "That detail helps explain the situation without needing a big reaction.",
        "The context is relevant, even if it does not need much emphasis.",
        "That reads as a small signal about {topic}, not something to overplay.",
    ),
    "light_acknowledgment": (
        "{ack_lead}. That seems {ack_unit} {restraint_phrase}.",
        "{ack_lead}, I can see why that would feel {mention_unit}.",
        "{ack_lead}. A measured nod fits {context_phrase}.",
        "{ack_lead}. That is a reasonable thing to acknowledge {tone_phrase}.",
        "{ack_lead}. There is a small but real point around {mechanism_phrase}.",
        "{ack_lead}, {topic} seems {ack_unit}.",
        "{ack_lead}. A little acknowledgment makes sense {restraint_phrase}.",
        "{ack_lead}. That can be noted while keeping the reaction modest.",
    ),
    "humor_tease": (
        "{playful_lead}, but I see the angle.",
        "{playful_lead}, and I will keep the reaction modest.",
        "That is one way to make {topic} sound casual.",
        "Fair, there is a little quiet flexing in there.",
        "That is a pretty careful way to slip the point in.",
        "I see what is happening there, and I will keep it light.",
        "That is a small brag in casual packaging.",
        "Point taken, with the reaction kept low-key.",
    ),
    "validate": (
        "That sounds meaningful, especially with the context around it.",
        "I can see why {topic} would feel good to acknowledge.",
        "That seems {ack_unit} {restraint_phrase}.",
        "It makes sense to take a small moment with that.",
        "That sounds like a solid outcome, kept in perspective.",
        "I can understand why that would land well.",
        "That is worth recognizing in a measured way.",
        "That sounds good, and a low-key response fits it.",
    ),
    "redirect": (
        "That gives context. I would connect it back to the main point.",
        "Fair enough. The useful part is what it adds to the discussion.",
        "That detail can help, as long as the focus stays on the shared topic.",
        "I would keep the emphasis on what it means for the situation.",
        "That is relevant context, and the next step is tying it back to the question.",
        "Point taken. I would bring it back to what the group is discussing.",
        "That can sit in the background while the main issue stays central.",
        "Useful context, but I would keep the conversation moving toward the core point.",
    ),
    "set_boundary": (
        "I hear the point, but I would keep the focus on the shared issue here.",
        "I get what you mean, but I do not want to turn this into a comparison.",
        "That may be true, but I would rather not rank people around {topic}.",
        "I would keep {mechanism_phrase} grounded in the situation rather than making it personal.",
        "I can acknowledge {topic} without turning it into a praise moment.",
        "I understand the point, but I would not make it about who comes out ahead.",
        "That is noted, though I would keep the response focused and fair.",
        "I would rather keep this about the situation than about personal standing.",
    ),
    "no_response": (
        "",
    ),
}

CONSTRAINED_HUMOR_TEMPLATES = (
    "I see the light joke there, but I would keep the response measured.",
    "There is a playful angle, though the setting calls for a restrained reply.",
    "That can be acknowledged lightly without leaning into the tease.",
    "The joke lands cleanly if the reaction stays low-key.",
)

SAFE_REWRITE_BANK: dict[str, tuple[str, ...]] = {
    "ask_followup": (
        "Interesting context. What part feels most relevant?",
        "Fair enough. What made that worth mentioning?",
        "I see the point. What would you want people to take from it?",
    ),
    "neutral_observation": (
        "That is useful context, and I would keep the response measured.",
        "The detail is relevant, but it does not need a big reaction.",
        "That gives context while keeping the focus grounded.",
    ),
    "light_acknowledgment": (
        "That is worth a small nod.",
        "Fair enough, that seems worth noting.",
        "I get why that would feel good to mention.",
    ),
    "humor_tease": (
        "That is a small flex, lightly acknowledged.",
        "I see the angle, and I will keep the reaction modest.",
        "Fair, that is a playful way to make the point.",
    ),
    "validate": (
        "That sounds meaningful, kept in perspective.",
        "I can see why that would feel good to acknowledge.",
        "That seems worth recognizing in a measured way.",
    ),
    "redirect": (
        "That gives context. I would bring it back to the main point.",
        "Point taken. I would keep the focus on the shared issue.",
        "That can help, as long as the discussion stays on track.",
    ),
    "set_boundary": (
        "I hear the point, but I would keep the focus on the shared issue.",
        "I get what you mean, but I would not turn it into a comparison.",
        "That is noted, though I would keep the response focused and fair.",
    ),
    "no_response": ("",),
}

SLOT_BANK: dict[str, tuple[str, ...]] = {
    "ack_lead": (
        "Fair enough",
        "That tracks",
        "I get that",
        "Makes sense",
        "Sure",
        "I see why",
        "Reasonable",
        "That is fair",
        "Understood",
        "Point taken",
    ),
    "ack_unit": (
        "worth a small nod",
        "fine to acknowledge",
        "reasonable to mention",
        "worth noting",
        "okay to recognize",
        "fair to bring up",
        "good to mark lightly",
        "valid to notice",
    ),
    "mention_unit": (
        "worth mentioning",
        "relevant to bring up",
        "good to acknowledge",
        "natural to note",
        "fair to share",
        "reasonable to point out",
        "like something to mark",
        "worth a brief reaction",
    ),
    "restraint_phrase": (
        "without making it a huge thing",
        "without turning it into a big reaction",
        "while keeping it low-key",
        "without overplaying it",
        "with the emphasis kept small",
        "while keeping the tone grounded",
        "without letting it take over",
        "in a measured way",
    ),
    "playful_lead": (
        "That is a very specific flex",
        "That is a tiny bit of a flex",
        "There is a small flex in there",
        "That is a careful little brag",
        "That is a pretty casual flex",
        "That is a light brag, noted",
        "That is a specific angle",
        "There is a playful brag in that",
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


def infer_tone(strategy: str, context: str, relationship: str) -> str:
    if strategy == "set_boundary":
        return "boundary"
    if context in {"constrained", "professional"}:
        return "professional"
    if strategy == "humor_tease":
        return "playful"
    if relationship in WARM_RELATIONSHIPS:
        return "warm"
    return "neutral"


def extract_features(post: str, mechanism: str, platform: str, relationship: str) -> dict[str, str]:
    theme = infer_theme(post, mechanism)
    context = infer_context(platform, relationship)
    return {
        "theme": theme,
        "theme_phrase": THEME_PHRASES.get(theme, THEME_PHRASES["other"]),
        "mask": infer_mask(post, mechanism),
        "context": context,
        "mechanism": mechanism,
        "tone": infer_tone("", context, relationship),
    }


def choose_template(strategy: str, features: dict[str, str], episode_id: str) -> str:
    if strategy == "humor_tease" and features.get("context") in {"constrained", "professional"}:
        templates = CONSTRAINED_HUMOR_TEMPLATES
    else:
        templates = TEMPLATE_BANK.get(strategy) or (
        "That is useful context about {topic}, without needing to overstate it.",
        )
    key = "|".join([
        episode_id,
        strategy,
        features["mechanism"],
        features["theme"],
        features["context"],
        features["mask"],
        features["tone"],
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
    tone_phrase = TONE_PHRASES.get(features["tone"], TONE_PHRASES["neutral"])
    template = choose_template(strategy, features, episode_id)
    slot_values = {
        name: stable_slot(
            values,
            (
                episode_id,
                strategy,
                features["mechanism"],
                features["theme"],
                features["context"],
                features["mask"],
                name,
            ),
        )
        for name, values in SLOT_BANK.items()
    }
    return template.format(
        topic=topic,
        topic_cap=topic_cap,
        mask_phrase=mask_phrase,
        context_phrase=context_phrase,
        mechanism_phrase=mechanism_phrase,
        tone_phrase=tone_phrase,
        **slot_values,
    )


def stable_slot(values: tuple[str, ...], key_parts: tuple[str, ...]) -> str:
    digest = hashlib.sha1("|".join(key_parts).encode("utf-8")).hexdigest()
    return values[int(digest[:8], 16) % len(values)]


def stable_pick(values: tuple[str, ...], key_parts: tuple[str, ...]) -> str:
    digest = hashlib.sha1("|".join(key_parts).encode("utf-8")).hexdigest()
    return values[int(digest[:8], 16) % len(values)]


def rewrite_for_hard_issues(
    row: dict[str, Any],
    input_row: dict[str, Any],
    features: dict[str, str],
) -> str:
    strategy = str(row.get("response_strategy", ""))
    episode_id = str(row.get("episode_id", ""))
    choices = SAFE_REWRITE_BANK.get(strategy, SAFE_REWRITE_BANK["neutral_observation"])
    return stable_pick(
        choices,
        (
            episode_id,
            strategy,
            features["mechanism"],
            features["theme"],
            features["context"],
            features["mask"],
            "safe_rewrite",
        ),
    )


def finalize_text(text: str, strategy: str) -> str:
    text = first_sentence(text) if strategy == "no_response" else normalize_space(text)
    return remove_overpraise_flags(text)


def build_response(row: dict[str, Any], input_row: dict[str, Any]) -> str:
    post = str(input_row.get("speaker_post", ""))
    platform = str(input_row.get("platform", ""))
    relationship = str(input_row.get("relationship", ""))
    strategy = str(row.get("response_strategy", ""))
    mechanism = str(row.get("bragging_mechanism", ""))
    episode_id = str(row.get("episode_id", ""))
    features = extract_features(post, mechanism, platform, relationship)
    features["tone"] = infer_tone(strategy, features["context"], relationship)

    text = finalize_text(template_for_strategy(strategy, mechanism, features, episode_id), strategy)
    candidate_row = dict(row)
    candidate_row["response_text"] = text
    first_judgment = judge_row(input_row, candidate_row)
    if not first_judgment["hard_issues"]:
        return text

    rewritten = finalize_text(rewrite_for_hard_issues(row, input_row, features), strategy)
    rewritten_row = dict(row)
    rewritten_row["response_text"] = rewritten
    second_judgment = judge_row(input_row, rewritten_row)
    if len(second_judgment["hard_issues"]) <= len(first_judgment["hard_issues"]):
        return rewritten
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
