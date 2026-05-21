# Phase 6: Candidate Freeze and Submission Readiness

> Update 2026-05-22: The frozen candidate was revalidated at
> `outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full` with
> `proxy_dev_score=69.007`, format valid, 0 fallback, 0 parse failure, 0 invalid label,
> and `memory_used_count=0`. Earlier references to `68.780` are historical context.

## 1. 背景

当前项目已经从最小 heuristic baseline 推进到 SkillFlow 和 memory scaffold。

最近关键 checkpoint：

```text
heuristic full dev: 49.223
llm_c_static_memory_v1 full dev: 50.881
skillflow full dev: 69.007
```

当前最佳 full dev 运行：

```text
run_id: dev__20260521_221741_731__llm_glm4_9b_skillflow__full
backend: llm
prompt_version: skillflow
use_skillflow: True
use_agent_memory: True
memory_mode: active
active_memory_count: 0
candidate_memory_count: 4
memory_used_count: 0
format valid: True
fallback_count: 0
parse_failure_count: 0
invalid_label_count: 0
proxy_dev_score: 69.007
mechanism_accuracy: 0.7556
strategy_score: 0.7111
risk_label_f1: 0.7296
response_reference_token_f1: 0.1532
```

注意：

- 当前 `memory_mode=active`，但 `active_memory_count=0`，所以这个 69.007 主要来自 SkillFlow / few-shot / postprocess，而不是 active memory。
- `agent_memory/candidate/` 中已有 candidate memory，但仍处于候选状态，不能直接进入最终推理链。
- 当前结果是 public dev proxy，不代表 hidden test 结果。

Phase 6 的目标不是继续堆功能，而是把当前最强候选变成可复现、可解释、可提交的稳定版本。

## 2. Phase 6 目标

Phase 6 做四件事：

1. 固化当前最佳候选配置。
2. 做必要 ablation，确认分数来自哪里。
3. 做 overfit / hidden-test 风险审计。
4. 生成 test submission 前的最终 readiness 报告。

本阶段不新增复杂能力，除非 ablation 证明必要。

## 3. 必须冻结的配置

需要在文档中明确记录：

```text
backend
model
prompt_version
use_skillflow
use_agent_memory
memory_mode
strategy_rules
fewshot settings
temperature
max_tokens
postprocess / contract version
static memory / active memory version
```

建议新增：

```text
FINAL_CANDIDATE_FREEZE.md
```

记录当前推荐候选：

```text
candidate_name: skillflow_v1_no_active_memory
source_run_id: dev__20260521_190335_066__llm_glm4_9b_skillflow__full
backend: llm
model: glm4:9b
prompt_version: skillflow
use_skillflow: true
use_agent_memory: true
memory_mode: active
active_memory_count: 0
strategy_rules: none
```

如果实际命令中还有 `--fewshot`、`--strategy-rules`、`--memory-mode` 等参数，也要精确记录。

## 4. Required Ablation

Phase 6 必须至少跑以下 ablation，避免误判最佳方案。

### 4.1 Baseline Reference

```bash
python3 main.py --mode dev --backend heuristic
```

目标：确认 heuristic reference 仍可运行。

