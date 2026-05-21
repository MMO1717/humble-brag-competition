# Final Candidate Freeze

更新时间：2026-05-22

## Freeze Summary

本文件冻结当前最强候选配置，用于后续复现、交接和提交前核查。

```text
candidate_name: skillflow_v1_fewshot_active_empty_memory
source_run_id: dev__20260521_221741_731__llm_glm4_9b_skillflow__full
source_output_dir: outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full
recommendation_scope: public dev candidate, not hidden-test guarantee
```

## Frozen Runtime Configuration

| Item | Frozen value | Evidence |
| --- | --- | --- |
| backend | `llm` | source `run_manifest.json` |
| model | `glm4:9b` | generator `llm_glm4_9b_skillflow` |
| prompt_version | `skillflow` | source `run_manifest.json` |
| use_skillflow | `true` | source `run_manifest.json` |
| use_agent_memory | `true` | source `run_manifest.json` |
| memory_mode | `active` | source `run_manifest.json` |
| active_memory_count | `0` | source `run_manifest.json` |
| candidate_memory_count | `4` in source run; later candidate file has 6 rows after offline error analysis | source `run_manifest.json`; current candidate file |
| memory_used_count | `0` | source `run_manifest.json` and trace audit |
| use_fewshot | `true` | source `run_manifest.json` |
| fewshot_k | `3` | source `run_manifest.json` |
| strategy_rules | `none` | source `run_manifest.json` |
| strategy_rule_applied_count | `0` | source `run_manifest.json` |
| temperature | `0.3` | `humble_brag/runner.py` SkillFlow context |
| max_tokens | `256` | `humble_brag/runner.py` SkillFlow context |
| postprocess / contract version | current `humble_brag/contract.py`, `humble_brag/output_builder.py`, `humble_brag/validators.py` | current code |
| static memory version | `n/a` for SkillFlow source run | source `run_manifest.json` |
| active memory version | no active memory item loaded | `active_memory_count=0` |

## Source Metrics

| Metric | Value |
| --- | ---: |
| format valid | `True` |
| fallback_count | `0` |
| parse_failure_count | `0` |
| invalid_label_count | `0` |
| skillflow_fallback_count | `0` |
| proxy_dev_score | `69.007` |
| mechanism_accuracy | `0.7556` |
| strategy_score | `0.7111` |
| risk_label_f1 | `0.7296` |
| response_reference_token_f1 | `0.1684` |

## Reproduction Command

Use explicit Ollama environment variables to avoid sandbox or model auto-detection ambiguity:

```bash
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode dev --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active
```

For a 45-row test dry run matching this frozen candidate:

```bash
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode test --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active --max-items 45
```

## Freeze Notes

- The strongest source run used few-shot retrieval (`use_fewshot=true`, `fewshot_k=3`).
- The active memory path was enabled, but active memory was empty and `memory_used_count=0`.
- Candidate memory must remain excluded from final inference unless separately reviewed, promoted, and ablated. The current candidate file is an offline review pool, not part of the frozen runtime chain.
- The public dev score is useful for iteration only. It is not evidence of hidden-test performance.
