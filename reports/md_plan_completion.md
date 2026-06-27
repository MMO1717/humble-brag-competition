# MD Plan Completion

Source plan: `/Users/mm/Downloads/BRAG-Pipeline-router-提升规划.md`

## Status

| Plan Item | Evidence | Status |
|---|---|---|
| Re-run complete dev and update results | `outputs/dev_20260622_220425_gemma3_12b/dev_eval_report.json`; latest full dev score is `81.775` | Done |
| Build run comparison table | `reports/run_comparison.md` | Done |
| Add local official-like Core/Bloom judge | `src/judges/local_official_like.py`; `scripts/evaluate_local_official_like.py`; report written to `outputs/dev_20260622_153413_gemma3_12b/local_official_like_report.json` | Done |
| Response candidate rerank | Implemented in `src/skills/response_skill.py` with `USE_RESPONSE_CANDIDATE_RERANK`; offline replay lowered proxy from `81.402` to `81.382`, so default is off | Implemented, not enabled |
| Risk control and Bloom guardrail | `risk_control_plan` from `src/skills/risk_skill.py`; included in prompt/debug only, not final JSONL | Done |
| Understanding field template repair | `src/understanding_templates.py`; dynamic `desired_feedback` repair enabled; full dev improves desired-feedback F1 `0.1511 -> 0.2372` and proxy score `81.402 -> 81.775` | Done |
| Final test generation path | `scripts/run_final_test.py`; `--dry-run` verified recommended test config | Ready |

## Current Recommended Config

```python
MEMORY_ROUTER_MODE = "llm_rerank"
USE_RESPONSE_CANDIDATE_RERANK = False
USE_UNDERSTANDING_TEMPLATE_REPAIR = True
UNDERSTANDING_TEMPLATE_REPAIR_FIELDS = ("desired_feedback",)
```

## Verification

```text
python -m pytest tests/test_pipeline.py -q
59 passed

python -m compileall src scripts -q
passed

git diff --check
passed

python scripts/run_final_test.py --dry-run
prints RUN_MODE=test with recommended flags
```

## Final Test Command

```bash
python scripts/run_final_test.py
```

This command runs all 409 test rows and writes `outputs/<run_id>/submission.jsonl`.
