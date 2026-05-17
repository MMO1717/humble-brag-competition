# BRAG v6d/v6e Runnable Package

This package keeps two families of submissions:

| Version | Purpose | Dev Proxy | Hidden-Test Risk |
|---|---|---:|---|
| `v6d_response_only` | public dev high-score reference | 96.296 | high |
| `v6d_generalized` | lower-overfit generalized candidate | 76.968 | lower |
| `v6e_generalized` | current no-overfit generalized candidate | 76.894 | lower |

`v6e_generalized` is the recommended hidden-test candidate in this package. It keeps the generalized label layer, adds a local social-rubric judge, rewrites only when hard issues are detected, and uses abstract template slots to reduce response repetition.

## Important Files

| Path | Purpose |
|---|---|
| `scripts/postprocess_full.py` | original high public-dev postprocessing |
| `scripts/postprocess_response_text.py` | original high public-dev response-text postprocessing |
| `scripts/postprocess_full_generalized.py` | no-overfit generalized label/risk layer |
| `scripts/postprocess_response_text_generalized.py` | v6d generalized response layer |
| `scripts/postprocess_response_text_v6e_generalized.py` | v6e generalized response layer |
| `scripts/judge_social_rubric.py` | local social pragmatic judge |
| `scripts/build_no_overfit_stress_set.py` | synthetic non-dev stress-set builder |
| `outputs/test_submission_v6e_generalized.jsonl` | recommended generalized test submission |
| `analysis/v6e_generalized_report.md` | v6e score, gates, and stress-set report |

## Rebuild v6e

Put the official data files under `BRAG-Agent-public/data/` if they are not already present:

- `dev_input.jsonl`
- `dev_gold.jsonl`
- `test_input.jsonl`

Then run:

```bash
python3 scripts/postprocess_full_generalized.py \
  outputs/dev_submission_v6b.jsonl \
  outputs/dev_submission_v6c_generalized.jsonl \
  --data-dir BRAG-Agent-public/data

python3 scripts/postprocess_response_text_v6e_generalized.py \
  outputs/dev_submission_v6c_generalized.jsonl \
  BRAG-Agent-public/data/dev_input.jsonl \
  outputs/dev_submission_v6e_generalized.jsonl \
  --report

python3 scripts/postprocess_full_generalized.py \
  outputs/test_submission_v6b.jsonl \
  outputs/test_submission_v6c_generalized.jsonl \
  --data-dir BRAG-Agent-public/data

python3 scripts/postprocess_response_text_v6e_generalized.py \
  outputs/test_submission_v6c_generalized.jsonl \
  BRAG-Agent-public/data/test_input.jsonl \
  outputs/test_submission_v6e_generalized.jsonl \
  --report
```

## Validate

```bash
python3 BRAG-Agent-public/scripts/evaluate_dev.py \
  BRAG-Agent-public/data/dev_input.jsonl \
  BRAG-Agent-public/data/dev_gold.jsonl \
  outputs/dev_submission_v6e_generalized.jsonl

python3 BRAG-Agent-public/scripts/format_checker.py \
  outputs/dev_submission_v6e_generalized.jsonl \
  BRAG-Agent-public/data/dev_input.jsonl

python3 BRAG-Agent-public/scripts/format_checker.py \
  outputs/test_submission_v6e_generalized.jsonl \
  BRAG-Agent-public/data/test_input.jsonl
```

## Social Rubric Check

```bash
python3 scripts/judge_social_rubric.py \
  BRAG-Agent-public/data/test_input.jsonl \
  outputs/test_submission_v6e_generalized.jsonl \
  analysis/v6e_generalized_social_rubric_test_report.md
```

## Stress Set

```bash
python3 scripts/build_no_overfit_stress_set.py \
  analysis/v6e_stress_input.jsonl \
  analysis/v6e_stress_seed_submission.jsonl

python3 scripts/postprocess_response_text_v6e_generalized.py \
  analysis/v6e_stress_seed_submission.jsonl \
  analysis/v6e_stress_input.jsonl \
  analysis/v6e_stress_submission_v6e.jsonl \
  --report

python3 BRAG-Agent-public/scripts/format_checker.py \
  analysis/v6e_stress_submission_v6e.jsonl \
  analysis/v6e_stress_input.jsonl

python3 scripts/judge_social_rubric.py \
  analysis/v6e_stress_input.jsonl \
  analysis/v6e_stress_submission_v6e.jsonl \
  analysis/v6e_stress_social_rubric_report.md
```

## Current v6e Checks

| Check | Result |
|---|---:|
| dev proxy | 76.894 |
| dev format errors | 0 |
| test format errors | 0 |
| test unique responses | 262 / 409 |
| test most frequent response count | 11 |
| dev exact reference response | 0 / 45 |
| dev/test social hard issues | 0 |
| stress format errors | 0 |
| stress social hard issues | 0 |

`.env` is not included. Use `.env.example` as the template if you need to regenerate base model outputs.
