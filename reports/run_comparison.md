# Run Comparison

This table tracks complete local dev runs used to decide whether a change is kept.

| Run ID | Model | Memory Router | Strategy Score | Risk F1 | Response F1 | Proxy Dev Score | Fallback Count | Main Change | Recommended |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| `dev_20260622_001031_gemma3_12b` | `gemma3:12b` | `function` | 0.8889 | 0.7237 | 0.2098 | 79.733 | n/a | Function memory router baseline | No |
| `dev_20260622_040201_gemma3_12b` | `gemma3:12b` | `llm_rerank` | 0.8889 | 0.7237 | 0.1920 | 79.465 | 0 | Initial LLM memory rerank | No |
| `dev_20260622_153413_gemma3_12b` | `gemma3:12b` | `llm_rerank` | 0.9556 | 0.7548 | 0.1907 | 81.402 | n/a | Strategy/Risk fixes plus LLM memory rerank | Yes |
| `dev_20260622_174046_gemma3_12b` | `gemma3:12b` | `llm_rerank` | 0.9556 | 0.7548 | 0.1956 | 81.475 | 0 | Understanding template repair validated on full dev | Yes |

Decision:

- Keep `MEMORY_ROUTER_MODE = "llm_rerank"` after the latest complete dev run.
- Keep the StrategySkill preferred-strategy and RiskSkill false-positive fixes.
- Keep internal `risk_control_plan`; it is used only by ResponseSkill/debug traces and does not change the submission schema.
- Keep `USE_UNDERSTANDING_TEMPLATE_REPAIR = True` for `desired_feedback`: the full 45-row dev run improves desired-feedback token F1 from 0.1511 to 0.2112, response F1 from 0.1907 to 0.1956, and proxy score from 81.402 to 81.475.
- Do not enable `USE_RESPONSE_CANDIDATE_RERANK` by default: offline simulation changed 2 responses and lowered proxy dev score from 81.402 to 81.382.
- Continue to treat response token F1 as the next main optimization target.

Local official-like judge:

```bash
python scripts/evaluate_local_official_like.py \
  data/dev_input.jsonl \
  outputs/dev_20260622_153413_gemma3_12b/submission.jsonl \
  --output outputs/dev_20260622_153413_gemma3_12b/local_official_like_report.json
```

Latest local official-like result for `dev_20260622_153413_gemma3_12b`:

| Metric | Value |
|---|---:|
| valid_submission | true |
| local_overall_score | 0.9664 |
| understanding_quality | 1.0000 |
| policy_quality | 1.0000 |
| response_quality | 0.9893 |
| consistency_quality | 0.9056 |
| sycophancy | 0.0256 |
| strategy_inconsistency | 0.0500 |
| context_insensitivity | 0.0000 |
| misrecognition | 0.0222 |
| preachiness | 0.0000 |
| over_coldness | 0.0000 |

Main local judge warnings:

- 3 redirect responses are not explicit enough.
- 1 response has praise that may be too strong.

Final test command:

```bash
python scripts/run_final_test.py --dry-run
python scripts/run_final_test.py
```
