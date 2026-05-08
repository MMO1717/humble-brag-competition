#!/usr/bin/env python3
"""
analyze_dev_results.py
分析 dev_submission.jsonl 与 dev_gold.jsonl 的差异，生成 bad case 报告。
"""

import json
import re
import sys
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

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def load_jsonl(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def normalize_tokens(text):
    return TOKEN_PATTERN.findall(text.lower())


def token_f1(prediction, gold):
    pred_tokens = normalize_tokens(prediction)
    gold_tokens = normalize_tokens(gold)
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    gold_counts = {}
    for t in gold_tokens:
        gold_counts[t] = gold_counts.get(t, 0) + 1
    overlap = 0
    for t in pred_tokens:
        if gold_counts.get(t, 0) > 0:
            gold_counts[t] -= 1
            overlap += 1
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def extract_risk_labels(text):
    lowered = text.lower()
    labels = set()
    for label, keywords in RISK_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            labels.add(label)
    return labels


def set_f1(pred_set, gold_set):
    if not pred_set and not gold_set:
        return 1.0
    if not pred_set or not gold_set:
        return 0.0
    overlap = len(pred_set & gold_set)
    p = overlap / len(pred_set)
    r = overlap / len(gold_set)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def main():
    submission_path = sys.argv[1] if len(sys.argv) > 1 else "outputs/dev_submission.jsonl"
    gold_path = sys.argv[2] if len(sys.argv) > 2 else "BRAG-Agent-public/data/dev_gold.jsonl"
    input_path = sys.argv[3] if len(sys.argv) > 3 else "BRAG-Agent-public/data/dev_input.jsonl"
    output_path = sys.argv[4] if len(sys.argv) > 4 else "analysis/dev_bad_cases.md"

    submission = {r["episode_id"]: r for r in load_jsonl(submission_path)}
    gold = {r["episode_id"]: r for r in load_jsonl(gold_path)}
    inputs = {r["episode_id"]: r for r in load_jsonl(input_path)}

    episode_ids = list(gold.keys())

    # ── 收集各类错误 ──
    mechanism_errors = []
    strategy_errors = []
    risk_label_issues = []
    response_quality_issues = []

    mechanism_confusion = Counter()
    strategy_confusion = Counter()
    mechanism_total = Counter()
    mechanism_correct = Counter()

    for eid in episode_ids:
        pred = submission.get(eid)
        g = gold[eid]
        inp = inputs.get(eid, {})

        if not pred:
            continue

        pred_mech = pred["bragging_mechanism"]
        gold_mech = g["gold_bragging_mechanism"]
        mechanism_total[gold_mech] += 1

        # Mechanism errors
        if pred_mech != gold_mech:
            mechanism_errors.append({
                "episode_id": eid,
                "speaker_post": inp.get("speaker_post", "")[:80],
                "pred": pred_mech,
                "gold": gold_mech,
            })
            mechanism_confusion[(pred_mech, gold_mech)] += 1
        else:
            mechanism_correct[gold_mech] += 1

        # Strategy errors
        pred_strat = pred["response_strategy"]
        pref_strat = g["preferred_strategy"]
        accept_strats = set(g.get("acceptable_strategies", []))
        if pred_strat != pref_strat and pred_strat not in accept_strats:
            strategy_errors.append({
                "episode_id": eid,
                "pred": pred_strat,
                "preferred": pref_strat,
                "acceptable": sorted(accept_strats),
            })
            strategy_confusion[(pred_strat, pref_strat)] += 1

        # Risk label issues
        pred_risk_labels = extract_risk_labels(pred["risk_assessment"])
        gold_risk_labels = set(g.get("gold_risk_labels", []))
        risk_f1 = set_f1(pred_risk_labels, gold_risk_labels)
        if risk_f1 < 0.5 and gold_risk_labels:
            risk_label_issues.append({
                "episode_id": eid,
                "pred_labels": sorted(pred_risk_labels),
                "gold_labels": sorted(gold_risk_labels),
                "f1": round(risk_f1, 3),
            })

        # Response quality issues
        resp_f1 = token_f1(pred["response_text"], g.get("reference_response", ""))
        if resp_f1 < 0.1:
            response_quality_issues.append({
                "episode_id": eid,
                "pred_text": pred["response_text"][:60],
                "ref_text": g.get("reference_response", "")[:60],
                "f1": round(resp_f1, 3),
            })

    # ── 生成 Markdown 报告 ──
    lines = []
    lines.append("# Dev Bad Case Analysis Report\n")

    # 总体分数
    score_data = json.loads(Path("outputs/dev_score_report.json").read_text())
    m = score_data["proxy_metrics"]
    lines.append("## 1. 总体分数摘要\n")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| proxy_dev_score | **{m['proxy_dev_score']}** |")
    lines.append(f"| mechanism_accuracy | {m['mechanism_accuracy']} |")
    lines.append(f"| strategy_score | {m['strategy_score']} |")
    lines.append(f"| risk_label_f1 | {m['risk_label_f1_from_risk_assessment']} |")
    lines.append(f"| response_reference_token_f1 | {m['response_reference_token_f1']} |")
    lines.append(f"| preferred_strategy_accuracy | {m['preferred_strategy_accuracy']} |")
    lines.append(f"| acceptable_strategy_rate | {m['acceptable_strategy_rate']} |")
    lines.append("")

    # 机制分类错误
    lines.append("## 2. 机制分类错误\n")
    lines.append(f"共 {len(mechanism_errors)} / {len(episode_ids)} 条错误\n")
    lines.append("### 机制准确率分布\n")
    lines.append(f"| 机制 | 正确 | 总计 | 准确率 |")
    lines.append(f"|------|------|------|--------|")
    for mech in sorted(mechanism_total.keys()):
        total = mechanism_total[mech]
        correct = mechanism_correct.get(mech, 0)
        acc = correct / total if total > 0 else 0
        lines.append(f"| {mech} | {correct} | {total} | {acc:.1%} |")
    lines.append("")

    lines.append("### 机制混淆 Top 10\n")
    lines.append(f"| 预测 | 金标 | 次数 |")
    lines.append(f"|------|------|------|")
    for (pred_m, gold_m), cnt in mechanism_confusion.most_common(10):
        lines.append(f"| {pred_m} | {gold_m} | {cnt} |")
    lines.append("")

    lines.append("### 机制错误样本\n")
    for err in mechanism_errors[:15]:
        lines.append(f"- **{err['episode_id']}**: pred=`{err['pred']}` gold=`{err['gold']}` — \"{err['speaker_post']}\"")
    lines.append("")

    # 策略选择错误
    lines.append("## 3. 策略选择错误\n")
    lines.append(f"共 {len(strategy_errors)} 条不在 preferred 且不在 acceptable\n")
    lines.append("### 策略混淆 Top 10\n")
    lines.append(f"| 预测 | 金标preferred | 次数 |")
    lines.append(f"|------|---------------|------|")
    for (pred_s, pref_s), cnt in strategy_confusion.most_common(10):
        lines.append(f"| {pred_s} | {pref_s} | {cnt} |")
    lines.append("")

    lines.append("### 策略错误样本\n")
    for err in strategy_errors[:15]:
        lines.append(f"- **{err['episode_id']}**: pred=`{err['pred']}` preferred=`{err['preferred']}` acceptable={err['acceptable']}")
    lines.append("")

    # 风险标签问题
    lines.append("## 4. 风险标签问题\n")
    lines.append(f"risk_label_f1 < 0.5 的样本: {len(risk_label_issues)} / {len(episode_ids)}\n")
    lines.append("### 缺少的风险标签分布\n")
    missing_label_counter = Counter()
    for issue in risk_label_issues:
        for gl in issue["gold_labels"]:
            if gl not in issue["pred_labels"]:
                missing_label_counter[gl] += 1
    for label, cnt in missing_label_counter.most_common():
        lines.append(f"- **{label}**: {cnt} 次未被包含在 risk_assessment 中")
    lines.append("")

    lines.append("### 典型低 F1 样本\n")
    for issue in sorted(risk_label_issues, key=lambda x: x["f1"])[:10]:
        lines.append(f"- **{issue['episode_id']}**: f1={issue['f1']}, pred_labels={issue['pred_labels']}, gold_labels={issue['gold_labels']}")
    lines.append("")

    # 回复质量问题
    lines.append("## 5. 回复质量问题\n")
    lines.append(f"response_reference_token_f1 < 0.1 的样本: {len(response_quality_issues)} / {len(episode_ids)}\n")
    for issue in sorted(response_quality_issues, key=lambda x: x["f1"])[:15]:
        lines.append(f"- **{issue['episode_id']}**: f1={issue['f1']}")
        lines.append(f"  - pred: \"{issue['pred_text']}\"")
        lines.append(f"  - ref: \"{issue['ref_text']}\"")
    lines.append("")

    # Prompt 调优建议
    lines.append("## 6. 下一轮 Prompt 调优建议\n")
    lines.append("### 6.1 机制分类")
    low_acc_mechs = [mech for mech in mechanism_total
                     if mechanism_correct.get(mech, 0) / max(mechanism_total[mech], 1) < 0.5]
    if low_acc_mechs:
        lines.append(f"- 低准确率机制需要补 few-shot: **{', '.join(low_acc_mechs)}**")
    lines.append("- 当前 few-shot 中缺少 `comparison_superiority` 和 `scarcity_flex` 的示例，建议补充")
    lines.append("- 机制定义需要更强调区分边界，特别是 `understated_flex` vs `faux_modesty` vs `humble_complaint`")
    lines.append("")

    lines.append("### 6.2 策略选择")
    lines.append("- `light_acknowledgment` 过度使用（占比过高），需要在 prompt 中强调何时应选择其他策略")
    lines.append("- `validate` 策略使用不足，few-shot 中可增加 validate 示例")
    lines.append("- 对于 `online_peer` 关系和 `community_peer` 角色，应更倾向 `humor_tease` / `ask_followup`")
    lines.append("")

    lines.append("### 6.3 风险标签")
    lines.append("- **关键问题**: risk_assessment 中几乎不包含官方风险标签关键词，导致 risk_label_f1 接近 0")
    lines.append("- 建议在 prompt 中明确要求 risk_assessment 包含以下关键词之一: sycophancy, preachiness, misrecognition, strategy_inconsistency, context_insensitivity, over_coldness")
    lines.append("- 在 few-shot 示例的 risk_assessment 字段中显式使用这些关键词")
    lines.append("")

    lines.append("### 6.4 回复质量")
    lines.append("- response_text 与 reference 的 token F1 极低(0.48%)，说明回复风格与金标差异大")
    lines.append("- 中文口语化回复 vs 英文 reference 的语言差异是主因，需确认是否应生成英文回复")
    lines.append("- 考虑将 response_text 的语言与输入语言匹配（英文输入 → 英文回复）")
    lines.append("")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Report saved to {output_path}")


if __name__ == "__main__":
    main()
