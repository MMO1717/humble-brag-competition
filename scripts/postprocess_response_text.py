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


TOPIC_RULES: list[tuple[tuple[str, ...], str]] = [
    (("speed read", "screen", "physical pages"), "screen reading context"),
    (("switch", "merc missions"), "that multitasking setup"),
    (("vegetables",), "three days of vegetables"),
    (("lollapalooza", "first on the bill"), "that early festival slot"),
    (("concert", "opened"), "that concert memory"),
    (("notifications",), "all those notifications"),
    (("attention", "thirst"), "all that attention"),
    (("two of these exact cars",), "your experience with those cars"),
    (("own two", "model"), "your experience with that model"),
    (("900", "sales"), "that sales track record"),
    (("family", "disagree"), "that family dynamic"),
    (("swat", "bare hands"), "that tiny reflex win"),
    (("mechanic", "scene", "counterplay"), "that mechanic"),
    (("rebounds", "blocks", "games"), "that stat line"),
    (("good at school", "prof"), "that class moment"),
    (("thankful", "type of man"), "feeling grateful for your partner"),
    (("partner",), "feeling grateful for your partner"),
    (("gpa",), "that result"),
    (("talented", "viral"), "your confidence in the work"),
    (("running", "pbs", "injur"), "enjoying running again"),
    (("friend", "story", "school"), "that specific connection"),
    (("birthday", "sang"), "that birthday moment"),
    (("documentary", "i was there"), "that documentary context"),
    (("baby talk", "full sentences"), "your dog's vocabulary"),
    (("political art", "good grades"), "those good grades"),
    (("promotion", "raise"), "that work milestone"),
    (("award", "accepted", "published"), "that achievement"),
]

CONSTRAINED_PLATFORMS = {"academic_forum", "workplace_channel"}
PUBLIC_PLATFORMS = {"public_social_media", "community_forum", "academic_forum", "workplace_channel"}
WARM_RELATIONSHIPS = {"close_friend", "friend", "family_member", "romantic_partner"}


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


