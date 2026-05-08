# BRAG-Agent v6 Dev Prompt Tuning Report

## Overview

Three rounds of prompt tuning on dev set (45 episodes), no architecture changes, no training.

## Score Progression

| Metric | v1 | v2 | v3.1 | Best |
|--------|-----|-----|------|------|
| **proxy_dev_score** | **44.6** | **56.1** | **63.8** | **v3.1** |
| mechanism_accuracy | 0.578 | 0.756 | 0.689 | v2 |
| strategy_score | 0.567 | 0.600 | 0.633 | v3.1 |
| risk_label_f1 | 0.044 | 0.170 | 0.611 | v3.1 |
| response_token_f1 | 0.005 | 0.204 | 0.218 | v3.1 |
| preferred_strategy_acc | 0.444 | 0.400 | 0.444 | v1/v3.1 |
| acceptable_strategy_rate | 0.689 | 0.800 | 0.822 | v3.1 |

**Overall gain: +19.2 points (+43%).**

## What Changed Each Round

**v2** — Switched all output to English. Rewrote mechanism definitions with explicit distinction rules and 13 few-shot examples. This unlocked response_token_f1 (+0.199) and improved mechanism_accuracy (+0.178).

**v3.1** — Added risk label reasoning guide (misrecognition as default, context_insensitivity for setting-sensitive cases, sycophancy only when interaction_goal demands it). Updated few-shot risk_assessment to use correct labels. This boosted risk_label_f1 from 0.17 to 0.61.

## Biggest Wins

1. **risk_label_f1: 0.044 → 0.611 (+1276%)** — The model now correctly identifies misrecognition as the primary risk instead of defaulting to sycophancy.
2. **response_token_f1: 0.005 → 0.218 (+4433%)** — English output enabled token overlap with English references.
3. **acceptable_strategy_rate: 0.689 → 0.822** — Better strategy calibration.

## Trade-offs

- mechanism_accuracy peaked at v2 (0.756) but dropped to 0.689 in v3.1. The risk label guide adds cognitive load that slightly hurts mechanism classification. Net score still improves because risk_label_f1 gain (0.44) outweighs mechanism loss (0.07 × 0.30/0.20 weight ratio).

## Remaining Gaps

1. mechanism_accuracy below v2 peak — need to reduce cognitive load
2. response_token_f1 moderate (0.218) — model phrasing more formal than references
3. preferred_strategy_accuracy stagnant (0.444) — still misses exact preferred in 55% of cases

## Files Modified

- `src/system_prompt_sections.py` — Prompt rewrite (English output, risk guide, mechanism defs, few-shot)
- `src/system.py` — User prompt and risk guide integration

## Outputs

- `outputs/dev_submission_v2.jsonl` / `dev_score_report_v2.json`
- `outputs/dev_submission_v3_1.jsonl` / `dev_score_report_v3_1.json`
- `analysis/dev_bad_cases_v2.md` / `dev_bad_cases_v3.md`
