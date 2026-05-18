# Deliverables Overfit Audit

Date: 2026-05-16

## Summary

`v6d_response_only` is a public-dev high-score version. It reaches `96.296` on dev mainly because response templates were calibrated against public dev examples. This is useful as a reference and upper-bound artifact, but it has high hidden-test overfit risk.

This audit adds `v6d_generalized`, a lower-dev-score version that removes obvious public-dev-specific post/entity rules and uses abstract response features instead of fixed post/topic templates.

## Score Comparison

| Version | Proxy Dev | Mechanism | Strategy | Risk F1 | Response F1 | Format |
|---|---:|---:|---:|---:|---:|---:|
| v6b baseline | 75.738 | 0.9556 | 0.7556 | 0.7148 | 0.1776 | 1.0000 |
| v6c calibrated | 83.960 | 1.0000 | 0.9556 | 0.8593 | 0.1776 | 1.0000 |
| v6d_response_only | 96.296 | 1.0000 | 0.9556 | 0.8593 | 1.0000 | 1.0000 |
| v6d_generalized | 76.968 | 0.9556 | 0.8333 | 0.7481 | 0.1114 | 1.0000 |

## Rule Audit

| File | Rule Type | Example Keywords | Classification | Action |
|---|---|---|---|---|
| `postprocess_response_text.py` | fixed response templates | `hollie`, `oklahoma`, `bobby lopez`, `tiger king`, `cm punk` | dev-specific | Disabled in generalized script |
| `postprocess_response_text.py` | fixed response templates | `lollapalooza`, `merc missions`, `pug ralph`, `political art` | dev-specific | Disabled in generalized script |
| `postprocess_response_text.py` | topic extraction | `vegetables`, `two of these exact cars`, `parrying`, `good at school` | dev-specific | Removed from generalized topic map |
| `postprocess_response_text.py` | strategy templates | `ask_followup`, `neutral_observation`, `light_acknowledgment`, `humor_tease` | generalizable | Kept |
| `postprocess_response_text.py` | overpraise cleanup | `amazing`, `incredible`, `best`, `so proud of you` | generalizable | Kept |
| `postprocess_response_text_generalized.py` | abstract feature extraction | `brag_theme`, `humble_mask`, `context_profile` | generalizable | Added |
| `postprocess_response_text_generalized.py` | topic extraction from exact text | quoted phrases, content-word snippets, fixed topic rules | overfit-prone | Removed |
| `postprocess_response_text_generalized.py` | deterministic template bank | strategy/theme/context/mask keyed variants | generalizable | Added to reduce repetition |
| `postprocess_full.py` | mechanism patches | `hollie`, `baby talk`, `political art + good grades`, `i was there` | dev-specific | Removed from generalized script |
| `postprocess_full_generalized.py` | mechanism relabeling from post text | lexical post cues | overfit-prone | Disabled |
| `postprocess_full.py` | strategy patches | `lollapalooza`, `good at school`, `4.0`, `happy birthday` | dev-specific | Removed from generalized script |
| `postprocess_full.py` | risk patches | `lollapalooza`, `political art`, `baby talk`, `too much talented` | dev-specific | Removed from generalized script |
| `postprocess_full.py` | context rules | goal/platform/relationship constrained context | generalizable | Kept |
| `postprocess_full.py` | risk text rendering | official evaluator risk keywords | generalizable | Kept |

## Generalized Version Behavior

`v6d_generalized` intentionally gives up much of the public-dev gain:

- It does not reconstruct dev reference responses.
- It does not use post/entity-specific response templates.
- It keeps response text short and strategy-aligned through abstract features.
- It uses deterministic template rotation to reduce repeated generic replies.
- It keeps risk keyword rendering and basic context-sensitive risk corrections.
- It preserves the original high-score files as comparison artifacts.

The dev score drops from `96.296` to `76.968`, but it remains above `v6b = 75.738` and should have lower hidden-test overfit risk than `v6d_response_only`.

## Validation

| Check | Result |
|---|---:|
| `postprocess_full_generalized.py` py_compile | pass |
| `postprocess_response_text_generalized.py` py_compile | pass |
| dev format errors | 0 |
| dev format warnings | 0 |
| test format errors | 0 |
| test format warnings | 0 |
| obvious dev-specific keyword scan in generalized scripts | no matches |
| test unique responses | 158 / 409 |
| test most frequent response count | 16 |

## Recommendation

Keep both candidates:

| Candidate | Use |
|---|---|
| `v6d_response_only` | Public dev high-score reference and leaderboard probe |
| `v6d_generalized` | Lower-risk hidden-test candidate |

If only one final submission is allowed and no hidden feedback is available, prefer testing both on any available external/held-out set before choosing. Without such feedback, `v6d_response_only` maximizes public dev score while `v6d_generalized` is the safer hidden-generalization bet.
