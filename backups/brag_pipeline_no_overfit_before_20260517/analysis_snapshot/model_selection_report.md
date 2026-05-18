# Model Selection Report

## Current Decision

The user explicitly decided to continue with `qwen3.6-27b` for the current development phase.

Therefore the `<20B` candidate sweep from `NEXT_PHASE_EXECUTION_PLAN.md` is paused. No further `qwen3-14b`, `qwen3-8b`, or `qwen2.5-14b-instruct` dev runs should be launched unless official-track eligibility becomes the priority again.

## Eligibility Note

`qwen3.6-27b` should be treated as a development/reference model, not an official `<=20B` submission model.

Official rules in `PARTICIPATION_RULES.md` state:

- official track requires total parameters `<=20B`;
- closed model APIs are not eligible for the official `<=20B` track;
- any model in the inference path must individually satisfy the parameter rule.

## Existing qwen3.6-27b Dev Results

| run | submission | proxy_dev_score | mechanism_accuracy | strategy_score | risk_label_f1 | response_reference_token_f1 | format errors |
|---|---|---:|---:|---:|---:|---:|---:|
| qwen3.6-27b original | `outputs/dev_submission_multi_v1_qwen36_27b.jsonl` | 61.213 | 0.6222 | 0.6222 | 0.6037 | 0.2019 | 0 |
| qwen3.6-27b rerun | `outputs/dev_submission_multi_v1_qwen36_27b_rerun.jsonl` | 62.805 | 0.6667 | 0.6000 | 0.6259 | 0.2191 | 0 |

## Aborted <20B Trial

An initial `qwen3-14b` trial was attempted through the configured DashScope OpenAI-compatible API. It failed for every row because the provider returned:

```text
parameter.enable_thinking must be set to false for non-streaming calls
```

The trial was stopped after the user clarified to continue with 27B. The failed sidecar error file was removed because it is not part of the selected path.

## Recommendation

Use `qwen3.6-27b` as the current main development model and proceed with qwen3.6-27b-specific bad case analysis or a tightly scoped next experiment.

Do not modify core code or prompt solely for official `<=20B` compatibility until the user reopens that track.
