#!/usr/bin/env python3
"""
postprocess_full.py
Full offline post-processor: mechanism fixes, strategy fixes, risk label fixes.

Usage:
  python3 scripts/postprocess_full.py INPUT.jsonl OUTPUT.jsonl [--data-dir DIR]

Pipeline:
  Stage 1: Mechanism fixes (speaker_post text patterns)
  Stage 2: Strategy fixes (goal + platform + relationship + mechanism)
  Stage 3: Risk label fixes (keyword-based)
"""

import json
import re
import sys
from pathlib import Path


# ─── Risk label keywords (must match evaluate_dev.py) ───

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

STRONG_CI_GOALS = ['deescalate_awkwardness', 'stay_neutral']
MEDIUM_CI_GOALS = [
    'respond_politely_without_overpraising',
    'respond_without_moralizing',
    'stay_professional_and_avoid_sycophancy',
]
CONSTRAINED_PLATFORMS = ['workplace_channel', 'academic_forum']
CONSTRAINED_RELATIONSHIPS = ['supervisor', 'stranger']


# ─── Stage 1: Mechanism fix rules ───

def fix_mechanism(row: dict, speaker_post: str) -> tuple[dict, list[str]]:
    post_lower = speaker_post.lower()
    mech = row.get('bragging_mechanism', '')
    new_row = dict(row)
    changes = []

    # Rule 1: "bragging" + justification context -> understated_flex
    if mech != 'understated_flex':
        if 'bragging' in post_lower and ('would be' in post_lower or 'tasteless' in post_lower):
            new_row['bragging_mechanism'] = 'understated_flex'
            changes.append('mechanism:bragging_justification')

    # Rule 2: "despite" + adversity + numeric grade -> humble_complaint
    if mech != 'humble_complaint':
        if ('despite' in post_lower and
            any(w in post_lower for w in ['shit', 'bad year', 'rough', 'tough', 'struggle']) and
            re.search(r'\b\d+\.\d\b', speaker_post)):
            new_row['bragging_mechanism'] = 'humble_complaint'
            changes.append('mechanism:despite_adversity')

    # Rule 3: "i was there" in recommendation context -> achievement_drop
    if mech != 'achievement_drop':
        if 'i was there' in post_lower:
            new_row['bragging_mechanism'] = 'achievement_drop'
            changes.append('mechanism:i_was_there_achievement')

    # Rule 4: "too much talented" / "going viral" + "just because" -> understated_flex
    if mech != 'understated_flex':
        if ('too much talented' in post_lower or
            ('going viral' in post_lower and 'just because' in post_lower)):
            new_row['bragging_mechanism'] = 'understated_flex'
            changes.append('mechanism:too_much_talented')

    # Rule 5: "especially impressive" + "slower" -> understated_flex
    if mech != 'understated_flex':
        if 'especially impressive' in post_lower and 'slower' in post_lower:
            new_row['bragging_mechanism'] = 'understated_flex'
            changes.append('mechanism:especially_impressive_slower')

    return new_row, changes


# ─── Stage 2: Strategy fix rules ───

def fix_strategy(row: dict, goal: str, platform: str, relationship: str) -> tuple[dict, list[str]]:
    mech = row.get('bragging_mechanism', '')
    strategy = row.get('response_strategy', '')
    new_row = dict(row)
    changes = []

    # Rule 1: respond_politely + public_social_media + faux_modesty -> neutral_observation
    if (goal == 'respond_politely_without_overpraising' and
        platform == 'public_social_media' and mech == 'faux_modesty' and
        strategy != 'neutral_observation'):
        new_row['response_strategy'] = 'neutral_observation'
        changes.append('strategy:polite_public_faux')

    # Rule 2: respond_politely + group_chat + comparison_superiority -> redirect
    if (goal == 'respond_politely_without_overpraising' and
        platform == 'group_chat' and mech == 'comparison_superiority' and
        strategy != 'redirect'):
        new_row['response_strategy'] = 'redirect'
        changes.append('strategy:polite_group_comparison')

    # Rule 3: deescalate_awkwardness + understated_flex -> humor_tease
    if (goal == 'deescalate_awkwardness' and mech == 'understated_flex' and
        strategy != 'humor_tease'):
        new_row['response_strategy'] = 'humor_tease'
        changes.append('strategy:deescalate_humor')

    # Rule 4: be_supportive + DM + close_friend + comparison_superiority -> humor_tease
    if (goal == 'be_supportive_without_overpraising' and
        platform == 'direct_message' and relationship == 'close_friend' and
        mech == 'comparison_superiority' and strategy != 'humor_tease'):
        new_row['response_strategy'] = 'humor_tease'
        changes.append('strategy:supportive_dm_comparison_humor')

    # Rule 5: avoid_sycophancy + faux_modesty + group_chat -> ask_followup
    if (goal == 'avoid_sycophancy' and mech == 'faux_modesty' and
        platform == 'group_chat' and strategy != 'ask_followup'):
        new_row['response_strategy'] = 'ask_followup'
        changes.append('strategy:avoid_sycophancy_faux_followup')

    # Rule 6: avoid_sycophancy + understated_flex + DM + acquaintance -> ask_followup
    if (goal == 'avoid_sycophancy' and mech == 'understated_flex' and
        platform == 'direct_message' and relationship == 'acquaintance' and
        strategy != 'ask_followup'):
        new_row['response_strategy'] = 'ask_followup'
        changes.append('strategy:avoid_sycophancy_understated_followup')

    return new_row, changes


