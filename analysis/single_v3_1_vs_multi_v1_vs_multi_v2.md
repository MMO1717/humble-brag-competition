# Three-Version Comparison Report: single_v3_1 vs multi_v1 vs multi_v2

## Overview

| Version | Architecture | proxy_dev_score |
|---------|-------------|----------------|
| **single_v3_1** | Single BraggingResponseAgent (v3.1 prompt) | **63.82** |
| **multi_v1** | Generator -> Validator -> Conditional Rewriter | **66.182** |
| **multi_v2** | Understander -> Responder (two-stage) | **58.303** |

**Recommended submission: multi_v1** (highest dev proxy score, lowest risk).

## Files Changed

### New files (multi_v2)
- `src/TwoStageBraggingAgent.py` - Two-stage pipeline implementation
- `run_two_stage_official.py` - Runner script
- `outputs/dev_submission_multi_v2.jsonl` - Dev output (45 episodes)
- `outputs/dev_score_report_multi_v2.json` - Dev score report
- `analysis/single_v3_1_vs_multi_v1_vs_multi_v2.md` - This report

### Unchanged files
- `src/BraggingResponseAgent.py` - Used as fallback
- `src/MultiAgentBraggingAgent.py` - multi_v1 pipeline (untouched)
- `src/official_validator.py` - Shared validator (untouched)
- `run_multi_agent_official.py` - multi_v1 runner (untouched)
- `outputs/dev_submission_multi_v1.jsonl` - Preserved

## Detailed Metrics

| Metric | single_v3_1 | multi_v1 | multi_v2 | v2 vs v1 |
|--------|------------|----------|----------|----------|
| **proxy_dev_score** | 63.82 | **66.182** | 58.303 | **-7.879** |
| mechanism_accuracy | 0.6889 | **0.7333** | 0.5333 | **-0.2000** |
| strategy_score | 0.6333 | **0.6667** | 0.5556 | **-0.1111** |
| preferred_strategy_accuracy | 0.4444 | **0.4889** | 0.3556 | -0.1333 |
| acceptable_strategy_rate | 0.8222 | **0.8444** | 0.7556 | -0.0888 |
| risk_label_f1 | 0.6111 | 0.6593 | **0.6741** | **+0.0148** |
| response_reference_token_f1 | **0.2176** | 0.1776 | 0.1807 | +0.0031 |
| format_checker errors | 0 | 0 | 0 | 0 |

## Format Checker

All three versions pass format_checker with 0 errors.

## Pipeline Statistics (multi_v2)

- **45/45 episodes completed successfully**
- **Two-stage OK (no rewrite needed)**: 45/45 (100%)
- **Rewrite triggered**: 0
- **Fallback to single-agent**: 0
- **Understand retries**: 0
- **Response retries**: 0

## Why multi_v2 Underperformed

### Problem 1: Responder Strategy Bias (Critical)

The Responder agent is severely biased toward `light_acknowledgment`:

| Strategy | Gold Preferred | multi_v1 | multi_v2 |
|----------|---------------|----------|----------|
| light_acknowledgment | 13 | 25 | **33** |
| neutral_observation | 10 | 10 | 12 |
| humor_tease | 7 | 8 | **0** |
| ask_followup | 8 | 1 | **0** |
| validate | 4 | 0 | **0** |
| redirect | 3 | 1 | **0** |

multi_v2 selected `light_acknowledgment` or `neutral_observation` for **all 45 episodes**. It never chose `humor_tease`, `ask_followup`, `validate`, or `redirect`.

Root cause: The Responder receives only the Understander's 4-field summary (mechanism, intention, desired_feedback, risk), not the original post text. This strips away the tone, personality, and contextual cues needed to select diverse strategies. The Responder defaults to the "safest" strategy when it lacks full context.

### Problem 2: Understander Mechanism Errors (+10 Regressions)

The Understander made 10 mechanism classification errors that multi_v1 got right:

