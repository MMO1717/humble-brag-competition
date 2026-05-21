# Overfit Risk Audit

更新时间：2026-05-21

## Scope

本审计覆盖当前 Phase 6 冻结候选：

```text
source_run_id: dev__20260521_190335_066__llm_glm4_9b_skillflow__full
candidate_name: skillflow_v1_fewshot_active_empty_memory
```

## Audit Checklist

| Risk item | Result | Evidence / note |
| --- | --- | --- |
| `dev_gold.jsonl` 是否进入推理链 | No runtime inference use found | `dev_gold.jsonl` is used by `scripts/evaluate_dev.py` and `humble_brag/error_analyzer.py`; `runner.py` passes it only after submissions are written for dev evaluation/error analysis. |
| 是否存在 episode_id 级 runtime 规则 | No episode-specific runtime rule found | `episode_id` is copied and traced; no `if episode_id == ...` style rule was found in runtime modules. Candidate memory source metadata contains episode ids but was not injected. |
| 是否使用 `acceptable_strategies` / `preferred_strategy` 参与 runtime | No runtime inference use found | These fields appear in evaluator/error-analysis/candidate-generation paths, not in SkillFlow generation prompts. |
| candidate memory 是否进入 final chain | No | Frozen source run has `candidate_memory_count=0`, `memory_used_count=0`. Later runs had candidate files present, but `memory_mode=active` and `active_memory_count=0`; trace reports `memory_used_count=0`. |
| 是否使用 `active_plus_candidate` 作为 final | No | Phase 6 did not run or recommend `active_plus_candidate`. |
| 是否存在 public-dev 特化 keyword hacks | No direct dev-id rule found; some generalized postprocess/risk keywords exist | Risk labels and anti-sycophancy filters are generalized task rules. No episode-level or gold-derived keyword rule is frozen. |
| test mode 是否依赖 gold | No | test runs do not call `evaluate_dev.py`; dry run generated format-valid output with `dev_eval_returncode=null`. |
| 是否把 public dev proxy 当 hidden-test 保证 | No | Readiness recommendation explicitly separates public dev proxy from hidden-test risk. |

## Allowed Gold Usage

The following uses are acceptable and were observed:

- Offline dev evaluation after `submission.jsonl` is generated.
- Error analysis after a dev run is complete.
- Candidate memory generation for review only.
- Documentation of metrics.

## Disallowed Gold Usage Check

No evidence was found that dev gold is used in:

- SkillFlow inference prompts.
- Runtime decision rules.
- test mode generation.
- Active memory injection for the frozen source run.

## Candidate Memory Status

Current repository has candidate memory files:

```text
agent_memory/candidate/memory_candidates.jsonl
agent_memory/candidate/candidate_review.md
```

They remain candidate-only. Phase 6 did not promote them. The frozen candidate should not use `active_plus_candidate`.

## Residual Overfit Risks

- Few-shot retrieves from official train data. This is allowed as a general method, but it should be documented because it is part of the strongest source configuration.
- `error_analyzer.py` can generate candidate memory after dev runs. This is offline and not part of frozen inference unless memory is promoted later.
- Public dev proxy score may still reward patterns that do not transfer to hidden Core + Bloom evaluation.

## Audit Conclusion

Status: pass with caveats.

The frozen candidate is submission-ready from a leakage-control perspective only if candidate memory remains unpromoted and final inference avoids `active_plus_candidate`. The score should still be treated as public-dev proxy evidence, not hidden-test proof.

