# Trace Sanity Report

更新时间：2026-05-21

## Trace Under Review

```text
outputs/dev__20260521_190335_066__llm_glm4_9b_skillflow__full/debug/trace.jsonl
```

This is the trace for the frozen source run:

```text
source_run_id: dev__20260521_190335_066__llm_glm4_9b_skillflow__full
```

## Sanity Results

| Check | Result |
| --- | ---: |
| trace rows | `45` |
| fallback rows | `0` |
| complete SkillFlow order | `45 / 45` |
| rows with raw_outputs | `45 / 45` |
| rows with normalized_output | `45 / 45` |
| skill_errors | `0` |
| validation_errors | `0` |
| invalid normalized labels | `0` |
| CoT-like text hits in raw outputs | `0` |
| rows with memory_used | `0` |
| total injected memory items | `0` |

Expected SkillFlow order:

```text
MechanismSkill -> UnderstandingSkill -> StrategySkill -> RiskSkill -> ResponseSkill -> ValidatorSkill
```

All 45 rows followed this order.

## Output Distribution

### response_strategy

| Label | Count |
| --- | ---: |
| neutral_observation | 16 |
| light_acknowledgment | 12 |
| redirect | 6 |
| humor_tease | 6 |
| ask_followup | 3 |
| validate | 2 |

### bragging_mechanism

| Label | Count |
| --- | ---: |
| achievement_drop | 13 |
| understated_flex | 12 |
| comparison_superiority | 10 |
| faux_modesty | 4 |
| humble_complaint | 4 |
| self_aware_brag | 2 |

## Sample Checks

| episode_id | skill_trace complete | final strategy | raw outputs present |
| --- | --- | --- | --- |
| `dev_seed_000131_a` | yes | `neutral_observation` | yes |
| `dev_seed_000131_b` | yes | `ask_followup` | yes |
| `dev_seed_000163_a` | yes | `humor_tease` | yes |

## Interpretation

- The trace supports the claim that the source run was a real SkillFlow run, not a fallback-only run.
- No chain-of-thought leakage pattern was detected in raw skill outputs.
- No active or candidate memory was actually injected.
- The strategy distribution is not collapsed to one label.

## Residual Trace Risk

The trace audit checks structure, leakage indicators, and label validity. It does not prove hidden-test generalization.

## 2026-05-21 Frozen Dev/Test 45 Trace Validation

本轮新增检查了 frozen candidate 的最新 dev-45 和 test-45 trace：

```text
outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full/debug/trace.jsonl
outputs/test__20260521_222905_096__llm_glm4_9b_skillflow__max45/debug/trace.jsonl
```

| Check | dev-45 | test-45 |
| --- | ---: | ---: |
| rows | 45 | 45 |
| complete SkillFlow order | 45 | 45 |
| fallback rows | 0 | 0 |
| CoT-like hits | 0 | 0 |
| rows with memory_used | 0 | 0 |
| total memory items injected | 0 | 0 |

Latest dev-45 strategy distribution:

| Label | Count |
| --- | ---: |
| neutral_observation | 16 |
| light_acknowledgment | 12 |
| redirect | 6 |
| humor_tease | 6 |
| ask_followup | 3 |
| validate | 2 |

Latest test-45 strategy distribution:

| Label | Count |
| --- | ---: |
| neutral_observation | 17 |
| light_acknowledgment | 17 |
| redirect | 7 |
| humor_tease | 4 |

Conclusion: both latest validation traces are structurally clean. Active memory path was enabled, but no memory item was injected.
