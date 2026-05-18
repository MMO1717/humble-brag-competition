# v6e Generalized Report

Date: 2026-05-16

## Summary

`v6e_generalized` extends `v6d_generalized` without restoring public-dev-specific rules. The change adds a local paper-rubric social judge, verify-first response rewriting, a larger abstract response template pool, and a synthetic non-dev stress set.

The version is not designed to chase public dev reference overlap. It is intended as a lower-overfit hidden-test candidate.

## Architecture Delta

| Layer | v6d_generalized | v6e_generalized |
|---|---|---|
| Label layer | `postprocess_full_generalized.py` | unchanged |
| Response generation | abstract `strategy + theme + context + mask` templates | abstract templates plus stable slot combinations |
| Judge | none | local social rubric judge |
| Rewrite | every row gets one generated template | only hard judge issues trigger one safe rewrite |
| Stress validation | dev/test only | dev/test plus 80-row synthetic non-dev stress set |

## Dev Score

| Version | Proxy Dev | Mechanism | Strategy | Risk F1 | Response F1 | Format |
|---|---:|---:|---:|---:|---:|---:|
| v6b baseline | 75.738 | 0.9556 | 0.7556 | 0.7148 | 0.1776 | 1.0000 |
| v6d_generalized | 76.968 | 0.9556 | 0.8333 | 0.7481 | 0.1114 | 1.0000 |
| v6e_generalized | 76.894 | 0.9556 | 0.8333 | 0.7481 | 0.1065 | 1.0000 |

## Gate Check

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| dev format errors | 0 | 0 | pass |
| test format errors | 0 | 0 | pass |
| dev proxy | >= 75.738 | 76.894 | pass |
| test unique responses | >= 150 / 409 | 262 / 409 | pass |
| test most frequent response count | <= 20 | 11 | pass |
| dev exact reference response | 0 / 45 | 0 / 45 | pass |
| dev-specific keyword scan | 0 high-risk matches | 0 | pass |
| mechanism accuracy | not below 0.9556 | 0.9556 | pass |
| strategy score | not below 0.8333 | 0.8333 | pass |
| risk F1 | not below 0.7481 | 0.7481 | pass |

## Social Rubric

| Split | Rows | Hard Issue Rows | Soft Issue Rows | Avg Context Fit | Avg Strategy Fit | Avg Naturalness |
|---|---:|---:|---:|---:|---:|---:|
| dev | 45 | 0 | 0 | 2.000 / 2 | 2.000 / 2 | 2.000 / 2 |
| test | 409 | 0 | 0 | 2.000 / 2 | 2.000 / 2 | 2.000 / 2 |
| stress | 80 | 0 | 0 | 2.000 / 2 | 2.000 / 2 | 2.000 / 2 |

## Stress Set

The synthetic stress set contains 80 rows:

- 8 mechanisms.
- 5 abstract examples per mechanism.
- 2 context variants per example.
- No public dev entities, fixed public dev phrases, or reference-like answers.

Results:

| Check | Result |
|---|---:|
| stress format errors | 0 |
| stress unique responses | 51 / 80 |
| stress most frequent response count | 7 |
| stress social hard issues | 0 |
| stress social soft issues | 0 |

## Recommendation

Keep `v6e_generalized` as the current no-overfit hidden-test candidate. It trades a tiny dev proxy drop from `v6d_generalized` for much stronger response diversity and an explicit social-rubric verification layer.