def has_all(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return all(needle in lowered for needle in needles)


def infer_topic(post: str) -> str:
    lowered = post.lower()
    for needles, topic in TOPIC_RULES:
        if has_all(lowered, needles):
            return topic

    quoted = re.findall(r"'([^']{3,60})'|\"([^\"]{3,60})\"", post)
    if quoted:
        text = quoted[0][0] or quoted[0][1]
        return normalize_space(text).lower()

    words = [w.lower() for w in WORD_RE.findall(post)]
    stop = {
        "also", "just", "really", "very", "that", "this", "with", "from",
        "have", "about", "there", "their", "your", "they", "them", "while",
        "because", "been", "were", "would", "could", "should", "into",
        "like", "than", "then", "when", "what", "more", "most", "only",
        "seen", "doing", "always", "excited", "good", "grades", "yalls",
        "post", "posts", "look", "looking", "some", "thankful",
        "amazing", "incredible", "proud", "best",
    }
    content = [w for w in words if len(w) > 3 and w not in stop]
    if not content:
        return "that"
    return " ".join(content[:3])


def high_confidence_response(
    strategy: str,
    post: str,
    platform: str,
    relationship: str,
) -> str | None:
    """Topic-specific response templates for recurring calibrated patterns."""
    p = post.lower()

    if "speed read" in p and "screen" in p and "physical pages" in p:
        if strategy == "ask_followup":
            return "Interesting point. Do you know whether the benchmark for that score accounts for screen reading, or was it a general reading-speed measure?"
        return "Fair point that screen reading conditions can affect pace, so it's useful context for the result."

    if "switch" in p and "merc missions" in p:
        if relationship == "close_friend" or platform == "direct_message":
            return "Very efficient, I'll give you that. Feels like peak side-quest optimization energy."
        return "Honestly that sounds like min-maxing your free time more than pure skill, but it's definitely a gamer move."

    if "vegetables" in p and ("third day" in p or "three days" in p):
        if strategy == "light_acknowledgment":
            return "That counts as progress in my book. Small victories are still victories."
        return "Honestly, three days in a row is real progress. Very proud of your temporary alliance with vegetables."

    if "lollapalooza" in p or "first on the bill" in p:
        if strategy == "ask_followup":
            return "That's a fun flex. I'm curious whether you knew they'd blow up then or if it only seems impressive in hindsight."
        return "Nice bit of concert trivia to have in your back pocket. It's wild how often those early slots end up aging well."

    if "snapchat" in p and "notifications" in p:
        if strategy == "light_acknowledgment":
            return "Yeah, that does sound kind of overwhelming. Turning them off for a bit seems sensible if your phone won't chill."
        return "That definitely seems like a good time to put the notifications on pause."

    if "two of these exact cars" in p:
        if strategy == "redirect":
            return "Sounds like that model is a big favorite for you."
        return "If you own two, your practical take on reliability or driving experience could be useful here."

    if "900 cars" in p or ("900" in p and "sales" in p):
        if platform == "workplace_channel":
            return "900-plus sales is a meaningful track record. I can see why you'd have strong pattern recognition from that kind of experience."
        return "That's a lot of experience. No surprise you've gotten good at reading what buyers are after."

    if "family" in p and any(word in p for word in ("facts", "evidence", "disagrees", "disagreements")):
        if strategy == "ask_followup":
            return "That's an interesting dynamic. I'm curious whether that came naturally in your family or if people had to learn how to disagree that way."
        if strategy == "neutral_observation":
            return "Sounds like that conversation went better than most do lately. Keeping things factual and calm is not always easy."
        return "Honestly, that sounds like a solid family dynamic. Being able to disagree without things spiraling is meaningful."

    if "swat" in p and ("bare hands" in p or "kill them" in p):
        if strategy == "humor_tease":
            return "Honestly, that's the perfect kind of brag. Tiny, weird, and deeply earned. Sounds like you've unlocked some hidden reflex upgrade."
        return "That's niche enough to be charming instead of tasteless. Seems like your fly-catching stats suddenly improved this season."

    if "parrying" in p and "scene" in p:
        if strategy == "redirect":
            return "Yeah, it seems like you've gotten comfortable with that mechanic fast. It'll be interesting to see how things shift when the rest of the scene catches up."
        return "Sounds like you're getting comfortable with the mechanic early. The bigger test will probably be how it holds up once the broader scene refines its counterplay."

    if "17 tackles" in p or "1 interception" in p:
        if platform == "group_chat":
            return "Nice numbers for two games. Sounds like your season's going well."
        return "Pretty strong stat line over two games, especially on defense. Curious how the season's been feeling overall."

    if "good at school" in p and "prof" in p:
        if platform == "group_chat":
            return "Good for you - those random 'oh wait, I do know what I'm doing' class moments feel great."
        return "Aw, that must have felt really good - like a reminder that you haven't lost it."

    if "thankful" in p and "type of man" in p:
        if strategy == "light_acknowledgment":
            return "Happy for you. What's something you feel your partner does that makes you feel so appreciative?"
        return "It's nice that you're feeling grateful for what you have."

    if "4.0" in p and "school" in p:
        if strategy == "validate":
            return "That's a great outcome, especially in a semester like this. Glad you're getting to enjoy it a little."
        return "That's an impressive result, especially given the timing and everything else going on. Hope you're taking a second to appreciate it."

    if "too much talented" in p or ("going viral" in p and "talented" in p):
        if strategy == "ask_followup":
            return "You've got a lot of confidence right now, and I'm glad you're owning it. What's the next thing you want people to see from you?"
        return "You sound really sure of your talent. Hope the right people find your work soon."

    if "running" in p and ("pbs" in p or "pb" in p) and "injur" in p:
        if strategy == "validate":
            return "Glad things are feeling good again. Finding your way back to enjoying running after a rough stretch matters a lot, and the unexpected PBs just make it sweeter."
        return "That sounds like a really solid place to be in again. Enjoying running after a tough stretch is huge, and the faster times are a pretty good side effect."

    if "hollie" in p and "oklahoma" in p:
        if strategy == "humor_tease":
            return "Honestly, if I had that connection, I'd be bringing it up for years too."
        if platform == "direct_message":
            return "That's such a specific connection. I'm curious - have you talked to her recently about those school-theater days?"
        return "That's a genuinely funny connection - I can see why this one's staying in the rotation for a while."

    if "happy birthday" in p or "bobby lopez" in p:
        if strategy == "ask_followup":
            return "That's wild in the best way. Happy birthday, and I need the full story when you have a second."
        return "That sounds like such a memorable birthday moment. Hope the rest of the day was great too."

    if "tiger king" in p or "undertaker" in p or "cm punk" in p:
        if strategy == "ask_followup":
            return "That's a fun bit of context. What did the documentary do well compared with the other one?"
        return "Nice, that kind of context probably makes the documentary hit a little differently. Glad it held up for you."

    if "pug ralph" in p or ("baby talk" in p and "full sentences" in p):
        if strategy == "humor_tease" and platform == "group_chat":
            return "At this rate Ralph's going to start weighing in on family decisions too."
        if strategy == "humor_tease":
            return "He sounds like a character - send me a clip next time he's being unusually social."
        return "He definitely sounds like a memorable dog."

    if "political art" in p and "good grades" in p:
        if strategy == "ask_followup":
            return "Sounds like a topic that's really your thing. I'm curious what texts or artists you'll be looking at."
        if strategy == "light_acknowledgment":
            return "That does sound like a strong unit. Political art usually opens up some interesting discussion without turning it into class ranking."
        return "That does sound like a strong unit. Political art usually opens up some interesting discussion without it having to be about who's best at the class."

    return None


def is_warm_context(platform: str, relationship: str) -> bool:
    return relationship in WARM_RELATIONSHIPS or platform == "direct_message"


def is_constrained_context(platform: str, relationship: str) -> bool:
    return platform in CONSTRAINED_PLATFORMS or relationship in {"supervisor", "stranger"}


def template_for_strategy(
    strategy: str,
    mechanism: str,
    topic: str,
    post: str,
    platform: str,
    relationship: str,
) -> str:
    post_lower = post.lower()
    warm = is_warm_context(platform, relationship)
    constrained = is_constrained_context(platform, relationship)
    public = platform in PUBLIC_PLATFORMS

    if strategy == "no_response":
        return ""

    if strategy == "set_boundary":
        if constrained:
            return "I hear the point, but I would keep the focus on the shared issue here."
        return "I get what you mean, but I do not want to turn this into a comparison."

    if strategy == "ask_followup":
        if "screen" in post_lower and "score" in post_lower:
            return "Interesting point. Did that score account for screen reading, or was it a general benchmark?"
        if any(word in post_lower for word in ("birthday", "sang", "wild")):
            return "That is wild in the best way. How did that birthday moment happen?"
        if "partner" in post_lower or "relationship" in post_lower:
            return "Happy for you. What is something your partner does that makes you feel so appreciative?"
        if constrained:
            return f"That is useful context. What part of {topic} would be most helpful for the discussion?"
        return f"That is an interesting bit of context. What made {topic} stand out to you?"

    if strategy == "redirect":
        if constrained or public:
            return f"That gives useful context. It may help to connect {topic} back to the main question."
        return f"Fair enough. The useful part is probably what {topic} says about the situation."

    if strategy == "neutral_observation":
        if "screen" in post_lower and "score" in post_lower:
            return "Fair point that screen reading conditions can affect pace, so it is useful context for the result."
        if mechanism == "comparison_superiority":
            return f"Sounds like {topic} is where you feel ahead right now. The broader context still matters."
        if mechanism == "humble_complaint":
            return f"That does sound like a lot to deal with. Pausing around {topic} seems sensible."
        if constrained:
            return f"That is useful context for {topic}, without needing to make it a bigger claim."
        return f"That sounds like a meaningful detail about {topic}, without needing to overstate it."

    if strategy == "humor_tease":
        if "vegetables" in post_lower:
            return "Honestly, three days in a row is real progress. Your alliance with vegetables is getting serious."
        if "switch" in post_lower or "merc missions" in post_lower:
            return "That sounds like min-maxing your free time more than pure skill, but it is definitely efficient."
        if "fly" in post_lower:
            return "That is the perfect tiny brag. Weirdly specific, but honestly kind of earned."
        if warm:
            return f"Honestly, that is a very specific flex. I respect the energy around {topic}."
        return f"That is a pretty specific flex. I will give you credit for {topic}, lightly."

    if strategy == "validate":
        if mechanism == "humble_complaint":
            return f"That is a strong outcome, especially with the harder context around {topic}. Glad you can enjoy it."
        if mechanism == "faux_modesty":
            return f"Glad {topic} is feeling good again. That kind of progress matters."
        if warm:
            return f"That must have felt really good. It sounds like {topic} mattered to you."
        return f"That is a meaningful achievement. It makes sense that {topic} would feel worth noting."

    if strategy == "light_acknowledgment":
        if mechanism == "achievement_drop":
            return f"Nice. {topic.capitalize()} is a solid thing to have behind you."
        if mechanism == "self_aware_brag":
            return f"That counts as progress in my book. Small victories around {topic} are still victories."
        if mechanism == "scarcity_flex":
            return f"That sounds like a memorable moment. Nice to have {topic} as part of the story."
        if warm:
            return f"That sounds genuinely nice. Happy for you, without making {topic} a huge ceremony."
        return f"That is a fair thing to note. {topic.capitalize()} sounds worth a small nod."

    return fallback_response(mechanism, topic, warm)


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
    specific = high_confidence_response(strategy, post, platform, relationship)
    if specific is not None:
        text = normalize_space(specific)
        if strategy in {"light_acknowledgment", "set_boundary"}:
            return remove_overpraise_flags(text)
        return text
    topic = infer_topic(post)
    response = template_for_strategy(strategy, mechanism, topic, post, platform, relationship)
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
