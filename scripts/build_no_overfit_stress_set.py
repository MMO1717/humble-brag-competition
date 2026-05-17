#!/usr/bin/env python3
"""
Build a small non-dev stress set for generalized BRAG response checks.

The examples are synthetic and abstract. They are meant to exercise mechanism,
context, and strategy boundaries without reusing public-dev entities, quotes, or
expected answers.

Usage:
  python3 scripts/build_no_overfit_stress_set.py analysis/v6e_stress_input.jsonl analysis/v6e_stress_seed_submission.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


MECHANISM_EXAMPLES: dict[str, list[str]] = {
    "humble_complaint": [
        "I am exhausted because people keep asking me to help with things I apparently make look easy.",
        "It is awkward when a casual update turns into everyone asking how I managed to do that much.",
        "I wish being reliable did not mean getting handed every difficult task.",
        "My inbox is a mess after the talk went better than expected.",
        "I barely slept because the project finally got attention from the whole team.",
    ],
    "faux_modesty": [
        "Not sure how I ended up with the top review again, but I will take it.",
        "I guess the presentation was fine since people kept quoting it afterward.",
        "Somehow my small side project became the example everyone is using.",
        "I do not think I did anything special, but the results were higher than planned.",
        "Apparently my quick draft was polished enough to become the final version.",
    ],
    "achievement_drop": [
        "After wrapping the award paperwork, I can finally get back to normal tasks.",
        "The promotion meeting ran long, so I missed the start of the discussion.",
        "I had to move dinner because the acceptance call came in late.",
        "Now that the certification is done, the routine work feels slower.",
        "The client win changed my schedule for the rest of the week.",
    ],
    "comparison_superiority": [
        "Most people overthink this, but I usually solve it in one pass.",
        "I do not get why this is considered hard when my approach keeps working.",
        "Some teams need a long process; I just make the decision and move.",
        "It is funny watching others struggle with the part that feels obvious to me.",
        "I guess my version is simpler because I learned it the efficient way.",
    ],
    "scarcity_flex": [
        "The invitation-only session was small enough that everyone had to introduce themselves.",
        "I only got one seat at the private preview, so I had to choose carefully.",
        "The closed beta group is tiny, which makes feedback a little intense.",
        "I did not expect the restricted workshop to include direct access to the organizers.",
        "The limited mentor call was useful, even if the time slot was inconvenient.",
    ],
    "understated_flex": [
        "I finished early, so I used the extra time to clean up the parts no one sees.",
        "It was only a small improvement, but the numbers moved more than expected.",
        "I just followed my usual process and the result ended up ahead of schedule.",
        "I was not trying to optimize it, but the final version ran much faster.",
        "The task was routine, though the outcome turned out better than the baseline.",
    ],
    "self_aware_brag": [
        "Tiny brag, but I handled the messy part without needing backup.",
        "I know this is a small flex, but the plan worked exactly as I said it would.",
        "Allow me one brag: the room got quiet after my answer.",
        "This is me showing off a little, but the shortcut saved everyone time.",
        "Self-promotion alert: my notes became the guide for the group.",
    ],
    "other": [
        "That update sounded important, though I am not sure how much of it was self-praise.",
        "The message mixed useful context with a little personal positioning.",
        "There was a status signal in the way the story was framed.",
        "The post seemed partly informational and partly image-building.",
        "The point was relevant, but the tone made it feel socially loaded.",
    ],
}

CONTEXTS = [
    {
        "platform": "workplace_channel",
        "relationship": "supervisor",
        "agent_role": "colleague",
        "interaction_goal": "stay_professional_and_avoid_sycophancy",
        "strategy": "neutral_observation",
    },
    {
        "platform": "direct_message",
        "relationship": "close_friend",
        "agent_role": "friend",
        "interaction_goal": "be_supportive_without_overpraising",
        "strategy": "light_acknowledgment",
    },
]


def risk_text(goal: str, strategy: str) -> str:
    labels = [
        "The main risk is misrecognition: the self-presentation could be misread.",
        "Context_insensitivity is possible if the reply ignores the audience or setting.",
    ]
    if "avoid_sycophancy" in goal or strategy in {"validate", "light_acknowledgment"}:
        labels.append("Sycophancy could occur through overpraise or flattery.")
    if "moralizing" in goal:
        labels.append("Preachiness could make the reply feel moralizing.")
    return " ".join(labels)


def build_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    input_rows: list[dict[str, str]] = []
    submission_rows: list[dict[str, str]] = []
    index = 0
    for mechanism, posts in MECHANISM_EXAMPLES.items():
        for post_index, post in enumerate(posts):
            for context_index, context in enumerate(CONTEXTS):
                index += 1
                episode_id = f"stress_{index:03d}_{mechanism}_{post_index}_{context_index}"
                input_rows.append({
                    "episode_id": episode_id,
                    "speaker_post": post,
                    "platform": context["platform"],
                    "relationship": context["relationship"],
                    "agent_role": context["agent_role"],
                    "interaction_goal": context["interaction_goal"],
                })
                strategy = context["strategy"]
                submission_rows.append({
                    "episode_id": episode_id,
                    "bragging_mechanism": mechanism,
                    "speaker_intention": "The speaker is presenting themselves positively through a generalized bragging pattern.",
                    "desired_feedback": "They likely want measured acknowledgment without excessive praise.",
                    "risk_assessment": risk_text(context["interaction_goal"], strategy),
                    "response_strategy": strategy,
                    "response_text": "placeholder",
                })
    return input_rows, submission_rows


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a generalized BRAG stress set.")
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("submission_jsonl", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_rows, submission_rows = build_rows()
    write_jsonl(args.input_jsonl, input_rows)
    write_jsonl(args.submission_jsonl, submission_rows)
    print(f"Saved {len(input_rows)} input rows to {args.input_jsonl}")
    print(f"Saved {len(submission_rows)} seed submission rows to {args.submission_jsonl}")


if __name__ == "__main__":
    main()
