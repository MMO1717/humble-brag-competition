# Memory Ablation Phase 1

更新时间：2026-05-22

## 1. 当前基线

当前已经冻结并推送的 baseline：

```text
branch: dev-phase3-skillflow
commit: 74e1ce1 Freeze skillflow candidate readiness
candidate_name: skillflow_v1_fewshot_active_empty_memory
```

## 11. Phase 1 实际执行结果 (2026-05-22)

本轮为 memory 实验线，不是最终提交链。本轮没有修改 SkillFlow、prompt、few-shot、strategy_rules、contract、evaluator 或 format checker；没有运行完整 test；没有使用 `active_plus_candidate`。

### 11.1 Candidate 筛选记录

候选池实际包含 6 条 candidate memory，但只有两类唯一内容，各重复 3 次。为降低过拟合风险，本轮只短暂 promote 最新 frozen run 生成的两条唯一 memory 做 ablation，旧 run 的重复条目全部 reject。

| memory_id | target_skills | 泛化性 | public dev 过拟合风险 | strategy 偏移风险 | 决策 | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `mem_20260521_191003_dev_20260521_190335_066_llm_glm4_001` | `MechanismSkill` | 是 | 中 | 低 | reject | 与最新 candidate 内容重复，来源更旧，不重复 promote。 |
| `mem_20260521_191003_dev_20260521_190335_066_llm_glm4_002` | `StrategySkill`, `ResponseSkill` | 是 | 中 | 中 | reject | 与最新 candidate 内容重复，且可能鼓励更多 `ask_followup` / `humor_tease`。 |
| `mem_20260521_212722_dev_20260521_212356_012_llm_glm4_001` | `MechanismSkill` | 是 | 中 | 低 | reject | 与最新 candidate 内容重复，来源更旧，不重复 promote。 |
| `mem_20260521_212722_dev_20260521_212356_012_llm_glm4_002` | `StrategySkill`, `ResponseSkill` | 是 | 中 | 中 | reject | 与最新 candidate 内容重复，且可能导致 strategy 偏移。 |
| `mem_20260521_222103_dev_20260521_221741_731_llm_glm4_001` | `MechanismSkill` | 是 | 中 | 低 | promote for ablation | 最新 frozen run 来源，内容短、抽象，不含 episode_id / dev gold / reference answer。 |
| `mem_20260521_222103_dev_20260521_221741_731_llm_glm4_002` | `StrategySkill`, `ResponseSkill` | 是 | 中 | 中 | promote for ablation | 最新 frozen run 来源，内容短、抽象；保留 workplace / professional negative condition。 |

Promote 写入时已清理 source，仅保留人工审核来源、candidate id 和 source run id；没有写入 episode_id、dev gold 或 reference answer。

### 11.2 执行命令

```bash
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py

OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode dev --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active
```

### 11.3 新输出目录

```text
outputs/dev__20260522_011033_370__llm_glm4_9b_skillflow__full
```

### 11.4 指标对比

| Metric | Frozen baseline | Active memory ablation | Delta |
| --- | ---: | ---: | ---: |
| proxy_dev_score | 69.007 | 68.849 | -0.158 |
| mechanism_accuracy | 0.7556 | 0.7556 | +0.0000 |
| strategy_score | 0.7111 | 0.7111 | +0.0000 |
| risk_label_f1 | 0.7296 | 0.7296 | +0.0000 |
| response_reference_token_f1 | 0.1684 | 0.1579 | -0.0105 |
| fallback_count | 0 | 0 | 0 |
| parse_failure_count | 0 | 0 | 0 |
| invalid_label_count | 0 | 0 | 0 |
| skillflow_fallback_count | 0 | 0 | 0 |
| active_memory_count | 0 | 2 | +2 |
| candidate_memory_count | 6 | 6 | 0 |
| memory_used_count | 0 | 90 | +90 |

Format checker 通过：`valid=true`，0 error，0 warning。

### 11.5 Trace 观察

| 检查项 | 结果 |
| --- | --- |
| trace rows | 45 |
| complete SkillFlow rows | 45 |
| fallback rows | 0 |
| skill error rows | 0 |
| validation error rows | 0 |
| CoT-like leakage | 0 |
| memory rows | 45 |
| memory by skill | `MechanismSkill=45`, `StrategySkill=45` |
| memory by id | 两条 promoted memory 各命中 45 次 |

Strategy 分布与 frozen baseline 完全相同：

```text
neutral_observation: 16
light_acknowledgment: 12
redirect: 6
humor_tease: 6
ask_followup: 3
validate: 2
```

Mechanism 分布也与 frozen baseline 完全相同。变化主要发生在 `response_text`，共有 30 行 response_text 与 baseline 不同，但没有带来分数收益。

### 11.6 结论

结论：本轮 active memory ablation 失败，不建议进入 memory candidate v1 freeze。

