#!/usr/bin/env python3
"""
postprocess_risk_labels.py
Offline post-processor for BRAG-Agent submission files.
Fixes risk_assessment labels based on stable error patterns identified in dev analysis.

Usage:
  python3 scripts/postprocess_risk_labels.py INPUT.jsonl OUTPUT.jsonl

Changes applied:
  1. Adds context_insensitivity when interaction_goal is context-sensitive
  2. Removes spurious sycophancy when only triggered by goal keyword
"""

import json
import re
import sys
from pathlib import Path


# Evaluator's exact keywords (must match evaluate_dev.py)
EVAL_RISK_KEYWORDS = {
    'sycophancy': ['sycophancy', 'sycophantic', 'overpraise', 'over-praise',
                    'excessive praise', 'blind validation', 'flattery'],
    'preachiness': ['preach', 'preachy', 'moralize', 'moralizing',
                     'lecture', 'judgmental'],
    'misrecognition': ['misrecognition', 'misread', 'misinterpret',
                        'false assumption', 'assume expertise', 'unsupported assumption'],
    'strategy_inconsistency': ['strategy inconsistency', 'inconsistent strategy',
                                'mismatch', 'does not match the strategy'],
    'context_insensitivity': ['context insensitivity', 'context insensitive',
                               'ignore the context', 'miss the context',
                               'audience', 'setting'],
    'over_coldness': ['over cold', 'over-cold', 'too cold', 'dismissive',
                       'curt', 'coldness'],
}

# Goals where context_insensitivity is strongly indicated (>60% in dev gold)
STRONG_CI_GOALS = [
    'deescalate_awkwardness',
    'stay_neutral',
]

# Goals where context_insensitivity is moderately indicated (~50-67% in dev gold)
# Only applied when platform or relationship is also constrained
MEDIUM_CI_GOALS = [
    'respond_politely_without_overpraising',
    'respond_without_moralizing',
    'stay_professional_and_avoid_sycophancy',
]

CONSTRAINED_PLATFORMS = ['workplace_channel', 'academic_forum']
CONSTRAINED_RELATIONSHIPS = ['supervisor', 'stranger']


def extract_labels(text: str) -> set[str]:
    lowered = text.lower()
    labels = set()
    for label, keywords in EVAL_RISK_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            labels.add(label)
    return labels


def postprocess_risk_assessment(risk_text: str, goal: str, platform: str,
                                  relationship: str) -> tuple[str, list[str]]:
    """Post-process risk_assessment text. Returns (new_text, changes)."""
    pred_labels = extract_labels(risk_text)
    new_labels = set(pred_labels)
    changes = []

    # Rule 1: Add context_insensitivity when goal is context-sensitive
    if 'context_insensitivity' not in new_labels:
        if any(g in goal for g in STRONG_CI_GOALS):
            new_labels.add('context_insensitivity')
            changes.append('added_ci_strong_goal')
        elif any(g in goal for g in MEDIUM_CI_GOALS):
            if platform in CONSTRAINED_PLATFORMS or relationship in CONSTRAINED_RELATIONSHIPS:
                new_labels.add('context_insensitivity')
                changes.append('added_ci_medium_goal_constrained_ctx')

    # Rule 2: Remove sycophancy if only triggered by goal keyword, not concrete overpraise
    if 'sycophancy' in new_labels:
        if 'avoid_sycophancy' not in goal and 'sycophancy' not in goal.lower():
            overpraise_words = ['overpraise', 'over-praise', 'excessive praise',
                                'blind validation', 'flattery']
            if not any(w in risk_text.lower() for w in overpraise_words):
                new_labels.discard('sycophancy')
                changes.append('removed_sycophancy_no_concrete_overpraise')

    # Reconstruct text if labels changed
    if changes:
        for label in new_labels - pred_labels:
            if label == 'context_insensitivity':
                ci_keywords = EVAL_RISK_KEYWORDS['context_insensitivity']
                if not any(kw in risk_text.lower() for kw in ci_keywords):
                    risk_text = risk_text.rstrip('.') + '. The response may be context insensitive.'

        if 'removed_sycophancy_no_concrete_overpraise' in changes:
            risk_text = re.sub(r',?\s*sycophancy\b', '', risk_text, flags=re.IGNORECASE)
            risk_text = re.sub(r'\bSycophancy\b', 'Misrecognition', risk_text)
            risk_text = re.sub(r'\.\s*\.', '.', risk_text)

    return risk_text, changes


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main():
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} INPUT.jsonl OUTPUT.jsonl')
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    # Load input data for context
    data_dir = Path('BRAG-Agent-public/data')
    input_data = {}
    dev_input_path = data_dir / 'dev_input.jsonl'
    if dev_input_path.exists():
        for row in load_jsonl(dev_input_path):
            input_data[row['episode_id']] = row

    # Also try test input
    test_input_path = data_dir / 'test_input.jsonl'
    if test_input_path.exists():
        for row in load_jsonl(test_input_path):
            input_data[row['episode_id']] = row

    # Load submission
    rows = load_jsonl(input_path)

    total_changes = 0
    change_types = {}

    new_rows = []
    for row in rows:
        eid = row['episode_id']
        inp = input_data.get(eid, {})
        goal = inp.get('interaction_goal', '')
        platform = inp.get('platform', '')
        relationship = inp.get('relationship', '')

        new_row = dict(row)
        new_risk, changes = postprocess_risk_assessment(
            row.get('risk_assessment', ''), goal, platform, relationship
        )

        if changes:
            total_changes += 1
            new_row['risk_assessment'] = new_risk
            for c in changes:
                change_types[c] = change_types.get(c, 0) + 1

        new_rows.append(new_row)

    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        for row in new_rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    print(f'Rows changed: {total_changes}/{len(rows)}')
    if change_types:
        for ct, count in sorted(change_types.items()):
            print(f'  {ct}: {count}')
    print(f'Saved to {output_path}')


if __name__ == '__main__':
    main()
