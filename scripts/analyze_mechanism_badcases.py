#!/usr/bin/env python3
"""
Analyze mechanism-level bad cases for the multi_v1 dev submission.

This script is intentionally report-only. It does not import or change agent
code, and it only compares submission, gold, and input JSONL files.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


FOCUS_MECHANISMS = [
    "understated_flex",
    "achievement_drop",
    "faux_modesty",
    "comparison_superiority",
    "scarcity_flex",
    "humble_complaint",
]


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def text_preview(text: str, limit: int = 220) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "..."


def escape_md(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def classify_understated_reason(post: str, pred: str) -> str:
    lowered = post.lower()
    cues: list[str] = []

    if any(cue in lowered for cue in ["especially impressive", "score", "finished", "got", "earned"]):
        cues.append("contains explicit achievement/result wording")
    if any(cue in lowered for cue in ["turns out", "apparently", "just", "only", "casually", "somehow"]):
        cues.append("uses casual hedging that can signal understatement")
    if any(cue in lowered for cue in ["true", "than", "top", "best", "better", "worst", "more than"]):
        cues.append("contains comparison/superiority language")
    if any(cue in lowered for cue in ["sadly", "unfortunately", "problem", "complaint", "tired"]):
        cues.append("has complaint-like framing")
    if any(cue in lowered for cue in ["invite", "reservation", "sold out", "limited", "rare"]):
        cues.append("has scarcity/status-access language")

    if pred == "achievement_drop":
        base = "Likely read as achievement_drop because the post foregrounds a concrete result or performance claim."
    elif pred == "faux_modesty":
        base = "Likely read as faux_modesty because the post has a modest/hedged surface while still seeking recognition."
    elif pred == "comparison_superiority":
        base = "Likely read as comparison_superiority because the wording contrasts the speaker with a standard or other people."
    elif pred == "scarcity_flex":
        base = "Likely read as scarcity_flex because the status signal depends on access, rarity, or invitation."
    elif pred == "humble_complaint":
        base = "Likely read as humble_complaint because the flex is wrapped in burden or inconvenience language."
    elif pred == "self_aware_brag":
        base = "Likely read as self_aware_brag because the speaker explicitly flags the utterance as a brag or jokes about reusing the brag."
    elif pred == "understated_flex":
        base = "Prediction matched understated_flex; the status signal is implied through offhand context rather than stated directly."
    else:
        base = f"Likely read as {pred}; the prediction is outside the main understated_flex confusion buckets."

    if cues:
        return f"{base} Text cues: {', '.join(cues)}."
    return base


def candidate_assessments(confusion: Counter[tuple[str, str]], understated_rows: list[dict]) -> list[dict]:
    understated_to_achievement = sum(
        1 for row in understated_rows if row["pred_mechanism"] == "achievement_drop"
    )
    understated_to_faux = sum(
        1 for row in understated_rows if row["pred_mechanism"] == "faux_modesty"
    )
    understated_to_comparison = sum(
        1 for row in understated_rows if row["pred_mechanism"] == "comparison_superiority"
    )

    return [
        {
            "candidate": "If gold-like cue is achievement wording plus contextual handicap/qualifier, prefer understated_flex over achievement_drop.",
            "type": "safe_candidate" if understated_to_achievement >= 1 else "reject",
            "expected_fix": understated_to_achievement,
            "risk": "Low-medium: only apply when the result is already known and the extra clause reframes it as harder/more impressive.",
            "decision": "Good v1.2 candidate; keep trigger narrow around context-boosting clauses.",
        },
        {
            "candidate": "If post has hedges like just/apparently/turns out but no explicit self-deprecation, prefer understated_flex over faux_modesty.",
            "type": "risky_candidate" if understated_to_faux >= 1 else "reject",
            "expected_fix": understated_to_faux,
            "risk": "Medium-high: faux_modesty and understated_flex share humility cues; rules can easily over-normalize genuine modesty.",
            "decision": "Use only as reranking evidence, not as a hard postprocess rule.",
        },
        {
            "candidate": "If superiority terms are generic style markers but the speaker's own status is implied indirectly, prefer understated_flex over comparison_superiority.",
            "type": "risky_candidate" if understated_to_comparison >= 1 else "reject",
            "expected_fix": understated_to_comparison,
            "risk": "High: comparison_superiority is defined by comparison terms, so lexical overrides can damage true positives.",
            "decision": "Better handled by pairwise reranking than deterministic rules.",
        },
        {
            "candidate": "Map rarity/access words directly to scarcity_flex.",
            "type": "reject",
            "expected_fix": confusion.get(("understated_flex", "scarcity_flex"), 0),
            "risk": "High: scarcity language can be background context; needs intent and access-status interpretation.",
            "decision": "Do not add a standalone keyword rule.",
        },
    ]


def build_report(args: argparse.Namespace) -> str:
    submission_rows = load_jsonl(args.submission)
    gold_rows = load_jsonl(args.gold)
    input_rows = load_jsonl(args.inputs)

    submission = {row["episode_id"]: row for row in submission_rows}
    inputs = {row["episode_id"]: row for row in input_rows}
    episode_ids = [row["episode_id"] for row in gold_rows]

    gold_total: Counter[str] = Counter()
    gold_correct: Counter[str] = Counter()
    pred_total: Counter[str] = Counter()
    confusion: Counter[tuple[str, str]] = Counter()
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    detailed: list[dict] = []

    for gold in gold_rows:
        eid = gold["episode_id"]
        pred = submission.get(eid, {})
        inp = inputs.get(eid, {})
        gold_mech = gold["gold_bragging_mechanism"]
        pred_mech = pred.get("bragging_mechanism", "<missing>")

        gold_total[gold_mech] += 1
        pred_total[pred_mech] += 1
        matrix[gold_mech][pred_mech] += 1
        if pred_mech == gold_mech:
            gold_correct[gold_mech] += 1
        else:
            confusion[(gold_mech, pred_mech)] += 1

        detailed.append(
            {
                "episode_id": eid,
                "speaker_post": inp.get("speaker_post", ""),
                "platform": inp.get("platform", ""),
                "gold_mechanism": gold_mech,
                "pred_mechanism": pred_mech,
                "correct": pred_mech == gold_mech,
                "speaker_intention": pred.get("speaker_intention", ""),
                "desired_feedback": pred.get("desired_feedback", ""),
                "response_strategy": pred.get("response_strategy", ""),
                "response_text": pred.get("response_text", ""),
                "gold_intention": gold.get("gold_speaker_intention", ""),
                "gold_feedback": gold.get("gold_desired_feedback", ""),
            }
        )

    total = len(episode_ids)
    correct = sum(gold_correct.values())
    mechanism_accuracy = correct / total if total else 0.0
    understated_rows = [row for row in detailed if row["gold_mechanism"] == "understated_flex"]
    all_mechanisms = sorted(set(gold_total) | set(pred_total))
    top_pairs = confusion.most_common(10)

    lines: list[str] = []
    lines.append("# multi_v1 Mechanism Bad Case Analysis")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"Analyzed `{args.submission}` against `{args.gold}` with source text from `{args.inputs}`. "
        f"The run covers {total} dev examples and gets {correct}/{total} mechanisms correct "
        f"(`mechanism_accuracy` = {mechanism_accuracy:.4f})."
    )
    lines.append("")
    lines.append(
        "The main failure mode is not random label noise: it concentrates in pairs where an indirect status signal also contains explicit achievement, modesty, or comparison cues. "
        "`understated_flex` is the most important class because it is both the largest gold class and the class most often pulled into adjacent mechanisms."
    )
    lines.append("")
    lines.append("## Overall Mechanism Metrics")
    lines.append("")
    lines.append(f"- overall `mechanism_accuracy`: **{mechanism_accuracy:.4f}** ({correct}/{total})")
    lines.append("")
    lines.append("| gold mechanism | samples | correct | accuracy |")
    lines.append("|---|---:|---:|---:|")
    for mech in all_mechanisms:
        if mech == "<missing>":
            continue
        samples = gold_total[mech]
        if samples == 0:
            continue
        hit = gold_correct[mech]
        lines.append(f"| `{mech}` | {samples} | {hit} | {hit / samples:.3f} |")
    lines.append("")
    lines.append("| predicted mechanism | prediction count |")
    lines.append("|---|---:|")
    for mech, count in pred_total.most_common():
        lines.append(f"| `{mech}` | {count} |")
    lines.append("")
    lines.append("## Confusion Matrix")
    lines.append("")
    pred_headers = [m for m in all_mechanisms if m in pred_total]
    lines.append("| gold \\ predicted | " + " | ".join(f"`{m}`" for m in pred_headers) + " |")
    lines.append("|---" + "|---:" * len(pred_headers) + "|")
    for gold_mech in [m for m in all_mechanisms if m in gold_total]:
        row = [str(matrix[gold_mech].get(pred_mech, 0)) for pred_mech in pred_headers]
        lines.append(f"| `{gold_mech}` | " + " | ".join(row) + " |")
    lines.append("")
    lines.append("## Top Confusion Pairs")
    lines.append("")
    lines.append("| rank | gold mechanism | predicted mechanism | errors |")
    lines.append("|---:|---|---|---:|")
    for idx, ((gold_mech, pred_mech), count) in enumerate(top_pairs[:5], 1):
        lines.append(f"| {idx} | `{gold_mech}` | `{pred_mech}` | {count} |")
    lines.append("")
    if len(top_pairs) > 5:
        lines.append("Additional non-zero confusion pairs:")
        lines.append("")
        for gold_mech, pred_mech_count in top_pairs[5:]:
            lines.append(f"- `{gold_mech[0]}` -> `{gold_mech[1]}`: {pred_mech_count}")
        lines.append("")
    lines.append("## Understated Flex Deep Dive")
    lines.append("")
    lines.append(
        f"Gold `understated_flex` has {len(understated_rows)} examples. "
        f"The model gets {sum(1 for row in understated_rows if row['correct'])}/{len(understated_rows)} correct."
    )
    lines.append("")
    lines.append("| episode_id | post | predicted | correct | speaker_intention | desired_feedback | strategy | response_text | judgment |")
    lines.append("|---|---|---|---:|---|---|---|---|---|")
    for row in understated_rows:
        judgment = classify_understated_reason(row["speaker_post"], row["pred_mechanism"])
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{escape_md(row['episode_id'])}`",
                    escape_md(text_preview(row["speaker_post"])),
                    f"`{escape_md(row['pred_mechanism'])}`",
                    "yes" if row["correct"] else "no",
                    escape_md(text_preview(row["speaker_intention"], 140)),
                    escape_md(text_preview(row["desired_feedback"], 140)),
                    f"`{escape_md(row['response_strategy'])}`",
                    escape_md(text_preview(row["response_text"], 140)),
                    escape_md(judgment),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("### Understated Flex Misread Buckets")
    lines.append("")
    bucket_counts = Counter(row["pred_mechanism"] for row in understated_rows if not row["correct"])
    for pred_mech, count in bucket_counts.most_common():
        eids = [row["episode_id"] for row in understated_rows if row["pred_mechanism"] == pred_mech]
        lines.append(f"- `understated_flex -> {pred_mech}`: {count} examples ({', '.join(eids)}).")
    for watched in ["achievement_drop", "faux_modesty", "comparison_superiority"]:
        if bucket_counts.get(watched, 0) == 0:
            lines.append(f"- `understated_flex -> {watched}`: 0 examples in this run.")
    if not bucket_counts:
        lines.append("- No `understated_flex` mechanism errors.")
    lines.append("")
    lines.append("## Error Pattern Summary")
    lines.append("")
    lines.append("- Explicit result words such as score, completed, accepted, or impressive make indirect flexes look like `achievement_drop`.")
    lines.append("- Casual hedge words such as just, apparently, somehow, or turns out are useful understated-flex evidence only when they do not also imply self-deprecation.")
    lines.append("- Comparison terms are strong attractors for `comparison_superiority`; when they simply intensify the implied status signal, hard keyword rules would be brittle.")
    lines.append("- `scarcity_flex` has too little dev support for reliable tuning from this split alone.")
    lines.append("")
    lines.append("## Rule Candidate Assessment")
    lines.append("")
    lines.append("| candidate | type | expected_fix | risk | decision |")
    lines.append("|---|---|---:|---|---|")
    for row in candidate_assessments(confusion, understated_rows):
        lines.append(
            f"| {escape_md(row['candidate'])} | `{row['type']}` | {row['expected_fix']} | "
            f"{escape_md(row['risk'])} | {escape_md(row['decision'])} |"
        )
    lines.append("")
    lines.append("## Candidate Reranking Assessment")
    lines.append("")
    lines.append(
        "Candidate reranking is a better fit than broad postprocessing for the high-confusion mechanism pairs. "
        "The useful scope is a narrow top-2 judge that only activates when the generator's first answer is one of the known neighboring labels and the post contains mixed cues."
    )
    lines.append("")
    lines.append("| pair | suitability | rationale |")
    lines.append("|---|---|---|")
    rerank_pairs = [
        ("understated_flex vs achievement_drop", "high", "The dev errors often hinge on whether a concrete achievement is being directly announced or indirectly boosted by context."),
        ("understated_flex vs faux_modesty", "medium", "Both can share modest/hedged wording; a judge can inspect whether there is actual self-deprecation."),
        ("understated_flex vs comparison_superiority", "medium", "Comparison cues are lexical traps; pairwise reasoning may avoid overcorrecting true superiority claims."),
        ("achievement_drop vs comparison_superiority", "medium", "Useful when direct achievements are phrased through rank or standards, but the class boundary is less central than understated_flex."),
        ("scarcity_flex vs understated_flex", "low", "Only one gold scarcity example in dev, so a reranker would be under-calibrated."),
    ]
    for pair, suitability, rationale in rerank_pairs:
        lines.append(f"| `{pair}` | {suitability} | {rationale} |")
    lines.append("")
    lines.append(
        "Expected upside is modest but plausible: fixing even 1-3 mechanism errors would move mechanism accuracy by 2.2-6.7pp on this 45-example dev set. "
        "The instability risk comes from adding another LLM decision point; this should be mitigated by activating only on specific pair sets and requiring an explicit reason to override the original prediction."
    )
    lines.append("")
    lines.append("## Recommendation for multi_v1.2")
    lines.append("")
    lines.append(
        "Proceed with a minimal `multi_v1.2` candidate-reranking experiment rather than a broad prompt rewrite or many deterministic rules. "
        "The first implementation should target only `understated_flex <-> achievement_drop` and optionally log decisions for `understated_flex <-> faux_modesty` without overriding until the behavior is measured."
    )
    lines.append("")
    lines.append("Minimum next scope:")
    lines.append("")
    lines.append("- Keep `multi_v1` generation unchanged.")
    lines.append("- Add an optional mechanism-only reranking step for selected top-2 pairs.")
    lines.append("- Override only when the judge identifies contextual boosting or indirect offhand status signaling with high confidence.")
    lines.append("- Re-run dev and compare mechanism accuracy, risk label F1, and acceptable strategy rate together; do not optimize mechanism accuracy alone.")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, default=Path("outputs/dev_submission_multi_v1_rerun.jsonl"))
    parser.add_argument("--gold", type=Path, default=Path("BRAG-Agent-public/data/dev_gold.jsonl"))
    parser.add_argument("--inputs", type=Path, default=Path("BRAG-Agent-public/data/dev_input.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("analysis/mechanism_badcases_multi_v1.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
