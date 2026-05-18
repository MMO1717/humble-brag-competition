# multi_v1 vs multi_v1.2 Mechanism Reranker

## Summary

`multi_v1.2_reranker` adds a mechanism-only reranker after the existing `multi_v1` generator/validator pipeline. The reranker is strictly limited to `achievement_drop` vs `understated_flex` and only overrides `bragging_mechanism` when confidence is `high`.

In this dev run, the reranker triggered 22 times but made 0 overrides. Therefore it produced no direct fixes and no direct harm. The full run scored lower than the stored `multi_v1` rerun because the generator output changed on a fresh API run, not because the reranker changed any labels.

Conclusion: do not keep this exact `multi_v1.2_reranker` as a scoring candidate. It is safe, but too conservative to improve dev.

## 1. Metric Comparison

| metric | multi_v1 rerun | multi_v1.2_reranker | delta |
|---|---:|---:|---:|
| `proxy_dev_score` | 65.309 | 62.970 | -2.339 |
| `mechanism_accuracy` | 0.7111 | 0.6667 | -0.0444 |
| `strategy_score` | 0.6556 | 0.6333 | -0.0223 |
| `risk_label_f1` | 0.6519 | 0.6259 | -0.0260 |
| `response_reference_token_f1` | 0.1885 | 0.1857 | -0.0028 |
| `format_checker errors` | 0 | 0 | 0 |

`multi_v1.2_reranker` fails the retention thresholds:

- `proxy_dev_score > 65.309`: no
- `mechanism_accuracy > 0.7111`: no
- `risk_label_f1 >= 0.6419`: no
- `strategy_score >= 0.6456`: no
- reranker net benefit positive: no

## 2. Reranker Trigger and Override Stats

| stat | value |
|---|---:|
| total rows | 45 |
| triggered | 22 |
| high confidence | 19 |
| medium confidence | 1 |
| low confidence | 2 |
| changed | 0 |
| fixed | 0 |
| harmed | 0 |
| net | 0 |

The reranker was conservative: it frequently returned `high`, but almost always agreed with the generator's original `achievement_drop` or `understated_flex` choice.

## 3. Covered Cases

No samples were covered by the reranker because `changed = 0`.

| episode_id | gold mechanism | original mechanism | reranker mechanism | fixed? | reason |
|---|---|---|---|---|---|
| _none_ | _none_ | _none_ | _none_ | _none_ | _none_ |

## 4. Generator Drift Note

Compared with `outputs/dev_submission_multi_v1_rerun.jsonl`, this fresh run changed 9 mechanism labels:

| episode_id | gold mechanism | multi_v1 rerun | multi_v1.2 run |
|---|---|---|---|
| `dev_seed_000131_a` | `understated_flex` | `achievement_drop` | `understated_flex` |
| `dev_seed_000163_a` | `comparison_superiority` | `understated_flex` | `comparison_superiority` |
| `dev_seed_000163_b` | `comparison_superiority` | `comparison_superiority` | `understated_flex` |
| `dev_seed_000461_a` | `understated_flex` | `understated_flex` | `faux_modesty` |
| `dev_seed_000556_b` | `understated_flex` | `understated_flex` | `achievement_drop` |
| `dev_seed_000691_a` | `understated_flex` | `understated_flex` | `scarcity_flex` |
| `dev_seed_000691_b` | `understated_flex` | `self_aware_brag` | `understated_flex` |
| `dev_seed_000701_b` | `achievement_drop` | `comparison_superiority` | `understated_flex` |
| `dev_seed_000738_a` | `understated_flex` | `understated_flex` | `achievement_drop` |

This drift makes the end-to-end score worse, but it is separate from reranker override quality because the reranker did not change any row.

## 5. Conclusion

Do not retain `multi_v1.2_reranker` as a candidate submission.

The implementation is controlled and format-safe, but the override rule is too strict to produce benefit. The next attempt should either:

- run reranking on the stored `multi_v1_rerun` outputs as an offline postprocess to isolate reranker value, or
- lower the override condition from `high only` to a narrowly defined `high or medium when contextual-boost cues are explicit`, then rerun with a fixed seed/model setting if available.

Do not expand reranking beyond `achievement_drop` vs `understated_flex` until this pair shows positive net benefit.