### 4.2 Static Memory Single Prompt Reference

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1
```

目标：保留 single-prompt LLM reference。

### 4.3 SkillFlow No Agent Memory

建议命令按当前 CLI 实际参数调整，例如：

```bash
python3 main.py --mode dev --backend llm --use-skillflow --memory-mode no_memory
```

目标：确认 SkillFlow 本身贡献。

### 4.4 SkillFlow Active Memory

```bash
python3 main.py --mode dev --backend llm --use-skillflow --use-agent-memory --memory-mode active
```

目标：确认 active memory 是否实际参与。当前 active memory count 为 0，所以这组应接近 no_memory。

### 4.5 Candidate Memory 禁用原则

不要默认跑：

```text
active_plus_candidate
```

除非明确要做 offline review ablation。

Candidate memory 只能用于分析，不应直接进入 final submission。

## 5. Overfit Risk Audit

新增：

```text
OVERFIT_RISK_AUDIT.md
```

至少覆盖：

1. 是否使用 `dev_gold.jsonl` 进入推理链。
2. 是否存在 episode_id 级规则。
3. 是否把 acceptable_strategies / preferred_strategy 写进 prompt 或规则。
4. 是否用 candidate memory 直接影响 final output。
5. 是否存在 public-dev 特化 keyword hacks。
6. 是否有 fallback 到 heuristic 造成隐性数据泄漏。
7. 是否 test mode 能在无 gold 下正常运行。

允许使用 dev gold 的地方：

```text
offline evaluation
error analysis
candidate memory generation
documentation
```

禁止使用 dev gold 的地方：

```text
inference prompt
runtime rules
test submission generation
active memory promotion without review
```

## 6. Trace Sanity Check

对最佳候选 trace 做抽样检查。

目标文件：

```text
outputs/dev__20260521_190335_066__llm_glm4_9b_skillflow__full/debug/trace.jsonl
```

检查内容：

- 是否每条都有 SkillFlow 中间步骤。
- 是否有 raw model output。
- 是否有 parsed / normalized output。
- 是否有 fallback。
- 是否有 CoT 泄露。
- 是否有 invalid label 被静默吞掉。
- 是否有 active memory 实际注入。

建议新增 summary：

```text
TRACE_SANITY_REPORT.md
```

## 7. Candidate Memory 处理原则

当前 candidate memory：

```text
agent_memory/candidate/memory_candidates.jsonl
agent_memory/candidate/candidate_review.md
```

处理原则：

- 保持 candidate 状态。
- 不要自动 promote 到 active。
- 如果要 promote，必须先做人工审查和 no-memory vs active-memory ablation。
- active memory 进入 final candidate 前，需要记录 promoted memory id、理由、风险和 ablation 结果。

当前 active memory 为空：

```text
agent_memory/active/memory.jsonl
```

这反而是一个优点：当前 69.007 不依赖未经审查的 active memory。

## 8. Test Submission Dry Run

在最终提交前，必须跑 test dry run。

建议命令按当前 CLI 实际参数调整：

```bash
python3 main.py --mode test --backend llm --use-skillflow --use-agent-memory --memory-mode active
```

要求：

- format checker valid。
- row count 与 test input 一致。
- no dev gold dependency。
- no evaluator call in test mode。
- submission.jsonl 只包含官方 7 字段。
- trace / manifest / RES.md 正常生成。

不要把 dev 输出当 test 输出。

## 9. Final Readiness Report

新增：

```text
FINAL_READINESS_REPORT.md
```

内容包括：

1. 最终候选配置。
2. dev ablation 表。
3. test dry run 输出目录。
4. format checker 结果。
5. fallback / parse failure / invalid label 统计。
6. overfit audit 结论。
7. candidate memory 是否启用。
8. 是否推荐提交。

推荐结论格式：

```text
Recommendation: submit / do not submit / needs one more ablation
Reason:
- ...
Residual risk:
- ...
```

## 10. 验收命令

先运行编译：

```bash
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py
```

再运行 dev ablation：

```bash
python3 main.py --mode dev --backend heuristic
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1
python3 main.py --mode dev --backend llm --use-skillflow --memory-mode no_memory
python3 main.py --mode dev --backend llm --use-skillflow --use-agent-memory --memory-mode active
```

最后运行 test dry run：

```bash
python3 main.py --mode test --backend llm --use-skillflow --use-agent-memory --memory-mode active
```

如果普通 sandbox 拦截本地 LLM 网络，导致 100% fallback，该结果不能作为有效指标。需要用可访问本地 Ollama / `glm4:9b` 的方式重跑。

## 11. 验收标准

Phase 6 完成标准：

- `FINAL_CANDIDATE_FREEZE.md` 已创建。
- `OVERFIT_RISK_AUDIT.md` 已创建。
- `TRACE_SANITY_REPORT.md` 已创建。
- `FINAL_READINESS_REPORT.md` 已创建。
- dev ablation 完整记录。
- test dry run format valid。
- final candidate 配置可复现。
- 没有 candidate memory 未经审查直接进入 final chain。
- 没有 dev gold 进入 inference chain。
- `task.md` 和 `report.md` 更新真实运行结果。

## 12. 不要做的事情

- 不要继续随意调 prompt。
- 不要直接 promote candidate memory。
- 不要直接使用 `active_plus_candidate` 作为 final。
- 不要按 episode_id 写规则。
- 不要读取 dev gold 参与 test inference。
- 不要把 public dev proxy score 当 hidden test 保证。
- 不要修改官方 `format_checker.py` / `evaluate_dev.py`。
- 不要删除旧 checkpoint。

## 13. 后续方向

如果 Phase 6 通过：

```text
freeze final candidate
-> generate final test submission
-> push branch / prepare GitHub handoff
```

如果 Phase 6 发现 active memory / candidate memory 有风险：

```text
use skillflow no active memory as final candidate
-> keep memory only as future work
```

如果 SkillFlow test dry run 不稳定：

```text
fallback candidate: llm_c_static_memory_v1
```