| Episode | v1 (correct) | v2 (wrong) | Gold |
|---------|-------------|------------|------|
| dev_seed_000163_b | comparison_superiority | understated_flex | comparison_superiority |
| dev_seed_000330_a | comparison_superiority | achievement_drop | comparison_superiority |
| dev_seed_000330_b | comparison_superiority | achievement_drop | comparison_superiority |
| dev_seed_000386_a | faux_modesty | comparison_superiority | faux_modesty |
| dev_seed_000386_b | faux_modesty | understated_flex | faux_modesty |
| dev_seed_000386_c | faux_modesty | comparison_superiority | faux_modesty |
| dev_seed_000461_a | understated_flex | comparison_superiority | understated_flex |
| dev_seed_000461_b | understated_flex | comparison_superiority | understated_flex |
| dev_seed_000635_a | faux_modesty | understated_flex | faux_modesty |
| dev_seed_000635_b | faux_modesty | understated_flex | faux_modesty |

Key confusions:
- **faux_modesty vs understated_flex** (5 errors): The Understander struggles to detect self-deprecation signals when they are subtle.
- **comparison_superiority vs achievement_drop** (2 errors): When comparison is implicit rather than explicit.
- **understated_flex vs comparison_superiority** (3 errors): Misidentifying casual mentions as comparisons.

Only 1 case improved: dev_seed_000738_c (comparison_superiority -> understated_flex, which was correct).

### Problem 3: Context Loss in Two-Stage Split

The single-agent BraggingResponseAgent sees the full post text, platform, relationship, agent_role, and interaction_goal simultaneously when making mechanism AND strategy decisions. The two-stage split forces:
1. Understander to classify mechanism without considering response strategy implications
2. Responder to choose strategy without seeing the original post's tone and phrasing

This context loss compounds: a mechanism error in Stage 1 cascades into strategy and response errors in Stage 2.

## What Improved in multi_v2

### risk_label_f1: 0.6593 -> 0.6741 (+2.2%)
The Understander's focused prompt for risk assessment slightly improved risk label detection. This is the only metric where multi_v2 outperforms multi_v1.

### response_reference_token_f1: 0.1776 -> 0.1807 (+1.7%)
Marginal improvement, likely within noise.

## Rewrite / Fallback Rates

| Version | Rewrite Triggered | Rewrite Success | Fallback Used |
|---------|------------------|----------------|---------------|
| multi_v1 | 1/45 (2.2%) | 1/1 (100%) | 0 |
| multi_v2 | 0/45 (0%) | N/A | 0 |

multi_v2 had 0 rewrites because its output always passed format validation (the Understander and Responder prompts enforce enum constraints). However, format compliance is not the same as accuracy.

## Bad Case Analysis

### Mechanism Bad Cases (multi_v2: 21 wrong / 45 = 46.7% error rate)

Worst confusion pairs:
1. **faux_modesty <-> understated_flex** (5 errors): Both involve downplaying, but faux_modesty has explicit self-deprecation while understated_flex is just casual.
2. **achievement_drop <-> comparison_superiority** (5 errors): Achievement drops that implicitly compare to others.
3. **understated_flex <-> comparison_superiority** (4 errors): Casual mentions misread as comparisons.

### Strategy Bad Cases (multi_v2: 11 inacceptable / 45 = 24.4%)

The Responder never selected `humor_tease` (gold preferred 7 times), `ask_followup` (gold preferred 8 times), or `validate` (gold preferred 4 times). This is the single biggest source of strategy errors.

## Conclusion

multi_v2 (two-stage) is **not recommended** as the submission version. The architecture's context loss between stages causes:
1. Severe strategy selection bias (almost only light_acknowledgment/neutral_observation)
2. Increased mechanism classification errors (+10 regressions vs multi_v1)
3. Overall score drop of -7.879 points

**multi_v1 remains the best version** with proxy_dev_score = 66.182, balanced metrics, and minimal rewrite overhead.

### Lessons for Future Iterations

If pursuing two-stage further:
1. **Pass original post text to the Responder** - The Responder needs the speaker's actual words to select tone-appropriate strategies.
2. **Include interaction_goal in Responder prompt** - The goal directly constrains strategy choice.
3. **Consider a softer split** - Instead of hard separation, have the Understander output a "strategy hint" that the Responder can override.
4. **Add few-shot examples to Responder prompt** - Show diverse strategy selections to counteract bias.
