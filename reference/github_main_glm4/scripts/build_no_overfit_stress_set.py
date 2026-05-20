#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


MECHANISM_EXAMPLES: dict[str, list[str]] = {
    "humble_complaint": [
        "I am tired because the difficult tasks keep getting handed to me.",
        "My inbox got crowded after the update drew more attention than expected.",
        "It is awkward when a small success turns into more work for me.",
        "I barely rested because people kept asking how I handled the project.",
        "I wish being reliable did not mean getting every urgent request.",
    ],
    "faux_modesty": [
        "Not sure how I ended up with the strongest review again, but I will take it.",
        "I guess the talk went fine since people kept quoting it later.",
        "Somehow my small side project became the example everyone is using.",
        "I do not think I did anything special, but the result landed well.",
        "Apparently my quick draft was polished enough to become the final version.",
    ],
    "achievement_drop": [
        "After wrapping the award paperwork, I can finally get back to routine tasks.",
        "The promotion meeting ran long, so I missed the start of the discussion.",
        "I had to move dinner because the acceptance call came in late.",
        "Now that the certification is done, the regular work feels slower.",
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
        "That update sounded important, though part of it was socially loaded.",
        "The message mixed useful context with a little personal positioning.",
        "There was a status signal in the way the story was framed.",
        "The post seemed partly informational and partly image-building.",
        "The point was relevant, but the tone made it feel socially delicate.",
    ],
}

CONTEXTS = [
    {
        "platform": "workplace_channel",
        "relationship": "supervisor",
        "agent_role": "colleague",
        "interaction_goal": "stay_professional_and_avoid_sycophancy",
    },
    {
        "platform": "direct_message",
        "relationship": "close_friend",
        "agent_role": "friend",
        "interaction_goal": "be_supportive_without_overpraising",
    },
]


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    index = 0
    for mechanism, posts in MECHANISM_EXAMPLES.items():
        for post_index, post in enumerate(posts):
            for context_index, context in enumerate(CONTEXTS):
                index += 1
                rows.append(
                    {
                        "episode_id": f"stress_{index:03d}_{mechanism}_{post_index}_{context_index}",
                        "speaker_post": post,
                        "platform": context["platform"],
                        "relationship": context["relationship"],
                        "agent_role": context["agent_role"],
                        "interaction_goal": context["interaction_goal"],
                        "expected_mechanism": mechanism,
                    }
                )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    output_path = Path("outputs/no_overfit_offline/stress_input.jsonl")
    rows = build_rows()
    write_jsonl(output_path, rows)
    print(f"Saved {len(rows)} stress rows to {output_path}")


if __name__ == "__main__":
    main()
