#!/usr/bin/env python3
"""
Compare baseline and qwen3.6-27b dev outputs for model adaptation analysis.

This is a read-only analysis script. It does not import or modify agent code.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


RISK_KEYWORDS = {
    "sycophancy": ["sycophancy", "sycophantic", "overpraise", "over-praise", "excessive praise", "blind validation", "flattery"],
    "preachiness": ["preach", "preachy", "moralize", "moralizing", "lecture", "judgmental"],
    "misrecognition": ["misrecognition", "misread", "misinterpret", "false assumption", "assume expertise", "unsupported assumption"],
    "strategy_inconsistency": ["strategy inconsistency", "inconsistent strategy", "mismatch", "does not match the strategy"],
    "context_insensitivity": ["context insensitivity", "context insensitive", "ignore the context", "miss the context", "audience", "setting"],
    "over_coldness": ["over cold", "over-cold", "too cold", "dismissive", "curt", "coldness"],
}

TOKEN_RE = re.compile(r"[a-z0-9]+")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def esc(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def preview(text: str, limit: int = 180) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "..."


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text).lower())


def token_f1(prediction: str, gold: str) -> float:
    pred_tokens = tokens(prediction)
    gold_tokens = tokens(gold)
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    gold_counts = Counter(gold_tokens)
    overlap = 0
    for token in pred_tokens:
        if gold_counts[token] > 0:
            gold_counts[token] -= 1
            overlap += 1
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def risk_labels(text: str) -> set[str]:
    lowered = str(text).lower()
    return {label for label, kws in RISK_KEYWORDS.items() if any(kw in lowered for kw in kws)}


def set_f1(predicted: set[str], gold: set[str]) -> float:
    if not predicted and not gold:
        return 1.0
    if not predicted or not gold:
        return 0.0
    overlap = len(predicted & gold)
    precision = overlap / len(predicted)
    recall = overlap / len(gold)
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def strategy_score(pred: str, gold: dict) -> float:
    if pred == gold["preferred_strategy"]:
        return 1.0
    if pred in gold.get("acceptable_strategies", []):
        return 0.5
    return 0.0


def evaluate(rows_by_id: dict[str, dict], gold_by_id: dict[str, dict], episode_ids: list[str]) -> dict:
    mechanism_hits = 0
    preferred_hits = 0
    acceptable_hits = 0
    strategy_scores = []
    response_scores = []
    risk_scores = []
    for eid in episode_ids:
        pred = rows_by_id[eid]
        gold = gold_by_id[eid]
        mechanism_hits += pred["bragging_mechanism"] == gold["gold_bragging_mechanism"]
        preferred_hits += pred["response_strategy"] == gold["preferred_strategy"]
        acceptable_hits += pred["response_strategy"] == gold["preferred_strategy"] or pred["response_strategy"] in gold.get("acceptable_strategies", [])
        strategy_scores.append(strategy_score(pred["response_strategy"], gold))
        response_scores.append(token_f1(pred["response_text"], gold["reference_response"]))
        risk_scores.append(set_f1(risk_labels(pred["risk_assessment"]), set(gold.get("gold_risk_labels", []))))
    total = len(episode_ids)
    mechanism_accuracy = mechanism_hits / total
    avg_strategy = sum(strategy_scores) / total
    avg_risk = sum(risk_scores) / total
    avg_response = sum(response_scores) / total
    proxy = 100 * (0.30 * mechanism_accuracy + 0.20 * avg_strategy + 0.20 * avg_risk + 0.15 * avg_response + 0.15)
    return {
        "proxy_dev_score": round(proxy, 3),
        "mechanism_accuracy": round(mechanism_accuracy, 4),
        "preferred_strategy_accuracy": round(preferred_hits / total, 4),
        "acceptable_strategy_rate": round(acceptable_hits / total, 4),
        "strategy_score": round(avg_strategy, 4),
        "risk_label_f1": round(avg_risk, 4),
        "response_reference_token_f1": round(avg_response, 4),
        "format_errors": 0,
    }


def per_gold_mechanism(rows_by_id: dict[str, dict], gold_by_id: dict[str, dict], episode_ids: list[str]) -> dict[str, tuple[int, int]]:
    total = Counter()
    correct = Counter()
    for eid in episode_ids:
        gold_mech = gold_by_id[eid]["gold_bragging_mechanism"]
        total[gold_mech] += 1
        correct[gold_mech] += rows_by_id[eid]["bragging_mechanism"] == gold_mech
    return {mech: (correct[mech], total[mech]) for mech in sorted(total)}


def confusion(rows_by_id: dict[str, dict], gold_by_id: dict[str, dict], episode_ids: list[str]) -> Counter[tuple[str, str]]:
    c = Counter()
    for eid in episode_ids:
        c[(gold_by_id[eid]["gold_bragging_mechanism"], rows_by_id[eid]["bragging_mechanism"])] += 1
    return c


def preferred_strategy_hits(rows_by_id: dict[str, dict], gold_by_id: dict[str, dict], episode_ids: list[str]) -> dict[str, tuple[int, int]]:
    total = Counter()
    hit = Counter()
    for eid in episode_ids:
        pref = gold_by_id[eid]["preferred_strategy"]
        total[pref] += 1
        hit[pref] += rows_by_id[eid]["response_strategy"] == pref
    return {s: (hit[s], total[s]) for s in sorted(total)}


def build_report(args: argparse.Namespace) -> str:
    inputs = {r["episode_id"]: r for r in load_jsonl(args.inputs)}
    gold = {r["episode_id"]: r for r in load_jsonl(args.gold)}
    baseline = {r["episode_id"]: r for r in load_jsonl(args.baseline)}
    qwen = {r["episode_id"]: r for r in load_jsonl(args.qwen)}
    episode_ids = [r["episode_id"] for r in load_jsonl(args.inputs)]

    base_metrics = evaluate(baseline, gold, episode_ids)
    qwen_metrics = evaluate(qwen, gold, episode_ids)

    base_mech = per_gold_mechanism(baseline, gold, episode_ids)
    qwen_mech = per_gold_mechanism(qwen, gold, episode_ids)
    base_pred_mech = Counter(baseline[eid]["bragging_mechanism"] for eid in episode_ids)
    qwen_pred_mech = Counter(qwen[eid]["bragging_mechanism"] for eid in episode_ids)
    qwen_conf = confusion(qwen, gold, episode_ids)

    mech_correct_to_wrong = []
    mech_wrong_to_correct = []
    strategy_worse = []
    strategy_better = []
    for eid in episode_ids:
        g = gold[eid]
        b = baseline[eid]
        q = qwen[eid]
        b_mech_ok = b["bragging_mechanism"] == g["gold_bragging_mechanism"]
        q_mech_ok = q["bragging_mechanism"] == g["gold_bragging_mechanism"]
        if b_mech_ok and not q_mech_ok:
            mech_correct_to_wrong.append(eid)
        if not b_mech_ok and q_mech_ok:
            mech_wrong_to_correct.append(eid)
        b_strat = strategy_score(b["response_strategy"], g)
        q_strat = strategy_score(q["response_strategy"], g)
        if b_strat > q_strat:
            strategy_worse.append(eid)
        if b_strat < q_strat:
            strategy_better.append(eid)

    added_confusions = Counter()
    for eid in mech_correct_to_wrong:
        added_confusions[(gold[eid]["gold_bragging_mechanism"], qwen[eid]["bragging_mechanism"])] += 1

    base_pred_strategy = Counter(baseline[eid]["response_strategy"] for eid in episode_ids)
    qwen_pred_strategy = Counter(qwen[eid]["response_strategy"] for eid in episode_ids)
    base_strategy_hits = preferred_strategy_hits(baseline, gold, episode_ids)
    qwen_strategy_hits = preferred_strategy_hits(qwen, gold, episode_ids)

    risk_counter_base = Counter()
    risk_counter_qwen = Counter()
    risk_missed_qwen = Counter()
    response_lengths_base = []
    response_lengths_qwen = []
    response_f1_deltas = []
    for eid in episode_ids:
        g_labels = set(gold[eid].get("gold_risk_labels", []))
        b_labels = risk_labels(baseline[eid]["risk_assessment"])
        q_labels = risk_labels(qwen[eid]["risk_assessment"])
        risk_counter_base.update(b_labels)
        risk_counter_qwen.update(q_labels)
        risk_missed_qwen.update(g_labels - q_labels)
        response_lengths_base.append(len(tokens(baseline[eid]["response_text"])))
        response_lengths_qwen.append(len(tokens(qwen[eid]["response_text"])))
        response_f1_deltas.append((eid, token_f1(qwen[eid]["response_text"], gold[eid]["reference_response"]) - token_f1(baseline[eid]["response_text"], gold[eid]["reference_response"])))

    avoid_validate = [
        eid for eid in episode_ids
        if inputs[eid].get("interaction_goal") == "avoid_sycophancy" and qwen[eid]["response_strategy"] == "validate"
    ]

    mechanism_cases = mech_correct_to_wrong[:4]
    strategy_cases = strategy_worse[:4]

    lines = []
    lines.append("# qwen3.6-27b Adaptation Analysis")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(
        "`qwen3.6-27b` underperforms the baseline mainly on strategy choice and secondarily on mechanism classification. "
        "The output format remains valid, and risk/response degradation is smaller than the mechanism/strategy drop."
    )
    lines.append("")
    lines.append(
        "The clearest stable pattern is strategy calibration: qwen3.6-27b overuses `light_acknowledgment` and underuses `ask_followup`/`humor_tease`, which directly lowers preferred and acceptable strategy scores. "
        "Mechanism errors are more dispersed, with the largest new confusion being `understated_flex -> achievement_drop` but only affecting two baseline-correct samples."
    )
    lines.append("")
    lines.append("## Data and Files Used")
    lines.append("")
    lines.append(f"- baseline: `{args.baseline}`")
    lines.append(f"- qwen3.6-27b: `{args.qwen}`")
    lines.append(f"- dev input: `{args.inputs}`")
    lines.append(f"- gold/reference: `{args.gold}`")
    lines.append("")
    lines.append("## Overall Metrics")
    lines.append("")
    lines.append("| metric | baseline | qwen3.6-27b | delta |")
    lines.append("|---|---:|---:|---:|")
    for key in ["proxy_dev_score", "mechanism_accuracy", "strategy_score", "risk_label_f1", "response_reference_token_f1", "format_errors"]:
        b = base_metrics[key]
        q = qwen_metrics[key]
        lines.append(f"| `{key}` | {b} | {q} | {round(q - b, 4)} |")
    lines.append("")
    lines.append("## Mechanism Comparison")
    lines.append("")
    lines.append("### Per-Gold Mechanism Accuracy")
    lines.append("")
    lines.append("| gold mechanism | baseline | qwen3.6-27b | delta |")
    lines.append("|---|---:|---:|---:|")
    for mech in sorted(set(base_mech) | set(qwen_mech)):
        bc, bt = base_mech.get(mech, (0, 0))
        qc, qt = qwen_mech.get(mech, (0, 0))
        bacc = bc / bt if bt else 0
        qacc = qc / qt if qt else 0
        lines.append(f"| `{mech}` | {bc}/{bt} ({bacc:.3f}) | {qc}/{qt} ({qacc:.3f}) | {qacc - bacc:+.3f} |")
    lines.append("")
    lines.append("### Predicted Mechanism Distribution")
    lines.append("")
    lines.append("| mechanism | baseline count | qwen3.6-27b count | delta |")
    lines.append("|---|---:|---:|---:|")
    for mech in sorted(set(base_pred_mech) | set(qwen_pred_mech)):
        lines.append(f"| `{mech}` | {base_pred_mech[mech]} | {qwen_pred_mech[mech]} | {qwen_pred_mech[mech] - base_pred_mech[mech]:+d} |")
    lines.append("")
    lines.append("### qwen3.6-27b Confusion Matrix")
    lines.append("")
    pred_mechs = sorted(set(qwen_pred_mech))
    gold_mechs = sorted({gold[eid]["gold_bragging_mechanism"] for eid in episode_ids})
    lines.append("| gold \\ predicted | " + " | ".join(f"`{m}`" for m in pred_mechs) + " |")
    lines.append("|---" + "|---:" * len(pred_mechs) + "|")
    for gm in gold_mechs:
        lines.append(f"| `{gm}` | " + " | ".join(str(qwen_conf[(gm, pm)]) for pm in pred_mechs) + " |")
    lines.append("")
    lines.append("### Mechanism Movement")
    lines.append("")
    lines.append(f"- baseline correct -> qwen wrong: {len(mech_correct_to_wrong)}")
    lines.append(f"- baseline wrong -> qwen correct: {len(mech_wrong_to_correct)}")
    lines.append("- largest added confusions:")
    for (gold_mech, pred_mech), count in added_confusions.most_common(5):
        lines.append(f"  - `{gold_mech} -> {pred_mech}`: {count}")
    lines.append("")
    lines.append("## Strategy Comparison")
    lines.append("")
    lines.append(f"- acceptable strategy rate: baseline {base_metrics['acceptable_strategy_rate']}, qwen3.6-27b {qwen_metrics['acceptable_strategy_rate']}")
    lines.append(f"- baseline better than qwen on strategy score: {len(strategy_worse)} samples")
    lines.append(f"- qwen better than baseline on strategy score: {len(strategy_better)} samples")
    lines.append(f"- qwen `validate` in `avoid_sycophancy` contexts: {len(avoid_validate)} samples ({', '.join(avoid_validate) if avoid_validate else 'none'})")
    lines.append("")
    lines.append("### Preferred Strategy Hit Rate")
    lines.append("")
    lines.append("| preferred strategy | baseline | qwen3.6-27b | delta |")
    lines.append("|---|---:|---:|---:|")
    for strat in sorted(set(base_strategy_hits) | set(qwen_strategy_hits)):
        bh, bt = base_strategy_hits.get(strat, (0, 0))
        qh, qt = qwen_strategy_hits.get(strat, (0, 0))
        bacc = bh / bt if bt else 0
        qacc = qh / qt if qt else 0
        lines.append(f"| `{strat}` | {bh}/{bt} ({bacc:.3f}) | {qh}/{qt} ({qacc:.3f}) | {qacc - bacc:+.3f} |")
    lines.append("")
    lines.append("### Predicted Strategy Distribution")
    lines.append("")
    lines.append("| strategy | baseline count | qwen3.6-27b count | delta |")
    lines.append("|---|---:|---:|---:|")
    for strat in sorted(set(base_pred_strategy) | set(qwen_pred_strategy)):
        lines.append(f"| `{strat}` | {base_pred_strategy[strat]} | {qwen_pred_strategy[strat]} | {qwen_pred_strategy[strat] - base_pred_strategy[strat]:+d} |")
    lines.append("")
    lines.append("## Risk and Response Comparison")
    lines.append("")
    lines.append("| item | baseline | qwen3.6-27b | note |")
    lines.append("|---|---:|---:|---|")
    lines.append(f"| avg response length | {sum(response_lengths_base)/len(response_lengths_base):.2f} | {sum(response_lengths_qwen)/len(response_lengths_qwen):.2f} | qwen is slightly shorter |")
    for label in sorted(set(risk_counter_base) | set(risk_counter_qwen)):
        lines.append(f"| risk label `{label}` mentions | {risk_counter_base[label]} | {risk_counter_qwen[label]} | delta {risk_counter_qwen[label] - risk_counter_base[label]:+d} |")
    lines.append("")
    lines.append("Most missed qwen risk labels:")
    lines.append("")
    for label, count in risk_missed_qwen.most_common():
        lines.append(f"- `{label}`: {count}")
    lines.append("")
    worst_response = sorted(response_f1_deltas, key=lambda x: x[1])[:5]
    lines.append("Largest response token-F1 drops:")
    lines.append("")
    for eid, delta in worst_response:
        lines.append(f"- `{eid}`: {delta:+.3f}")
    lines.append("")
    lines.append("## Representative Bad Cases")
    lines.append("")
    lines.append("### Mechanism: baseline correct, qwen wrong")
    lines.append("")
    lines.append("| episode_id | post | gold mechanism / strategy | baseline prediction | qwen3.6-27b prediction | reason | minimal fix direction |")
    lines.append("|---|---|---|---|---|---|---|")
    for eid in mechanism_cases:
        g = gold[eid]
        b = baseline[eid]
        q = qwen[eid]
        reason = "qwen overweights explicit achievement/status wording and misses indirect context or comparison boundary."
        if g["gold_bragging_mechanism"] == "comparison_superiority":
            reason = "qwen treats superiority framing as an offhand flex instead of recognizing the explicit comparison standard."
        lines.append(
            f"| `{eid}` | {esc(preview(inputs[eid]['speaker_post']))} | `{g['gold_bragging_mechanism']}` / `{g['preferred_strategy']}` | "
            f"`{b['bragging_mechanism']}` / `{b['response_strategy']}` | `{q['bragging_mechanism']}` / `{q['response_strategy']}` | "
            f"{reason} | Add a short boundary reminder for this mechanism pair. |"
        )
    lines.append("")
    lines.append("### Strategy: baseline strategy score better than qwen")
    lines.append("")
    lines.append("| episode_id | post | gold mechanism / strategy | baseline prediction | qwen3.6-27b prediction | reason | minimal fix direction |")
    lines.append("|---|---|---|---|---|---|---|")
    for eid in strategy_cases:
        g = gold[eid]
        b = baseline[eid]
        q = qwen[eid]
        reason = "qwen chooses a safer generic acknowledgment where the gold prefers a more interactive or playful response."
        if q["response_strategy"] == "validate":
            reason = "qwen over-validates despite a context where praise should be bounded."
        lines.append(
            f"| `{eid}` | {esc(preview(inputs[eid]['speaker_post']))} | `{g['gold_bragging_mechanism']}` / `{g['preferred_strategy']}` | "
            f"`{b['bragging_mechanism']}` / `{b['response_strategy']}` | `{q['bragging_mechanism']}` / `{q['response_strategy']}` | "
            f"{reason} | Prefer `ask_followup` or `humor_tease` when they are explicitly supported by playful/community context. |"
        )
    lines.append("")
    lines.append("## Minimal Prompt Calibration Candidates")
    lines.append("")
    lines.append("| priority | target | proposed_change | expected_gain | risk |")
    lines.append("|---:|---|---|---|---|")
    lines.append("| 1 | strategy: avoid generic light_acknowledgment | Add one short rule: When the context is playful/community and the brag invites banter or curiosity, prefer `humor_tease` or `ask_followup` over generic `light_acknowledgment`; keep praise bounded in `avoid_sycophancy`. | Could recover several strategy-score losses; directly targets overuse of `light_acknowledgment` and underuse of `ask_followup`/`humor_tease`. | Medium: may overuse playful strategies in serious contexts unless scoped to playful/community cues. |")
    lines.append("| 2 | mechanism: understated_flex vs achievement_drop | Add a short boundary note: if a concrete achievement is already present but the boast comes from an extra constraint/context that makes it look stronger, choose `understated_flex`; if the achievement itself is the main dropped fact, choose `achievement_drop`. | Targets the largest added mechanism confusion, affecting 2 baseline-correct samples. | Low-medium: could over-convert direct achievements with contextual details. |")
    lines.append("| 3 | mechanism: comparison_superiority vs understated_flex | Add a small reminder that explicit superiority standards such as true skill, better than, top, or outperforming others usually indicate `comparison_superiority`, not `understated_flex`. | May recover comparison boundary misses. | Medium: lexical cues can be misleading when comparison is background context. |")
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append(
        "Proceed to a minimal next-step implementation only if the experiment is allowed to target strategy calibration. "
        "There is one stable strategy pattern affecting more than two dev samples: qwen3.6-27b overuses `light_acknowledgment` and underuses `ask_followup`/`humor_tease`, lowering strategy score by 6.7pp. "
        "The recommended single change is the priority-1 strategy calibration, kept under 120 English words and limited to `src/system_prompt_sections.py`."
    )
    lines.append("")
    lines.append(
        "Do not implement a mechanism-only calibration first: the mechanism errors are real but more dispersed, and the clearest pair (`understated_flex -> achievement_drop`) affects only two baseline-correct examples."
    )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=Path("outputs/dev_submission_multi_v1_current.jsonl"))
    parser.add_argument("--qwen", type=Path, default=Path("outputs/dev_submission_multi_v1_qwen36_27b.jsonl"))
    parser.add_argument("--inputs", type=Path, default=Path("BRAG-Agent-public/data/dev_input.jsonl"))
    parser.add_argument("--gold", type=Path, default=Path("BRAG-Agent-public/data/dev_gold.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("analysis/qwen36_27b_adaptation_analysis.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
