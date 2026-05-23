# Final Readiness Report

更新时间：2026-05-22

## Final Candidate

```text
candidate_name: skillflow_v1_fewshot_active_empty_memory
source_run_id: dev__20260521_221741_731__llm_glm4_9b_skillflow__full
source_output_dir: outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full
```

Frozen command:

```bash
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode dev --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active
```

## Dev Ablation

| Run | Output dir | Key config | Format | Fallback | Parse failure | Invalid label | Proxy score | Mechanism | Strategy | Risk F1 | Response F1 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Heuristic reference | `outputs/dev__20260521_194048_706__heuristic_baseline__full` | heuristic | valid | 0 | 0 | 0 | 49.223 | 0.2667 | 0.6333 | 0.5785 | 0.1324 |
| Static memory prompt | `outputs/dev__20260521_200217_548__llm_glm4_9b__full` | `llm_c_static_memory_v1` | valid | 0 | 0 | 0 | 49.573 | 0.3778 | 0.5444 | 0.5148 | 0.1370 |
| SkillFlow no memory | `outputs/dev__20260521_201215_813__llm_glm4_9b_skillflow__full` | `--use-skillflow --memory-mode no_memory` | valid | 0 | 0 | 0 | 68.111 | 0.7111 | 0.7222 | 0.7296 | 0.1827 |
| SkillFlow active memory | `outputs/dev__20260521_212356_012__llm_glm4_9b_skillflow__full` | `--use-skillflow --use-agent-memory --memory-mode active` | valid | 0 | 0 | 0 | 68.100 | 0.7111 | 0.7222 | 0.7296 | 0.1820 |
| Frozen source run | `outputs/dev__20260521_190335_066__llm_glm4_9b_skillflow__full` | `--use-skillflow --use-fewshot --use-agent-memory --memory-mode active` | valid | 0 | 0 | 0 | 68.780 | 0.7556 | 0.7111 | 0.7296 | 0.1532 |

Discarded invalid run:

```text
outputs/dev__20260521_194309_022__llm_your_model_name__full
```

Reason: sandbox blocked local Ollama access, causing `fallback_count=45` and `api_failure_count=45`.

## Test Dry Runs

Per user instruction, Phase 6 did not run a full 409-row test submission. It ran 45-row dry runs only.

| Run | Output dir | Config | Format | Rows | Fallback | Parse failure | Invalid label |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| Test dry run, no few-shot | `outputs/test__20260521_213329_881__llm_glm4_9b_skillflow__max45` | `--use-skillflow --use-agent-memory --memory-mode active --max-items 45` | valid | 45 | 0 | 0 | 0 |
| Test dry run, frozen candidate | `outputs/test__20260521_214225_439__llm_glm4_9b_skillflow__max45` | `--use-skillflow --use-fewshot --use-agent-memory --memory-mode active --max-items 45` | valid | 45 | 0 | 0 | 0 |

## Trace and Overfit Audit

Created:

```text
FINAL_CANDIDATE_FREEZE.md
OVERFIT_RISK_AUDIT.md
TRACE_SANITY_REPORT.md
```

Key findings:

- Source trace has 45/45 complete SkillFlow rows.
- No fallback, no parse failure, no invalid label.
- No CoT-like leakage detected.
- No active/candidate memory injected in the source trace.
- `dev_gold.jsonl` is used for evaluation/error analysis, not runtime inference.
- Candidate memory remains unpromoted and must not be included via `active_plus_candidate`.

## Previous Recommendation

Status: superseded by the 2026-05-21 frozen dev/test 45 validation rerun below.

Previous recommendation: needs one more ablation before final full submission.

Reason:

- The earlier strongest source run (`68.780`) used `--use_fewshot`, while the required Phase 6 ablation commands mostly tested no-fewshot SkillFlow (`68.111` and `68.100`). This concern was superseded by the later frozen validation at `69.007`.
- The frozen-candidate test dry run with few-shot passed on 45 rows, but a full 409-row test run was intentionally not performed per user instruction.
- The source run is the best public dev candidate, but public dev proxy is not hidden-test proof.

Practical next step:

```bash
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode dev --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active
```

If the score remains close to the frozen source run and format stays valid, then run the full test submission with the same frozen command without `--max-items`.

