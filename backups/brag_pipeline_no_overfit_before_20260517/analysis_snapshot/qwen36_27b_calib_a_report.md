# qwen3.6-27b Calibration A Report

## Decision From Adaptation Analysis

The adaptation analysis identified one stable strategy pattern: qwen3.6-27b overused `light_acknowledgment` and underused `humor_tease` / `ask_followup`, causing most of the strategy-score drop.

This met the implementation gate:

- stable pattern: yes
- affects at least 2 dev samples: yes
- proposed calibration under 120 English words: yes
- implementation limited to `src/system_prompt_sections.py`: yes

## Code Change

Calibration A temporarily added one strategy rule near the existing response-strategy decision framework:

> when playful/community context or close_friend/group_chat banter invites curiosity, do not default to light_acknowledgment; prefer humor_tease for joking brags and ask_followup when the speaker is fishing for a story. Keep praise bounded, especially under avoid_sycophancy.

The change was evaluated and then reverted because it failed the retention criteria.

## Metrics Comparison

| metric | baseline qwen-turbo/current | qwen3.6-27b original | qwen36_27b_calib_a |
|---|---:|---:|---:|
| `proxy_dev_score` | 64.180 | 61.213 | 63.882 |
| `mechanism_accuracy` | 0.6667 | 0.6222 | 0.7333 |
| `strategy_score` | 0.6889 | 0.6222 | 0.5667 |
| `risk_label_f1` | 0.6111 | 0.6037 | 0.6111 |
| `response_reference_token_f1` | 0.2120 | 0.2019 | 0.2218 |
| `format_checker errors` | 0 | 0 | 0 |
| `rewrite triggered` | 1 | 0 | 1 |

Calibration A improves total score by `+2.669` over qwen3.6-27b original, but this is not attributable to the targeted strategy fix. The biggest gain is mechanism accuracy, likely from normal run variance. Strategy score regresses by `-0.0555`.

## Targeted Error Pattern Result

The target was to reduce generic `light_acknowledgment` and recover `humor_tease` / `ask_followup` in playful or curiosity-inviting contexts.

| strategy | qwen3.6-27b original | calib_a | delta |
|---|---:|---:|---:|
| `light_acknowledgment` | 31 | 32 | +1 |
| `humor_tease` | 3 | 5 | +2 |
| `ask_followup` | 1 | 2 | +1 |
| `neutral_observation` | 9 | 5 | -4 |
| `redirect` | 1 | 1 | 0 |

Preferred-strategy hit rates:

| preferred strategy | qwen3.6-27b original | calib_a | result |
|---|---:|---:|---|
| `humor_tease` | 2/7 | 3/7 | improved |
| `ask_followup` | 1/8 | 1/8 | unchanged |
| `light_acknowledgment` | 11/13 | 10/13 | worse |
| `neutral_observation` | 4/10 | 3/10 | worse |

Strategy changes from original to calib_a:

| episode_id | preferred | original strategy | calib_a strategy | score delta |
|---|---|---|---|---:|
| `dev_seed_000131_b` | `ask_followup` | `neutral_observation` | `light_acknowledgment` | -0.5 |
| `dev_seed_000163_a` | `humor_tease` | `neutral_observation` | `light_acknowledgment` | -0.5 |
| `dev_seed_000163_b` | `humor_tease` | `light_acknowledgment` | `ask_followup` | 0.0 |
| `dev_seed_000274_a` | `neutral_observation` | `neutral_observation` | `light_acknowledgment` | -1.0 |
| `dev_seed_000319_a` | `light_acknowledgment` | `light_acknowledgment` | `humor_tease` | -1.0 |
| `dev_seed_000386_c` | `ask_followup` | `neutral_observation` | `light_acknowledgment` | -0.5 |
| `dev_seed_000402_a` | `humor_tease` | `light_acknowledgment` | `humor_tease` | +1.0 |

Net targeted strategy effect is negative.

## Regression Check

Success criteria:

- `format_checker = 0 errors`: pass
- `proxy_dev_score > qwen3.6-27b original + 1.0`: pass (`63.882` vs `62.213` threshold)
- `mechanism_accuracy` or `strategy_score` clearly improves: pass for mechanism, fail for targeted strategy
- `risk_label_f1` does not drop more than 1pp: pass
- `response_reference_token_f1` does not drop more than 1pp: pass

Despite meeting the numeric score gate, the targeted calibration did not work. It harmed strategy selection, which was the intended repair target.

## Keep or Revert

Revert.

Reason: the improvement is not aligned with the intended single-variable change. The target metric (`strategy_score`) dropped from `0.6222` to `0.5667`, and the rule caused collateral damage to `neutral_observation` and correct `light_acknowledgment` cases.

The prompt change was reverted after evaluation.

## Next Recommendation

Do not keep Calibration A.

Next attempt should avoid broad "prefer humor_tease / ask_followup" wording. A safer experiment would target one narrower strategy boundary:

- In close-friend or group-chat contexts, use `humor_tease` only when the post contains explicit joking/self-aware brag cues.
- Do not mention `ask_followup` in the same calibration rule.
- Preserve `neutral_observation` for `stay_neutral` and public/forum contexts.

Alternatively, pause qwen3.6-27b prompt tuning because the model may exceed the final `<20B` constraint noted in the next-step prompt.