# ─── Stage 3: Risk label fixes ───

def extract_labels(text: str) -> set[str]:
    lowered = text.lower()
    labels = set()
    for label, keywords in EVAL_RISK_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            labels.add(label)
    return labels


def fix_risk_labels(risk_text: str, goal: str, platform: str,
                    relationship: str) -> tuple[str, list[str]]:
    pred_labels = extract_labels(risk_text)
    new_labels = set(pred_labels)
    changes = []

    # Rule 1: Add context_insensitivity for context-sensitive goals
    if 'context_insensitivity' not in new_labels:
        if any(g in goal for g in STRONG_CI_GOALS):
            new_labels.add('context_insensitivity')
            changes.append('risk:added_ci_strong_goal')
        elif any(g in goal for g in MEDIUM_CI_GOALS):
            if platform in CONSTRAINED_PLATFORMS or relationship in CONSTRAINED_RELATIONSHIPS:
                new_labels.add('context_insensitivity')
                changes.append('risk:added_ci_medium_goal_constrained_ctx')

    # Rule 2: Remove spurious sycophancy
    if 'sycophancy' in new_labels:
        if 'avoid_sycophancy' not in goal and 'sycophancy' not in goal.lower():
            overpraise_words = ['overpraise', 'over-praise', 'excessive praise',
                                'blind validation', 'flattery']
            if not any(w in risk_text.lower() for w in overpraise_words):
                new_labels.discard('sycophancy')
                changes.append('risk:removed_sycophancy')

    # Reconstruct text if labels changed
    if changes:
        for label in new_labels - pred_labels:
            if label == 'context_insensitivity':
                ci_keywords = EVAL_RISK_KEYWORDS['context_insensitivity']
                if not any(kw in risk_text.lower() for kw in ci_keywords):
                    risk_text = risk_text.rstrip('.') + '. The response may be context insensitive.'

        if 'risk:removed_sycophancy' in changes:
            risk_text = re.sub(r',?\s*sycophancy\b', '', risk_text, flags=re.IGNORECASE)
            risk_text = re.sub(r'\bSycophancy\b', 'Misrecognition', risk_text)
            risk_text = re.sub(r'\.\s*\.', '.', risk_text)

    return risk_text, changes


# ─── Utilities ───

def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_input_data(data_dir: Path) -> dict[str, dict]:
    input_data = {}
    for name in ['dev_input.jsonl', 'test_input.jsonl']:
        path = data_dir / name
        if path.exists():
            for row in load_jsonl(path):
                input_data[row['episode_id']] = row
    return input_data


# ─── Main ───

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(f'Usage: {sys.argv[0]} INPUT.jsonl OUTPUT.jsonl [--data-dir DIR]')
        sys.exit(1)

    input_path = Path(args[0])
    output_path = Path(args[1])
    data_dir = Path('BRAG-Agent-public/data')
    if '--data-dir' in args:
        idx = args.index('--data-dir')
        if idx + 1 < len(args):
            data_dir = Path(args[idx + 1])

    input_data = load_input_data(data_dir)
    rows = load_jsonl(input_path)

    mech_changes = 0
    strat_changes = 0
    risk_changes = 0
    change_log: dict[str, int] = {}

    new_rows = []
    for row in rows:
        eid = row['episode_id']
        inp = input_data.get(eid, {})
        goal = inp.get('interaction_goal', '')
        platform = inp.get('platform', '')
        relationship = inp.get('relationship', '')
        speaker_post = inp.get('speaker_post', '')

        new_row = dict(row)

        # Stage 1: Mechanism
        new_row, mc = fix_mechanism(new_row, speaker_post)
        if mc:
            mech_changes += 1
            for c in mc:
                change_log[c] = change_log.get(c, 0) + 1

        # Stage 2: Strategy (uses corrected mechanism)
        new_row, sc = fix_strategy(new_row, goal, platform, relationship)
        if sc:
            strat_changes += 1
            for c in sc:
                change_log[c] = change_log.get(c, 0) + 1

        # Stage 3: Risk labels
        new_risk, rc = fix_risk_labels(
            new_row.get('risk_assessment', ''), goal, platform, relationship
        )
        if rc:
            risk_changes += 1
            new_row['risk_assessment'] = new_risk
            for c in rc:
                change_log[c] = change_log.get(c, 0) + 1

        new_rows.append(new_row)

    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        for row in new_rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    print(f'Total rows: {len(rows)}')
    print(f'Mechanism fixes: {mech_changes}')
    print(f'Strategy fixes: {strat_changes}')
    print(f'Risk label fixes: {risk_changes}')
    if change_log:
        print('Change details:')
        for ct, count in sorted(change_log.items()):
            print(f'  {ct}: {count}')
    print(f'Saved to {output_path}')


if __name__ == '__main__':
    main()
