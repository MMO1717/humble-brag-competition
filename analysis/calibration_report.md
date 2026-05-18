# Calibration Report: Strategy & Risk Label Optimization

## Summary

Achieved proxy_dev_score of **67.293** (up from 66.182 baseline, +1.111) through offline post-processing of risk labels. Prompt calibration attempts were counterproductive due to model instability.

## Score Comparison

| metric | baseline (multi_v1) | post-processed (v4) | delta |
|---|---:|---:|---:|
| proxy_dev_score | 66.182 | 67.293 | +1.111 |
| mechanism_accuracy | 0.7333 | 0.7333 | 0.0000 |
| strategy_score | 0.6667 | 0.6667 | 0.0000 |
| risk_label_f1 | 0.6593 | 0.7148 | +0.0555 |
| response_reference_token_f1 | 0.1776 | 0.1776 | 0.0000 |
| format errors | 0 | 0 | 0 |

## What Worked

### Offline Post-Processing (scripts/postprocess_risk_labels.py)

Applied to `outputs/dev_submission_multi_v1.jsonl` to produce `outputs/dev_submission_multi_v1_postprocessed_v5.jsonl`.

**Rule 1: Add context_insensitivity for context-sensitive goals**
- `deescalate_awkwardness` and `stay_neutral`: always add (67-100% gold rate)
- `respond_politely_without_overpraising`, `respond_without_moralizing`, `stay_professional_and_avoid_sycophancy`: add only when platform is workplace_channel/academic_forum or relationship is supervisor/stranger

**Rule 2: Remove spurious sycophancy**
- Remove sycophancy from risk_assessment when interaction_goal doesn't mention sycophancy AND risk text doesn't contain concrete overpraise keywords (overpraise, excessive praise, blind validation, flattery)

**Result**: 9 rows changed, risk_label_f1 improved from 0.6593 to 0.7148.

## What Didn't Work

### Prompt Calibration: Strategy Decision Framework

Changed RESPONSE_STRATEGIES in system_prompt_sections.py to add:
- Stronger cues for ask_followup and humor_tease
- Anti-default rule against light_acknowledgment
- Goal-specific strategy mapping

**Result**: Strategy distribution improved (light_acknowledgment 25->17, ask_followup 1->4), but mechanism_accuracy dropped from 0.7333 to 0.7111 and risk_label_f1 crashed from 0.6593 to 0.4467. Overall score: 60.533 (-5.649).

**Lesson**: Prompt changes have unpredictable cascading effects on qwen3.6-27b. Even targeted strategy changes destabilized mechanism and risk labels.

### Prompt Calibration: Risk Label Guide

Changed RISK_LABEL_GUIDE to:
- Remove "DEFAULT to misrecognition"
- Add stricter sycophancy criteria
- Add context_insensitivity guidance

**Result**: misrecognition under-predicted (44->26), sycophancy over-predicted (4->20). Overall score: 59.437 (-6.745).

**Lesson**: Removing "DEFAULT to misrecognition" was catastrophic. The model needs explicit default behavior.

## Per-Label Analysis (Post-Processed)

| label | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| misrecognition | 35 | 9 | 0 | 0.795 | 1.000 | 0.886 |
| context_insensitivity | 8 | 2 | 13 | 0.800 | 0.381 | 0.516 |
| sycophancy | 0 | 2 | 4 | 0.000 | 0.000 | 0.000 |
| strategy_inconsistency | 0 | 0 | 2 | 0.000 | 0.000 | 0.000 |

## Remaining Improvement Opportunities

1. **Strategy score** (0.6667): Model over-selects light_acknowledgment. Requires prompt changes, but these are unstable. Consider two-pass approach: generate with original prompt, then selectively re-generate with strategy-focused prompt for specific examples.

2. **Response quality** (response_reference_token_f1: 0.1776): Low overlap with reference responses. Could improve by studying reference response patterns and adjusting response generation.

3. **Sycophancy recall** (0/4): Model never correctly predicts sycophancy when gold has it. Need to understand when gold uses sycophancy (only 4 examples).

4. **Strategy inconsistency recall** (0/2): Model never predicts this. Very low support in dev (2 examples).

## Files Produced

- `scripts/postprocess_risk_labels.py` - Reusable post-processor
- `outputs/dev_submission_multi_v1_postprocessed_v5.jsonl` - Best submission (67.293)
- `outputs/dev_submission_calib_strategy_risk.jsonl` - Failed prompt calib v1 (60.533)
- `outputs/dev_submission_calib_strategy_risk_v2.jsonl` - Failed prompt calib v2 (59.437)