原因：

- memory 确实进入了推理链，`memory_used_count=90`。
- 但 mechanism、strategy、risk 三个核心指标没有提升。
- `response_reference_token_f1` 从 `0.1684` 降到 `0.1579`，导致 proxy dev score 从 `69.007` 降到 `68.849`。
- 两条 memory 因 conditions 过宽，在 45 条样本上全部命中，说明检索不够选择性。

按决策规则，已清空：

```text
agent_memory/active/memory.jsonl
```

最终候选仍保持原 frozen baseline：

```text
skillflow_v1_fewshot_active_empty_memory
outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full
```

补充说明：本轮 dev 运行触发了现有 offline error analysis 的 candidate memory 自动追加副作用。为保持本轮“只修改 active memory 和文档”的边界，已将 `agent_memory/candidate/memory_candidates.jsonl` 和 `agent_memory/candidate/candidate_review.md` 恢复到运行前快照；candidate memory 没有 promote，也没有进入 final chain。

当前 frozen candidate：

```text
SkillFlow + few-shot + active memory path
active memory: empty
memory_used_count: 0
dev-45 proxy_dev_score: 69.007
source_output_dir: outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full
```

这说明当前高分主要来自：

```text
SkillFlow
few-shot
contract normalization
postprocess / validation
```

不是来自 active memory。

## 2. 本阶段目标

Memory Ablation Phase 1 的目标不是直接替换最终候选，而是验证：

```text
active memory 是否真的能被检索到
active memory 是否能提升或至少不损害 dev-45 表现
active memory 是否会导致 strategy / risk / response 被带偏
```

本阶段只允许建立一条 memory 实验线。当前 frozen baseline 必须保留为可回滚候选。

## 3. 严格边界

本阶段允许修改：

```text
agent_memory/active/memory.jsonl
MEMORY_ABLATION_PHASE1.md
report.md
task.md
```

必要时可以更新：

```text
FINAL_READINESS_REPORT.md
```

但不能覆盖原 frozen baseline 结论，除非 memory ablation 明显成功。

本阶段不允许修改：

```text
humble_brag/skillflow.py
humble_brag/prompts_skillflow.py
humble_brag/prompts.py
humble_brag/fewshot.py
humble_brag/strategy_rules.py
humble_brag/contract.py
scripts/format_checker.py
scripts/evaluate_dev.py
```

本阶段不允许：

```text
run full 409-row test
use memory_mode=active_plus_candidate
promote all candidate memory at once
write dev-gold-specific rules
bind memory to episode_id
change prompt or SkillFlow while testing memory
```

## 4. Memory 筛选原则

从下面文件中筛选候选：

```text
agent_memory/candidate/memory_candidates.jsonl
agent_memory/candidate/candidate_review.md
```

每条 candidate memory 都要判断：

```text
是否泛化
是否依赖 public dev gold
是否只是在记某个样本答案
是否会强行改变 strategy 分布
是否会让 response_text 变模板化
是否适合进入某个具体 skill
```

第一轮只 promote 1-3 条。宁可少，不要多。

## 5. Promote 格式要求

写入：

```text
agent_memory/active/memory.jsonl
```

要求：

```text
JSONL 格式
status 必须是 active
target_skills 必须准确
content_en 必须短
conditions 必须抽象
不能包含 episode_id
不能包含 dev gold answer
不能包含 reference response
不能写成大段 prompt
```

推荐优先选择这类 memory：

```text
泛化到 mechanism 判断的抽象 cue
泛化到 strategy 选择的社交语境 cue
泛化到 response 风格控制的短规则
```

不推荐选择：

```text
只对一个 dev 样本有效的规则
过度指定某个 label 的规则
会把 strategy 固定到某一类的规则
会鼓励过度夸奖的规则
```

## 6. 验证命令

编译检查：

```bash
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py
```

active memory dev-45 ablation：

```bash
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode dev --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active
```

说明：

```text
dev 本身只有 45 条，所以不用加 --max-items 45。
本阶段不跑完整 test。
```

## 7. 必看输出

新 run 生成后，检查：

```text
outputs/<new_run_id>/RES.md
outputs/<new_run_id>/run_manifest.json
outputs/<new_run_id>/format_report.json
outputs/<new_run_id>/dev_eval_report.json
outputs/<new_run_id>/debug/trace.jsonl
```

核心指标：

```text
proxy_dev_score
mechanism_accuracy
strategy_score
risk_label_f1
response_reference_token_f1
fallback_count
parse_failure_count
invalid_label_count
skillflow_fallback_count
active_memory_count
candidate_memory_count
memory_used_count
```

trace 必须额外检查：

```text
哪些 memory_id 被使用
memory 用在哪些 skill
memory 是否真的进入 prompt
memory 是否导致 strategy 判断变差
memory 是否让 response_text 变模板化
```

