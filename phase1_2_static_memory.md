# Phase 1.2: Static Memory Prompt Integration

## 1. 背景

当前项目已经完成：

- Heuristic baseline。
- Minimal LLM backend。
- `llm_a_minimal_v1`。
- `llm_b_label_definition_v1`。
- JSON parse / repair。
- Contract normalization。
- `debug/trace.jsonl`。
- `RES.md` 自动记录。

最新有效 full dev 对比：

```text
heuristic full dev: 49.223
llm_a_minimal_v1 full dev: 35.983
llm_b_label_definition_v1 full dev: 45.971
```

`llm_b_label_definition_v1` 相比 v1 明显提升：

```text
proxy_dev_score: 35.983 -> 45.971
mechanism_accuracy: 0.2667 -> 0.3778
strategy_score: 0.4444 -> 0.5889
risk_label_f1: 0.0481 -> 0.2667
response_reference_token_f1: 0.2087 -> 0.1684
```

结论：

- LLM pipeline 已经跑通。
- prompt v2 有效，但还没超过 heuristic。
- 下一步不应直接上动态 RAG / few-shot。
- 也不应立刻做完整 SkillFlow。
- 先加入一层短的、固定的 static memory，测试“任务知识小抄”是否能继续提升 LLM 稳定性。

## 2. Static Memory 是什么

Static memory 是每次 LLM 调用都固定加入 prompt 的任务知识块。

它不是：

- 动态检索。
- RAG。
- few-shot examples。
- 从 `data/Bragging_data.json` 检索样本。
- 使用 dev gold 的答案。
- 根据 episode_id 写规则。

它是：

- 固定的任务规则。
- 稳定的 label 判断原则。
- 稳定的 strategy 选择原则。
- 稳定的 risk label 约束。
- anti-sycophancy 风格约束。
- platform / relationship 的通用响应风格。

可以理解为：

```text
prompt = 当前任务说明
static memory = 长期固定任务知识
input = 当前样本
```

最终模型看到的是：

```text
[static memory]
[prompt instruction]
[input row]
[output schema]
```

## 3. Phase 1.2 目标

新增一个 prompt version：

```text
llm_c_static_memory_v1
```

它应在 `llm_b_label_definition_v1` 的基础上加入固定 memory block。

目标：

1. 保留 `heuristic` backend。
2. 保留 `llm_a_minimal_v1`。
3. 保留 `llm_b_label_definition_v1`。
4. 新增 `llm_c_static_memory_v1`。
5. 新增 static memory 文件或模块。
6. trace / manifest / RES.md 记录 `memory_version`。
7. 不引入动态 retrieval。
8. 不引入 few-shot examples。
9. 不使用 dev gold 进入推理链路。

## 4. 推荐文件结构

建议新增：

```text
humble_brag/static_memory.py
```

包含：

```python
STATIC_MEMORY_VERSION = "STATIC_MEMORY_V1"

STATIC_MEMORY_V1 = """
...
"""
```

也可以命名为：

```text
humble_brag/memory.py
```

但推荐用 `static_memory.py`，避免和后续 dynamic memory / retrieval memory 混淆。

## 5. Static Memory 内容设计

第一版 memory 必须短，不要过长。

建议控制在 300-500 英文词以内。

建议包含 5 个小节：

### 5.1 Core Behavior

```text
- Do not default to praise.
- Many humble-brags should be handled with neutral observation, grounded follow-up, redirect, or light teasing.
- Keep response_text brief, grounded, and socially appropriate.
- Avoid sycophantic language unless validation is clearly appropriate.
```

### 5.2 Strategy Selection Memory

```text
- For stay_neutral, prefer neutral_observation.
- For avoid_sycophancy, avoid validate and praise-heavy light_acknowledgment.
- For acquaintance or direct_message contexts, ask_followup can be safer than praise.
- For close_friend or playful online_peer contexts, humor_tease can be acceptable.
- Use redirect when continuing the brag would be awkward or unhelpful.
- Use validate sparingly, only when explicit affirmation fits the relationship and interaction_goal.
```

### 5.3 Risk Label Memory

Use evaluator-recognized risk types:

```text
sycophancy
preachiness
misrecognition
strategy_inconsistency
context_insensitivity
over_coldness
```

Memory should tell the model:

```text
- risk_assessment should explicitly mention 1-3 likely risk labels.
- Prefer evaluator-recognized risk names over vague natural language.
- Explain the risk briefly after naming it.
```

### 5.4 Mechanism Memory

Keep mechanism guidance short:

```text
- achievement_drop: direct mention of accomplishment, score, status, award, output, or performance.
- comparison_superiority: explicit or implicit comparison that makes the speaker seem better.
- faux_modesty: modest or self-effacing wording that still highlights an achievement.
- humble_complaint: complaint about a burden or inconvenience caused by success or ability.
- scarcity_flex: rare access, exclusivity, elite opportunity, or limited availability.
- self_aware_brag: explicit awareness of bragging, e.g. "not to brag" or "flex".
- understated_flex: indirect impressive framing without direct brag cue.
```

### 5.5 Style Memory

