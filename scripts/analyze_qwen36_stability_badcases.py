#!/usr/bin/env python3
"""Compare qwen3.6-27b original/rerun dev outputs for stable bad cases."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "outputs/dev_submission_multi_v1_qwen36_27b.jsonl"
RERUN = ROOT / "outputs/dev_submission_multi_v1_qwen36_27b_rerun.jsonl"
ORIGINAL_SCORE = ROOT / "outputs/dev_score_report_multi_v1_qwen36_27b.json"
RERUN_SCORE = ROOT / "outputs/dev_score_report_multi_v1_qwen36_27b_rerun.json"
DEV_INPUT = ROOT / "BRAG-Agent-public/data/dev_input.jsonl"
DEV_GOLD = ROOT / "BRAG-Agent-public/data/dev_gold.jsonl"
OUT = ROOT / "analysis/qwen36_27b_stability_badcases.md"


RISK_KEYWORDS = {
    "sycophancy": [
        "sycophancy",
        "sycophantic",
        "overpraise",
        "over-praise",
        "over praise",
        "excessive praise",
        "blind validation",
        "flattery",
        "over-validat",
        "too much praise",
        "uncritical praise",
    ],
    "preachiness": [
        "preachiness",
        "preach",
        "preachy",
        "moralize",
        "moralizing",
        "lecture",
        "lecturing",
        "judgmental",
        "scold",
    ],
    "misrecognition": [
        "misrecognition",
        "misread",
        "misinterpret",
        "misinterpretation",
        "taking this as",
        "treating this as",
        "false assumption",
        "miss the brag",
        "missing the",
        "fail to see",
        "failing to see",
    ],
    "strategy_inconsistency": [
        "strategy inconsistency",
        "strategy_inconsistency",
        "inconsistent strategy",
        "mismatch",
        "does not match the strategy",
        "strategy mismatch",
    ],
    "context_insensitivity": [
        "context insensitivity",
        "context_insensitivity",
        "context insensitive",
        "ignore the context",
        "ignoring the context",
        "miss the context",
        "audience",
        "setting",
        "platform",
        "relationship",
        "public forum",
        "professional",
        "workplace",
    ],
    "over_coldness": [
        "over_coldness",
        "over cold",
        "over-cold",
        "too cold",
        "dismissive",
        "curt",
        "coldness",
        "detached",
    ],
}

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_by_id(path: Path) -> dict[str, dict]:
    return {row["episode_id"]: row for row in load_jsonl(path)}


def normalize_tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall((text or "").lower())


def token_f1(prediction: str, gold: str) -> float:
    pred_tokens = normalize_tokens(prediction)
    gold_tokens = normalize_tokens(gold)
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    counts = Counter(gold_tokens)
    overlap = 0
    for tok in pred_tokens:
        if counts[tok] > 0:
            counts[tok] -= 1
            overlap += 1
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def extract_risk_labels(text: str) -> set[str]:
    lowered = (text or "").lower()
    return {
        label
        for label, keywords in RISK_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    }


def set_f1(pred: set[str], gold: set[str]) -> float:
    if not pred and not gold:
        return 1.0
    if not pred or not gold:
        return 0.0
    overlap = len(pred & gold)
    precision = overlap / len(pred)
    recall = overlap / len(gold)
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def strategy_case_score(pred: str, gold: dict) -> float:
    if pred == gold["preferred_strategy"]:
        return 1.0
    if pred in set(gold.get("acceptable_strategies", [])):
        return 0.5
    return 0.0


def strategy_status(pred: str, gold: dict) -> str:
    score = strategy_case_score(pred, gold)
    if score == 1.0:
        return "preferred"
    if score == 0.5:
        return "acceptable"
    return "unacceptable"


def context_flags(inp: dict) -> str:
    flags = [
        f"platform={inp.get('platform')}",
        f"relationship={inp.get('relationship')}",
        f"goal={inp.get('interaction_goal')}",
    ]
    return ", ".join(flags)


def short(text: str, n: int = 180) -> str:
    value = " ".join((text or "").split())
    return value if len(value) <= n else value[: n - 1] + "..."


def reason_for_mechanism(gold_mech: str, orig_mech: str, rerun_mech: str, post: str) -> str:
    if orig_mech == rerun_mech:
        return f"stable boundary confusion: both runs map `{gold_mech}` to `{orig_mech}`."
    return f"unstable wrong mechanism: both miss `{gold_mech}`, but choose different alternatives."


def reason_for_strategy(inp: dict, gold: dict, orig: dict, rerun: dict) -> str:
    o = orig["response_strategy"]
    r = rerun["response_strategy"]
    pref = gold["preferred_strategy"]
    if o == r:
        return f"stable strategy over-selection of `{o}` where preferred is `{pref}`."
    if pref in {"ask_followup", "humor_tease"} and o in {"light_acknowledgment", "neutral_observation"} and r in {"light_acknowledgment", "neutral_observation"}:
        return "both runs choose a safer generic acknowledgment/observation instead of the more interactive preferred strategy."
    return "both runs miss the preferred/acceptable strategy, but the concrete wrong label is not identical."


def reason_for_risk(missed: set[str], pred_o: set[str], pred_r: set[str]) -> str:
    if "context_insensitivity" in missed:
        return "stable miss of contextual risk; model names generic misrecognition/sycophancy but not platform/relationship sensitivity."
    if "misrecognition" in missed:
        return "stable miss of the core brag-recognition risk."
    if "over_coldness" in missed:
        return "stable miss of warmth/engagement risk."
    return f"stable missing risk labels: {', '.join(sorted(missed))}."


def metrics_table(score_a: dict, score_b: dict) -> list[str]:
    ma = score_a["proxy_metrics"]
    mb = score_b["proxy_metrics"]
    rows = [
        "| metric | original | rerun | delta |",
        "|---|---:|---:|---:|",
    ]
    for key, label in [
        ("proxy_dev_score", "proxy_dev_score"),
        ("mechanism_accuracy", "mechanism_accuracy"),
        ("strategy_score", "strategy_score"),
        ("risk_label_f1_from_risk_assessment", "risk_label_f1"),
        ("response_reference_token_f1", "response_reference_token_f1"),
    ]:
        a = ma[key]
        b = mb[key]
        rows.append(f"| `{label}` | {a:.4f} | {b:.4f} | {b - a:+.4f} |")
    rows.append(
        f"| `format errors` | {score_a['format_report']['warning_count']} | {score_b['format_report']['warning_count']} | 0 |"
    )
    return rows


def main() -> None:
    original = load_by_id(ORIGINAL)
    rerun = load_by_id(RERUN)
    inputs = load_by_id(DEV_INPUT)
    gold = load_by_id(DEV_GOLD)
    score_a = json.loads(ORIGINAL_SCORE.read_text(encoding="utf-8"))
    score_b = json.loads(RERUN_SCORE.read_text(encoding="utf-8"))
    episode_ids = list(gold.keys())

    mech_same = 0
    strategy_same = 0
    risk_same = 0
    response_f1_diffs = []
    response_f1_abs_diffs = []

    stable_mech_errors = []
    stable_strategy_unacceptable = []
    stable_strategy_nonpreferred = []
    stable_risk_misses = []

    mech_conf_orig = Counter()
    mech_conf_rerun = Counter()
    mech_conf_same_episode = Counter()
    pred_mech_distribution = {"original": Counter(), "rerun": Counter(), "gold": Counter()}

    strategy_dist = {"original": Counter(), "rerun": Counter(), "preferred": Counter()}
    strategy_wrong_pair_orig = Counter()
    strategy_wrong_pair_rerun = Counter()
    stable_wrong_strategy_pair = Counter()
    stable_nonpref_strategy_pair = Counter()

    risk_pred_dist = {"original": Counter(), "rerun": Counter(), "gold": Counter()}
    stable_missed_risk_labels = Counter()
    false_positive_risk_orig = Counter()
    false_positive_risk_rerun = Counter()
    stable_false_positive_risk = Counter()
    per_episode = {}

    for eid in episode_ids:
        g = gold[eid]
        inp = inputs[eid]
        o = original[eid]
        r = rerun[eid]
        gold_risks = set(g.get("gold_risk_labels", []))
        o_risks = extract_risk_labels(o.get("risk_assessment", ""))
        r_risks = extract_risk_labels(r.get("risk_assessment", ""))
        gold_mech = g["gold_bragging_mechanism"]
        o_mech = o["bragging_mechanism"]
        r_mech = r["bragging_mechanism"]
        o_strategy = o["response_strategy"]
        r_strategy = r["response_strategy"]

        pred_mech_distribution["gold"][gold_mech] += 1
        pred_mech_distribution["original"][o_mech] += 1
        pred_mech_distribution["rerun"][r_mech] += 1
        strategy_dist["preferred"][g["preferred_strategy"]] += 1
        strategy_dist["original"][o_strategy] += 1
        strategy_dist["rerun"][r_strategy] += 1
        for label in gold_risks:
            risk_pred_dist["gold"][label] += 1
        for label in o_risks:
            risk_pred_dist["original"][label] += 1
        for label in r_risks:
            risk_pred_dist["rerun"][label] += 1
        false_positive_risk_orig.update(o_risks - gold_risks)
        false_positive_risk_rerun.update(r_risks - gold_risks)
        stable_false_positive_risk.update((o_risks & r_risks) - gold_risks)

        if o_mech == r_mech:
            mech_same += 1
        if o_strategy == r_strategy:
            strategy_same += 1
        if o_risks == r_risks:
            risk_same += 1

        o_f1 = token_f1(o.get("response_text", ""), g.get("reference_response", ""))
        r_f1 = token_f1(r.get("response_text", ""), g.get("reference_response", ""))
        response_f1_diffs.append(r_f1 - o_f1)
        response_f1_abs_diffs.append(abs(r_f1 - o_f1))

        if o_mech != gold_mech:
            mech_conf_orig[(gold_mech, o_mech)] += 1
        if r_mech != gold_mech:
            mech_conf_rerun[(gold_mech, r_mech)] += 1
        if o_mech != gold_mech and r_mech != gold_mech:
            if o_mech == r_mech:
                mech_conf_same_episode[(gold_mech, o_mech)] += 1
            stable_mech_errors.append(
                {
                    "eid": eid,
                    "post": inp["speaker_post"],
                    "gold": gold_mech,
                    "orig": o_mech,
                    "rerun": r_mech,
                    "same": o_mech == r_mech,
                    "reason": reason_for_mechanism(gold_mech, o_mech, r_mech, inp["speaker_post"]),
                }
            )

        o_strat_score = strategy_case_score(o_strategy, g)
        r_strat_score = strategy_case_score(r_strategy, g)
        if o_strat_score < 1.0 and r_strat_score < 1.0:
            stable_nonpref_strategy_pair[(g["preferred_strategy"], o_strategy, r_strategy)] += 1
            stable_strategy_nonpreferred.append(eid)
        if o_strat_score == 0.0:
            strategy_wrong_pair_orig[(g["preferred_strategy"], o_strategy)] += 1
        if r_strat_score == 0.0:
            strategy_wrong_pair_rerun[(g["preferred_strategy"], r_strategy)] += 1
        if o_strat_score == 0.0 and r_strat_score == 0.0:
            stable_wrong_strategy_pair[(g["preferred_strategy"], o_strategy, r_strategy)] += 1
            stable_strategy_unacceptable.append(
                {
                    "eid": eid,
                    "post": inp["speaker_post"],
                    "context": context_flags(inp),
                    "preferred": g["preferred_strategy"],
                    "acceptable": sorted(g.get("acceptable_strategies", [])),
                    "orig": o_strategy,
                    "rerun": r_strategy,
                    "same": o_strategy == r_strategy,
                    "reason": reason_for_strategy(inp, g, o, r),
                }
            )

        missed_both = gold_risks - o_risks - set()
        missed_both = missed_both & (gold_risks - r_risks)
        if missed_both:
            stable_missed_risk_labels.update(missed_both)
            stable_risk_misses.append(
                {
                    "eid": eid,
                    "post": inp["speaker_post"],
                    "gold": sorted(gold_risks),
                    "orig": sorted(o_risks),
                    "rerun": sorted(r_risks),
                    "missed": sorted(missed_both),
                    "reason": reason_for_risk(missed_both, o_risks, r_risks),
                }
            )

        per_episode[eid] = {
            "o_risks": o_risks,
            "r_risks": r_risks,
            "gold_risks": gold_risks,
            "o_response_f1": o_f1,
            "r_response_f1": r_f1,
            "o_strategy_score": o_strat_score,
            "r_strategy_score": r_strat_score,
        }

    common_mech_pairs = sorted(
        set(mech_conf_orig) & set(mech_conf_rerun),
        key=lambda pair: (mech_conf_orig[pair] + mech_conf_rerun[pair], mech_conf_same_episode[pair]),
        reverse=True,
    )
    common_strategy_pairs = sorted(
        set(strategy_wrong_pair_orig) & set(strategy_wrong_pair_rerun),
        key=lambda pair: strategy_wrong_pair_orig[pair] + strategy_wrong_pair_rerun[pair],
        reverse=True,
    )

    avg_f1_delta = sum(response_f1_diffs) / len(response_f1_diffs)
    avg_abs_f1_delta = sum(response_f1_abs_diffs) / len(response_f1_abs_diffs)

    lines: list[str] = []
    lines.append("# qwen3.6-27b Stability Bad Case Analysis\n")
    lines.append("## Summary\n")
    lines.append(
        f"`qwen3.6-27b` is format-stable but behaviorally noisy: rerun score is higher by "
        f"{score_b['proxy_metrics']['proxy_dev_score'] - score_a['proxy_metrics']['proxy_dev_score']:+.3f}, "
        "while `strategy_score` drops. Stable errors exist, but most are boundary cases rather than a clean global prompt bug."
    )
    lines.append("")
    lines.append(
        f"Stable bad cases: {len(stable_mech_errors)} mechanism misses, "
        f"{len(stable_strategy_unacceptable)} fully unacceptable strategy misses "
        f"({len(stable_strategy_nonpreferred)} non-preferred in both runs), and "
        f"{len(stable_risk_misses)} examples with at least one gold risk label missed in both runs."
    )
    lines.append("")
    lines.append("## Files Used\n")
    for path in [ORIGINAL, RERUN, ORIGINAL_SCORE, RERUN_SCORE, DEV_INPUT, DEV_GOLD]:
        lines.append(f"- `{path.relative_to(ROOT)}`")
    lines.append("")
    lines.append("## Metrics Comparison\n")
    lines.extend(metrics_table(score_a, score_b))
    lines.append("")
    lines.append("## Run-to-Run Consistency\n")
    lines.append("| item | count / 45 | rate |")
    lines.append("|---|---:|---:|")
    lines.append(f"| `bragging_mechanism` exactly same | {mech_same}/45 | {mech_same / 45:.1%} |")
    lines.append(f"| `response_strategy` exactly same | {strategy_same}/45 | {strategy_same / 45:.1%} |")
    lines.append(f"| extracted risk labels exactly same | {risk_same}/45 | {risk_same / 45:.1%} |")
    lines.append(f"| mean response token-F1 delta (rerun-original) | {avg_f1_delta:+.4f} | - |")
    lines.append(f"| mean absolute response token-F1 delta | {avg_abs_f1_delta:.4f} | - |")
    lines.append("")
    lines.append("Prediction distribution drift:")
    lines.append("")
    lines.append("| label family | original | rerun | note |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| mechanisms | {dict(pred_mech_distribution['original'].most_common())} | {dict(pred_mech_distribution['rerun'].most_common())} | rerun shifts toward more correct mechanisms overall |"
    )
    lines.append(
        f"| strategies | {dict(strategy_dist['original'].most_common())} | {dict(strategy_dist['rerun'].most_common())} | `light_acknowledgment` remains dominant; `neutral_observation` falls |"
    )
    lines.append(
        f"| risk labels | {dict(risk_pred_dist['original'].most_common())} | {dict(risk_pred_dist['rerun'].most_common())} | `misrecognition` is almost always present; other risks are unstable |"
    )
    lines.append("")

    lines.append("## Stable Error Cases\n")
    lines.append("### Mechanism Both Wrong\n")
    lines.append("| episode_id | speaker_post | gold | original | rerun | same wrong? | reason |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in stable_mech_errors:
        lines.append(
            f"| `{row['eid']}` | {short(row['post'], 120)} | `{row['gold']}` | `{row['orig']}` | `{row['rerun']}` | {row['same']} | {row['reason']} |"
        )
    lines.append("")

    lines.append("### Strategy Both Unacceptable\n")
    lines.append("| episode_id | context | speaker_post | preferred / acceptable | original | rerun | same wrong? | reason |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in stable_strategy_unacceptable:
        lines.append(
            f"| `{row['eid']}` | {row['context']} | {short(row['post'], 115)} | `{row['preferred']}` / {row['acceptable']} | `{row['orig']}` | `{row['rerun']}` | {row['same']} | {row['reason']} |"
        )
    lines.append("")
    lines.append(
        f"Non-preferred in both runs, including acceptable-but-not-preferred cases: **{len(stable_strategy_nonpreferred)} / 45**."
    )
    lines.append("")

    lines.append("### Risk Labels Missed In Both Runs\n")
    lines.append("| episode_id | speaker_post | gold labels | original extracted | rerun extracted | missed both | reason |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in stable_risk_misses:
        lines.append(
            f"| `{row['eid']}` | {short(row['post'], 120)} | {row['gold']} | {row['orig']} | {row['rerun']} | {row['missed']} | {row['reason']} |"
        )
    lines.append("")

    lines.append("## Stable Mechanism Confusions\n")
    lines.append("| gold -> predicted | original count | rerun count | same-episode stable count | interpretation |")
    lines.append("|---|---:|---:|---:|---|")
    for pair in common_mech_pairs:
        gold_mech, pred_mech = pair
        interp = "repeatable confusion" if mech_conf_same_episode[pair] else "appears in both runs but not necessarily same examples"
        lines.append(
            f"| `{gold_mech}` -> `{pred_mech}` | {mech_conf_orig[pair]} | {mech_conf_rerun[pair]} | {mech_conf_same_episode[pair]} | {interp} |"
        )
    if not common_mech_pairs:
        lines.append("| none | 0 | 0 | 0 | no common confusion pair |")
    lines.append("")
    lines.append("Key read: only one shared same-episode mechanism pair reaches 3 examples, and the rest are at 1-2 examples. This is too sparse for broad mechanism calibration.")
    lines.append("")

    lines.append("## Stable Strategy Errors\n")
    lines.append("| pattern | evidence | read |")
    lines.append("|---|---:|---|")
    light_orig = strategy_dist["original"]["light_acknowledgment"]
    light_rerun = strategy_dist["rerun"]["light_acknowledgment"]
    neutral_orig = strategy_dist["original"]["neutral_observation"]
    neutral_rerun = strategy_dist["rerun"]["neutral_observation"]
    ask_pref = strategy_dist["preferred"]["ask_followup"]
    ask_orig = strategy_dist["original"]["ask_followup"]
    ask_rerun = strategy_dist["rerun"]["ask_followup"]
    humor_pref = strategy_dist["preferred"]["humor_tease"]
    humor_orig = strategy_dist["original"]["humor_tease"]
    humor_rerun = strategy_dist["rerun"]["humor_tease"]
    lines.append(
        f"| overuse `light_acknowledgment` | original {light_orig}, rerun {light_rerun}, preferred {strategy_dist['preferred']['light_acknowledgment']} | stable dominance, but many are acceptable/correct; do not add broad downweighting. |"
    )
    lines.append(
        f"| overuse `neutral_observation` | original {neutral_orig}, rerun {neutral_rerun}, preferred {strategy_dist['preferred']['neutral_observation']} | not stable overuse in rerun; original was more neutral-heavy. |"
    )
    lines.append(
        f"| underuse `ask_followup` | original {ask_orig}, rerun {ask_rerun}, preferred {ask_pref} | stable underuse and likely the best narrow candidate. |"
    )
    lines.append(
        f"| underuse `humor_tease` | original {humor_orig}, rerun {humor_rerun}, preferred {humor_pref} | original underuses it; rerun improves but still low. Prior broad calibration already caused collateral damage. |"
    )
    avoid_syc_bad = []
    cold_close = []
    for eid in episode_ids:
        inp = inputs[eid]
        g = gold[eid]
        o = original[eid]
        r = rerun[eid]
        if inp.get("interaction_goal") == "avoid_sycophancy" and (o["response_strategy"] == "validate" or r["response_strategy"] == "validate"):
            avoid_syc_bad.append(eid)
        if inp.get("relationship") in {"close_friend", "friend"} and g["preferred_strategy"] in {"humor_tease", "ask_followup"}:
            if o["response_strategy"] in {"neutral_observation", "light_acknowledgment"} and r["response_strategy"] in {"neutral_observation", "light_acknowledgment"}:
                cold_close.append(eid)
    lines.append(
        f"| `avoid_sycophancy` misuses `validate` | {len(avoid_syc_bad)} examples | not a stable issue in these two runs. |"
    )
    lines.append(
        f"| close/playful contexts too cold | {len(cold_close)} examples | exists, but overlaps with ask/humor underuse and should not be fixed by broad humor preference. |"
    )
    lines.append("")
    lines.append("Common unacceptable strategy pairs appearing in both runs:")
    lines.append("")
    lines.append("| preferred -> predicted | original count | rerun count |")
    lines.append("|---|---:|---:|")
    for pref, pred in common_strategy_pairs:
        lines.append(f"| `{pref}` -> `{pred}` | {strategy_wrong_pair_orig[(pref, pred)]} | {strategy_wrong_pair_rerun[(pref, pred)]} |")
    lines.append("")

    lines.append("## Stable Risk Label Errors\n")
    lines.append("| gold risk label | gold count | missed in both runs | original predicted count | rerun predicted count | false positives original/rerun | read |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for label in ["misrecognition", "context_insensitivity", "sycophancy", "preachiness", "strategy_inconsistency", "over_coldness"]:
        read = ""
        if label == "context_insensitivity":
            read = "yes, this is a stable miss: contextual labels are often absent unless the response names audience/platform explicitly."
        elif label == "sycophancy":
            read = f"stable over-write problem: {stable_false_positive_risk[label]} examples add it in both runs without gold support."
        elif label == "misrecognition":
            read = "not a stable miss; it is heavily predicted and sometimes over-predicted."
        else:
            read = "low support in this dev slice; avoid global rule."
        lines.append(
            f"| `{label}` | {risk_pred_dist['gold'][label]} | {stable_missed_risk_labels[label]} | {risk_pred_dist['original'][label]} | {risk_pred_dist['rerun'][label]} | {false_positive_risk_orig[label]}/{false_positive_risk_rerun[label]} | {read} |"
        )
    lines.append("")
    lines.append(
        "Answer to required checks: qwen3.6-27b **does** stably miss `context_insensitivity`; it also **does** stably over-write `sycophancy` "
        f"({stable_false_positive_risk['sycophancy']} examples where both runs add it but gold does not); it does **not** stably miss `misrecognition`."
    )
    lines.append("")

    lines.append("## Calibration Candidates\n")
    lines.append("| priority | target | evidence | proposed_change | expected_gain | risk | decision |")
    lines.append("|---:|---|---|---|---|---|---|")
    lines.append(
        "| 1 | risk-label boundary: `context_insensitivity` vs `sycophancy` | "
        f"{stable_missed_risk_labels['context_insensitivity']} stable `context_insensitivity` misses out of {risk_pred_dist['gold']['context_insensitivity']} gold occurrences; "
        f"{stable_false_positive_risk['sycophancy']} stable `sycophancy` false positives where both runs add it but gold does not. | "
        "Tiny risk-assessment calibration: include `context_insensitivity` when platform/relationship/interaction goal changes the safe response; do not add `sycophancy` merely because the goal says avoid_sycophancy unless overpraise/validate is the concrete risk. | "
        "Likely improves risk_label_f1 precision/recall without changing mechanism or response strategy. | May under-report true sycophancy if wording becomes too restrictive. | Worth one small isolated prompt or offline postprocess experiment. |"
    )
    lines.append(
        "| 2 | `ask_followup` underuse | "
        f"preferred `ask_followup` appears {ask_pref} times; predictions are original {ask_orig}, rerun {ask_rerun}; several stable misses choose generic acknowledgment/observation. | "
        "Offline analysis first: identify exact cues where acceptable set contains only/primarily `ask_followup`; do not combine with humor rules. | "
        "Could recover some strategy score. | Broad wording already hurt previous calibration; high collateral risk. | Analyze further before implementation. |"
    )
    lines.append(
        "| 3 | mechanism boundary examples | "
        f"{len(stable_mech_errors)} both-wrong examples, but no confusion pair has high support. | "
        "Do not change prompt yet; collect stable pairs across more seeds/models or add an offline confusion notebook. | "
        "Unclear. | High risk of random-seed overfit. | Do not implement now. |"
    )
    lines.append("")

    lines.append("## Recommendation\n")
    lines.append(
        "**Yes, but only for a very narrow next step.** The only implementation candidate with enough stable evidence is a small risk-label boundary calibration: recover missed `context_insensitivity` while reducing automatic `sycophancy` additions. It can be scoped to `risk_assessment` wording and should not disturb mechanism or strategy choices."
    )
    lines.append("")
    lines.append(
        "Do **not** run another broad strategy calibration yet. `ask_followup` underuse is real, but previous mixed strategy calibration already showed collateral damage. The next strategy step should be offline case filtering, not prompt implementation."
    )
    lines.append("")
    lines.append("Recommended next small implementation scope:")
    lines.append("")
    lines.append("- One short prompt addition only in the risk-assessment instruction area.")
    lines.append("- Add `context_insensitivity` when platform/relationship/interaction-goal context changes the safe response.")
    lines.append("- Avoid adding `sycophancy` just because `interaction_goal=avoid_sycophancy`; require a concrete overpraise/validate risk.")
    lines.append("- Re-evaluate against both original-style and rerun-style qwen3.6-27b dev runs; keep only if risk F1 improves without >1pp drop in mechanism or strategy.")
    lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print(
        json.dumps(
            {
                "mechanism_consistency": mech_same,
                "strategy_consistency": strategy_same,
                "risk_label_consistency": risk_same,
                "stable_mechanism_errors": len(stable_mech_errors),
                "stable_strategy_unacceptable": len(stable_strategy_unacceptable),
                "stable_risk_miss_examples": len(stable_risk_misses),
                "recommend_implementation": True,
                "recommended_scope": "narrow context_insensitivity/sycophancy risk-label boundary calibration",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