## 8. 对比基线

固定对比对象：

```text
baseline_output_dir: outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full
baseline_proxy_dev_score: 69.007
baseline_memory_used_count: 0
baseline_fallback_count: 0
baseline_parse_failure_count: 0
baseline_invalid_label_count: 0
```

判断标准：

```text
通过：
- format valid = true
- fallback_count = 0
- parse_failure_count = 0
- invalid_label_count = 0
- skillflow_fallback_count = 0
- memory_used_count > 0
- proxy_dev_score 接近或高于 69.007
- trace 中没有明显 memory 带偏

保留但不替换：
- memory_used_count > 0
- proxy_dev_score 接近 69.007
- 没有结构性错误
- 但没有明确指标收益

失败：
- proxy_dev_score 明显下降
- strategy_score 或 risk_label_f1 明显下降
- 出现 fallback / parse failure / invalid label
- memory_used_count = 0
- trace 显示 memory 把模型带向错误 strategy
```

## 9. 决策规则

实验结束后只允许三种结论：

```text
1. Promote 成功：
   冻结为 memory candidate v1，但仍需保留 no-memory frozen baseline。

2. 效果接近：
   保留实验记录，不替换最终候选。

3. 效果变差：
   清空 agent_memory/active/memory.jsonl，回到 commit 74e1ce1 的 frozen baseline。
```

不要因为“想用 memory”而强行保留 memory。

## 10. 给 Coding Agent 的提示词

```text
你现在在 /Users/mm/Desktop/BRAG-Pipeline-main/humble-brag-competition 工作。

当前任务：执行 Memory Ablation Phase 1。只测试 active memory，不修改核心 pipeline。

当前 frozen baseline：
commit: 74e1ce1 Freeze skillflow candidate readiness
candidate: SkillFlow + few-shot + active memory path
active memory: empty
memory_used_count: 0
dev-45 proxy_dev_score: 69.007
baseline output:
outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full

严格限制：
- 不跑完整 409-row test。
- 不使用 memory_mode=active_plus_candidate。
- 不一次性 promote 全部 candidate memory。
- 不修改 SkillFlow。
- 不修改 prompt。
- 不修改 few-shot。
- 不修改 strategy_rules。
- 不修改 contract / evaluator / format checker。
- 不根据 dev gold 写样本特化规则。
- 不把 candidate memory 直接带入 final chain。

允许修改：
- agent_memory/active/memory.jsonl
- MEMORY_ABLATION_PHASE1.md
- report.md
- task.md
- 必要时 FINAL_READINESS_REPORT.md

执行步骤：

1. 读取并理解：
- MEMORY_ABLATION_PHASE1.md
- FINAL_CANDIDATE_FREEZE.md
- FINAL_READINESS_REPORT.md
- agent_memory/README.md
- agent_memory/candidate/memory_candidates.jsonl
- agent_memory/candidate/candidate_review.md

2. 对 candidate memory 做人工筛选，记录每条：
- memory_id
- target_skill
- 是否泛化
- 是否可能过拟合 public dev
- 是否可能导致 strategy 偏移
- 是否建议 promote
- promote / reject 理由

3. 只选择 1-3 条低风险 memory 写入：
agent_memory/active/memory.jsonl

要求：
- JSONL 格式正确
- status = active
- content_en 简短
- target_skills 准确
- conditions 抽象
- 不包含 episode_id
- 不包含 dev gold 或 reference answer

4. 运行编译检查：

python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py

5. 运行 active memory dev-45 ablation：

OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode dev --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active

6. 检查新 outputs 目录：
- RES.md
- run_manifest.json
- format_report.json
- dev_eval_report.json
- debug/trace.jsonl

7. 和 baseline 对比：
baseline proxy_dev_score = 69.007
baseline memory_used_count = 0

重点输出：
- 新 run_id
- 新 proxy_dev_score
- mechanism_accuracy
- strategy_score
- risk_label_f1
- response_reference_token_f1
- fallback_count
- parse_failure_count
- invalid_label_count
- skillflow_fallback_count
- active_memory_count
- memory_used_count
- 使用到的 memory_id
- memory 作用在哪些 skill

8. 更新文档：
- MEMORY_ABLATION_PHASE1.md
- report.md
- task.md
- 必要时 FINAL_READINESS_REPORT.md

文档必须写清：
- 本轮是 memory 实验线，不是最终提交链。
- promote 了哪些 memory。
- reject 了哪些 memory。
- 新输出目录。
- 新指标与 69.007 baseline 的对比。
- 是否建议保留 active memory。
- 如果失败，是否已清空 active memory 或建议回滚。

最后输出：
- 修改文件列表
- promote 的 memory_id
- 新 outputs 目录
- dev-45 指标表
- 和 baseline 的差异
- 是否建议进入 memory candidate v1
- 当前 git status
```
