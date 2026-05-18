# Model Candidate Pool

## Eligibility Rules

Source: `PARTICIPATION_RULES.md` and `BRAG-Agent-public/docs/USAGE_GUIDE.md`.

- Official leaderboard model parameter limit: total parameters `<=20B`.
- Dense models count full parameters.
- MoE models count total parameters, not active parameters.
- Every model in an ensemble, cascade, reranker, or rewriter path must individually satisfy `<=20B`.
- Closed model APIs are not eligible for the official `<=20B` track, even if the provider claims the model is small.
- Open-weight local or self-hosted models are eligible when the total parameter count is disclosed and `<=20B`.

Practical implication: DashScope API runs are useful for quick dev comparison, but a final eligible submission should use the same open-weight model locally or in a self-hosted deployment.

## Candidate Models

| model | total params | official <=20B eligible if self-hosted | DashScope/OpenAI-compatible id to try | expected speed | expected cost | enter dev eval | notes |
|---|---:|---|---|---|---|---|---|
| Qwen3-14B | ~14.8B dense | yes | `qwen3-14b` | medium | medium | yes | Strongest Qwen3 dense candidate below 20B. Use non-thinking/instruct behavior if provider supports it. |
| Qwen3-8B | ~8B dense | yes | `qwen3-8b` | fast | low | yes | Good speed/cost candidate; likely weaker reasoning than 14B but safer for latency. |
| Qwen2.5-14B-Instruct | ~14B dense | yes | `qwen2.5-14b-instruct` | medium | medium | yes | Older but stable instruct model; useful as a robustness baseline. |
| Qwen2.5-7B-Instruct | ~7B dense | yes | `qwen2.5-7b-instruct` | fast | low | optional | Backup if Qwen3 models are unavailable or unstable. |
| Qwen3-4B | ~4B dense | yes | `qwen3-4b` | very fast | very low | optional | Likely quality floor check, not first-line candidate. |
| qwen3.6-27b | ~27B / undisclosed >20B development model | no | `qwen3.6-27b` | slow-medium | high | reference only | Current temporary development model; excluded from final candidate selection. |

## Current Decision

User decision on 2026-05-14: continue using `qwen3.6-27b` for the next development phase.

This overrides the immediate `<20B` cross-evaluation plan. The official eligibility note still matters:

- `qwen3.6-27b` is not eligible for the official `<=20B` track as currently understood.
- It remains acceptable as the current development/reference model if the goal is to improve behavior before final track compliance is revisited.
- Do not continue running `<20B` candidate sweeps unless the user explicitly reopens official-track model selection.

## Deferred Dev Eval Plan

If official-track selection is reopened, use this comparison set:

1. `qwen3-14b`
2. `qwen3-8b`
3. `qwen2.5-14b-instruct`

Commands:

```bash
python3 run_multi_agent_official.py --input BRAG-Agent-public/data/dev_input.jsonl --output outputs/dev_submission_model_<safe_model_name>.jsonl --concurrency 5 --model <model_id>
python3 BRAG-Agent-public/scripts/format_checker.py outputs/dev_submission_model_<safe_model_name>.jsonl BRAG-Agent-public/data/dev_input.jsonl
python3 BRAG-Agent-public/scripts/evaluate_dev.py BRAG-Agent-public/data/dev_input.jsonl BRAG-Agent-public/data/dev_gold.jsonl outputs/dev_submission_model_<safe_model_name>.jsonl > outputs/dev_score_report_model_<safe_model_name>.json
```

If a model id is not available through the configured provider, record the failure in `analysis/model_selection_report.md` and do not fabricate metrics.