```text
- For neutral_observation, do not use impressive, amazing, great, awesome, congrats, or well done.
- For avoid_sycophancy, responses should avoid praise and focus on context or substance.
- For direct_message/acquaintance, avoid overly familiar teasing.
- For public forums, keep response non-escalatory and context-aware.
```

## 6. Prompt 设计

在 `humble_brag/prompts.py` 中新增：

```python
def build_static_memory_prompt_v1(row: dict[str, Any]) -> str:
    ...
```

或在 `build_label_definition_prompt_v1` 的基础上抽公共 builder。

新增支持：

```python
SUPPORTED_PROMPT_VERSIONS = {
    "llm_a_minimal_v1",
    "llm_b_label_definition_v1",
    "llm_c_static_memory_v1",
}
```

`llm_c_static_memory_v1` 的结构建议：

```text
You are generating a valid JSON response for a humble-brag response task.

Static task memory:
[STATIC_MEMORY_V1]

Allowed bragging_mechanism labels and definitions:
...

Allowed response_strategy labels and definitions:
...

Strategy selection rules:
...

Risk assessment rule:
...

Input:
...

Return JSON with exactly these fields:
...
```

注意：

- 不要删除 v1/v2 prompt。
- 不要让 static memory 覆盖输出 schema。
- 不要加入具体 dev examples。
- 不要加入 `episode_id` 级规则。

## 7. Runner / Trace / RES.md 修改

### 7.1 Runner

`runner.py` 需要识别：

```text
llm_c_static_memory_v1
```

当使用该 prompt 时，记录：

```text
memory_version = STATIC_MEMORY_V1
```

当使用 `llm_a_minimal_v1` 或 `llm_b_label_definition_v1` 时，记录：

```text
memory_version = n/a
```

### 7.2 Trace

每条 trace 新增：

```json
{
  "memory_version": "STATIC_MEMORY_V1"
}
```

如无 memory：

```json
{
  "memory_version": "n/a"
}
```

### 7.3 Manifest

`run_manifest.json` 新增：

```json
{
  "memory_version": "STATIC_MEMORY_V1"
}
```

### 7.4 RES.md

Summary 中新增：

```text
- memory_version: `STATIC_MEMORY_V1`
```

如无 memory：

```text
- memory_version: `n/a`
```

## 8. 验收命令

先确认旧版本不坏：

```bash
python3 main.py --mode dev --backend heuristic --max-items 3
python3 main.py --mode dev --backend llm --prompt-version llm_b_label_definition_v1 --max-items 3
```

跑 static memory 小样本：

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1 --max-items 10
```

如果 max10 正常，再跑 full dev：

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1
```

编译检查：

```bash
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py
```

注意：如果本地 LLM 网络被 sandbox 拦截，需要用有权限的方式运行。普通 sandbox 下 100% fallback 的结果不能作为有效 LLM 指标。

## 9. 对比指标

必须对比：

```text
heuristic full dev: 49.223
llm_b_label_definition_v1 full dev: 45.971
llm_c_static_memory_v1 full dev: ?
```

重点看：

```text
format valid
fallback_count
parse_failure_count
invalid_label_count
proxy_dev_score
mechanism_accuracy
strategy_score
risk_label_f1
response_reference_token_f1
strategy distribution
```

预期：

- `risk_label_f1` 应继续高于 v2 的 0.2667。
- `strategy_score` 不应低于 v2 的 0.5889。
- `proxy_dev_score` 应高于 v2 的 45.971。
- fallback / parse failure 不应明显升高。

注意：`response_reference_token_f1` 可能下降，因为 static memory 会让回复更规则化。这可以接受，但总分不能明显下降。

## 10. 完成标准

Phase 1.2 完成标准：

- `llm_c_static_memory_v1` 可通过 CLI 选择。
- static memory 被单独模块化。
- trace 正确记录 `memory_version`。
- RES.md 正确记录 `memory_version`。
- format checker 通过。
- full dev 成功运行。
- 没有引入 dynamic retrieval。
- 没有引入 few-shot examples。
- 没有使用 dev gold 进入推理链路。
- task.md / report.md 同步记录输出目录和核心指标。

## 11. 不要做的事情

- 不要读取 `dev_gold.jsonl` 来生成推理输出。
- 不要按 episode_id 写规则。
- 不要使用 `data/Bragging_data.json` 做检索。
- 不要把 774 条数据塞进 prompt。
- 不要加入相似样本 few-shot。
- 不要引入向量数据库。
- 不要实现 dynamic memory。
- 不要删除 v1/v2 prompt。
- 不要删除 heuristic baseline。
- 不要改官方 `format_checker.py` / `evaluate_dev.py` 评分逻辑。

## 12. 后续方向

如果 static memory 有效：

```text
llm_b_label_definition_v1: 45.971
llm_c_static_memory_v1: higher
```

则下一步可以继续做：

```text
Phase 1.3: trace error analysis for static memory
Phase 2: minimal SkillFlow
```

如果 static memory 无效或变差：

```text
llm_c_static_memory_v1 <= llm_b_label_definition_v1
```

说明问题可能不是知识不足，而是流程结构不足。下一步应进入 minimal SkillFlow：

```text
Step 1: mechanism classification
Step 2: strategy classification
Step 3: risk + response generation
Step 4: contract normalization
```

不要因为 static memory 无效就直接上 dynamic RAG。