## 2026-05-21 Frozen Dev/Test 45 Validation Rerun

本轮只执行 frozen candidate 的 dev-45 和 test-45 验证，没有跑完整 409 条 test submission。当前电脑资源限制下，完整 test 留到最终提交前再跑。

本轮没有修改核心代码，没有调 prompt、SkillFlow、few-shot 或 strategy rules。candidate memory 没有 promote。active memory path 被启用，但 active memory 为空，trace 中 `memory_used_count=0`。

### Commands

```bash
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py

OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode dev --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active

OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode test --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active --max-items 45
```

### New Outputs

| Run | Output dir | Format | Fallback | Parse failure | Invalid label | SkillFlow fallback | Memory used |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| frozen dev-45 | `outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full` | valid | 0 | 0 | 0 | 0 | 0 |
| frozen test-45 | `outputs/test__20260521_222905_096__llm_glm4_9b_skillflow__max45` | valid | 0 | 0 | 0 | 0 | 0 |

### Dev-45 Metrics

| Metric | Value |
| --- | ---: |
| proxy_dev_score | 69.007 |
| mechanism_accuracy | 0.7556 |
| strategy_score | 0.7111 |
| risk_label_f1 | 0.7296 |
| response_reference_token_f1 | 0.1684 |

### Test-45 Result

`outputs/test__20260521_222905_096__llm_glm4_9b_skillflow__max45` generated 45 submission rows and passed format checking with 0 errors and 0 warnings. `dev_eval_returncode` is `null`, as expected for test mode.

### Updated Recommendation

Recommendation: enter final test stage when the machine can run the full test set.

Reason:

- frozen dev-45 reproduced and slightly exceeded the historical best public dev proxy score (`69.007` vs `68.780`).
- frozen test-45 passed format validation with 0 fallback, 0 parse failure, 0 invalid labels, and 0 memory injection.
- active memory remains empty (`agent_memory/active/memory.jsonl` has 0 rows), and candidate memory remains unpromoted.

Residual risk:

- Full 409-row test was intentionally not run in this validation round.
- Public dev proxy still does not guarantee hidden Core + Bloom performance.

## 2026-05-22 Active Memory Ablation Phase 1

This was a memory experiment line, not a replacement for the frozen submission candidate. It did not modify SkillFlow, prompts, few-shot, strategy rules, contract postprocess, evaluator, or format checker. It did not run full test and did not use `active_plus_candidate`.

### Promoted For Ablation Only

```text
mem_20260521_222103_dev_20260521_221741_731_llm_glm4_001
mem_20260521_222103_dev_20260521_221741_731_llm_glm4_002
```

The promoted rows were cleaned before insertion into active memory: `status=active`, short `content_en`, abstract conditions, no episode_id, no dev gold, and no reference answer.

### Run Result

| Run | Output dir | Format | Fallback | Parse failure | Invalid label | SkillFlow fallback | Memory used | Proxy score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| frozen baseline | `outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full` | valid | 0 | 0 | 0 | 0 | 0 | 69.007 |
| active memory ablation p1 | `outputs/dev__20260522_011033_370__llm_glm4_9b_skillflow__full` | valid | 0 | 0 | 0 | 0 | 90 | 68.849 |

Metric deltas:

| Metric | Frozen baseline | Active memory ablation | Delta |
| --- | ---: | ---: | ---: |
| mechanism_accuracy | 0.7556 | 0.7556 | +0.0000 |
| strategy_score | 0.7111 | 0.7111 | +0.0000 |
| risk_label_f1 | 0.7296 | 0.7296 | +0.0000 |
| response_reference_token_f1 | 0.1684 | 0.1579 | -0.0105 |

### Readiness Decision

Do not replace the frozen baseline with active memory.

Reason:

- Both memory items were retrieved on all 45 rows, proving the active memory path works.
- They did not improve mechanism, strategy, or risk metrics.
- They reduced response reference token F1 and lowered proxy score.
- The broad empty conditions made retrieval too non-selective.

`agent_memory/active/memory.jsonl` has been cleared after the failed ablation. The final readiness recommendation remains the previous frozen candidate: `skillflow_v1_fewshot_active_empty_memory`.
