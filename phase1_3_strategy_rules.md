# Phase 1.3: Trace Error Analysis and Strategy Rules

## 1. 背景

当前最佳版本是：

```text
prompt_version: llm_c_static_memory_v1
memory_version: STATIC_MEMORY_V1
output_dir: outputs/dev__20260521_103942_363__llm_glm4_9b__full
proxy_dev_score: 50.881
mechanism_accuracy: 0.4222
strategy_score: 0.5889
risk_label_f1: 0.4600
response_reference_token_f1: 0.1491
format valid: True
fallback_count: 0
parse_failure_count: 0
invalid_label_count: 0
```

对比：

```text
heuristic full dev: 49.223
llm_b_label_definition_v1 full dev: 45.971
llm_c_static_memory_v1 full dev: 50.881
```

结论：

- Static memory 有效。
- 当前 LLM v3 已经超过 heuristic baseline。
- 但 strategy 仍有明显系统性问题。
- 下一步应先做 trace error analysis，再实现轻量 `strategy_rules_v1`。

## 2. 当前主要问题

### 2.1 Strategy 过度保守

`llm_c_static_memory_v1` full dev 策略分布：

```text
neutral_observation: 31
light_acknowledgment: 9
humor_tease: 5
ask_followup: 0
validate: 0
redirect: 0
```

Gold preferred strategy 分布中实际存在：

```text
ask_followup: 8
validate: 4
redirect: 3
```

说明 static memory 把模型从“过度夸奖”拉回了中性，但现在又过度偏向 `neutral_observation`。

### 2.2 Strategy acceptable 仍有可修空间

当前 `acceptable_strategy_rate` 已经达到：

```text
0.8444
```

但仍有若干样本预测策略不在 acceptable strategies 中。

已观察到的 not acceptable 样本包括：

```text
dev_seed_000231_a
dev_seed_000386_b
dev_seed_000461_a
dev_seed_000556_b
dev_seed_000691_c
dev_seed_000738_a
dev_seed_000738_c
```

Phase 1.3 不允许写这些 episode_id 的硬编码规则。它们只能作为错误分析样本，用于总结通用规则。

### 2.3 Mechanism 仍有混淆

常见 mechanism 混淆：

```text
understated_flex -> self_aware_brag
comparison_superiority -> understated_flex
faux_modesty -> achievement_drop
understated_flex -> achievement_drop
humble_complaint -> achievement_drop
```

Phase 1.3 的主要目标不是机制分类，但 trace analysis 文档应记录这些混淆，为后续 SkillFlow 做准备。

## 3. Strategy Rules 是什么

`strategy_rules` 是 LLM 输出之后、contract normalization 之前的一层轻量策略校准。

位置：

```text
input
  -> LLM prompt
  -> raw model output
  -> JSON parse / repair
  -> strategy_rules
  -> contract normalization
  -> format checker / evaluator
  -> trace / RES.md
```

职责：

- 不生成完整答案。
- 不替代 LLM。
- 只检查 `response_strategy` 是否明显不合适。
- 必要时根据通用上下文规则做轻量修正。
- 必须记录每次修正的 before / after / reason。

它和其他模块的区别：

| 模块 | 作用 |
| --- | --- |
| `prompts.py` | 告诉 LLM 如何完成任务 |
| `static_memory.py` | 提供固定任务知识 |
| `strategy_rules.py` | 复核并校准 `response_strategy` |
| `contract.py` | 字段合法性、字数、risk 补强、CoT 清理、anti-sycophancy |
| `runner.py` | 串联运行、trace、报告、评测 |

## 4. Phase 1.3 目标

本阶段目标：

1. 基于 v3 trace 生成错误分析文档。
2. 新增轻量 `strategy_rules_v1`。
3. 允许通过 CLI 开关启用 / 关闭 strategy rules。
4. trace 记录 strategy rule 是否被触发。
5. 保持 `llm_c_static_memory_v1` 原始版本可复现。
6. 不引入 dynamic RAG。
7. 不引入 few-shot examples。
8. 不读取 dev gold 进入推理链路。
9. 不写 episode_id 规则。

## 5. 新增文件建议

### 5.1 新增错误分析文档

建议新增：

```text
phase1_3_error_analysis.md
```

内容包括：

- v3 full dev 指标摘要。
- strategy 预测分布。
- gold preferred strategy 分布。
- mechanism 预测分布。
- mechanism 混淆摘要。
- strategy 混淆摘要。
- not acceptable strategy 样本摘要。
- risk label 缺失模式。
- 下一步 strategy rules 设计依据。

这个文档可以由脚本或手工整理生成。它是分析文档，不进入推理链路。

### 5.2 新增策略规则模块

建议新增：

```text
humble_brag/strategy_rules.py
```

建议接口：

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class StrategyRuleResult:
    strategy: str
    applied: bool
    reason: str | None = None

def apply_strategy_rules(
    row: dict[str, Any],
    candidate: dict[str, Any],
    rule_version: str = "strategy_rules_v1",
) -> StrategyRuleResult:
    ...
```

也可以返回更新后的 candidate：

```python
def apply_strategy_rules(row, candidate, rule_version) -> tuple[dict[str, Any], dict[str, Any]]:
    ...
```

重点是 trace 必须拿到：

```text
strategy_before
strategy_after
strategy_rule_applied
strategy_rule_reason
strategy_rule_version
```

## 6. Strategy Rules v1 设计原则

规则必须是通用规则。

允许使用：

```text
speaker_post
platform
relationship
agent_role
interaction_goal
bragging_mechanism
model predicted response_strategy
```

禁止使用：

```text
episode_id
dev_gold.jsonl
gold labels
reference_response
acceptable_strategies
unacceptable_strategies
```

## 7. Strategy Rules v1 候选规则

### 7.1 ask_followup 补强

当前 v3 完全没有预测 `ask_followup`，但 gold preferred 中有 8 条。

通用规则建议：

```text
If predicted strategy is neutral_observation or light_acknowledgment,
and interaction_goal is avoid_sycophancy,
and relationship is acquaintance or platform is direct_message,
then prefer ask_followup when the post contains a concrete activity, project, work, score, or experience that can be followed up substantively.
```

可检测词：

```text
project, work, score, exam, class, research, game, training, run, read, built, finished, made, learned, wrote
```

不要对明显玩笑或尴尬场景强行 follow-up。

### 7.2 redirect 补强

当前 v3 没有预测 `redirect`。

通用规则建议：

```text
If interaction_goal is deescalate_awkwardness,
and relationship is acquaintance or platform is group_chat / community_forum,
and the post sounds socially awkward, self-amplifying, or invites escalation,
then redirect can be safer than neutral_observation.
```

可检测线索：

```text
shocked, everyone, nobody, adults, family gatherings, can't believe, obviously, better than, full conversation
```

注意：redirect 规则应保守，避免大量覆盖 `neutral_observation`。

### 7.3 humor_tease 保护

当前 v3 有 `humor_tease`，但有些样本仍被中性化。

通用规则建议：

```text
If interaction_goal is deescalate_awkwardness,
and relationship is close_friend or online_peer,
and platform is social_media / group_chat / community_forum,
then humor_tease can be acceptable when the post tone is playful or absurd.
```

可检测线索：

```text
gaming, dog, pug, flex, ridiculous, somehow, true skill, obviously
```

注意：不要在 direct_message + acquaintance 中强行 humor_tease。

### 7.4 validate 限制性补强

当前 v3 没有预测 `validate`。

通用规则建议：

```text
Use validate only when interaction_goal is not avoid_sycophancy,
relationship is close_friend or supportive context,
and the post expresses a genuine achievement rather than social one-upmanship.
```

这条规则应非常保守。Phase 1.3 可以先只记录 validate candidate，不一定实际改成 validate。

### 7.5 stay_neutral 保护

不要为了提升多样性破坏 `stay_neutral`。

规则：

```text
If interaction_goal is stay_neutral, do not change neutral_observation to validate.
If interaction_goal is stay_neutral and current strategy is neutral_observation, keep it unless there is a strong redirect or humor_tease cue.
```

## 8. CLI 设计

建议新增参数：

```bash
--strategy-rules none|v1
```

默认：

```text
none
```

这样可以复现原始 v3：

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1 --strategy-rules none
```

也可以运行 v4：

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1 --strategy-rules v1
```

## 9. Trace / Manifest / RES.md 修改

### 9.1 Trace

每条 trace 增加：

```json
{
  "strategy_rule_version": "strategy_rules_v1",
  "strategy_rule_applied": true,
  "strategy_before": "neutral_observation",
  "strategy_after": "ask_followup",
  "strategy_rule_reason": "avoid_sycophancy_acquaintance_substantive_followup"
}
```

如果未启用或未触发：

```json
{
  "strategy_rule_version": "none",
  "strategy_rule_applied": false,
  "strategy_before": "neutral_observation",
  "strategy_after": "neutral_observation",
  "strategy_rule_reason": null
}
```

### 9.2 Manifest

`run_manifest.json` 增加：

```json
{
  "strategy_rules": "v1",
  "strategy_rule_applied_count": 5
}
```

### 9.3 RES.md

Summary 增加：

```text
- strategy_rules: `v1`
- strategy_rule_applied_count: `5`
```

## 10. 验收命令

先确保原始 v3 可复现：

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1 --strategy-rules none --max-items 10
```

跑 strategy rules 小样本：

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1 --strategy-rules v1 --max-items 10
```

如果 max10 正常，再跑 full dev：

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1 --strategy-rules v1
```

编译检查：

```bash
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py
```

注意：本地 LLM 被 sandbox 网络拦截时，100% fallback 的结果不能作为有效 LLM 指标。需要使用可访问本地 Ollama / glm4:9b 的方式运行。

## 11. 对比指标

必须对比：

```text
heuristic full dev: 49.223
llm_c_static_memory_v1 no rules: 50.881
llm_c_static_memory_v1 + strategy_rules_v1: ?
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
strategy_rule_applied_count
```

预期：

- `strategy_score` 应高于或不低于 0.5889。
- `proxy_dev_score` 应高于或不明显低于 50.881。
- `ask_followup` / `redirect` / `validate` 至少应有合理候选或少量输出。
- fallback / parse failure 不应升高。
- format checker 必须 valid。

## 12. 完成标准

Phase 1.3 完成标准：

- 新增 `phase1_3_error_analysis.md`。
- 新增 `humble_brag/strategy_rules.py`。
- CLI 支持 `--strategy-rules none|v1`。
- 原始 v3 可通过 `--strategy-rules none` 复现。
- strategy rules v1 可通过 `--strategy-rules v1` 启用。
- trace / manifest / RES.md 记录 strategy rule 信息。
- full dev 成功运行。
- 不读取 dev gold 进入推理链路。
- 不写 episode_id 规则。
- 不引入 dynamic RAG / few-shot。
- task.md / report.md 同步记录真实输出目录和核心指标。

## 13. 不要做的事情

- 不要使用 `dev_gold.jsonl` 参与推理。
- 不要写 episode_id 硬编码。
- 不要把 acceptable_strategies / preferred_strategy 放入推理链路。
- 不要引入 dynamic retrieval。
- 不要引入 few-shot examples。
- 不要删除 heuristic baseline。
- 不要删除 `llm_a` / `llm_b` / `llm_c` prompt。
- 不要修改官方 `format_checker.py` / `evaluate_dev.py` 逻辑。
- 不要为了 public dev 分数过度写死样本模式。

## 14. 后续方向

如果 strategy_rules_v1 有效：

```text
llm_c_static_memory_v1: 50.881
llm_c_static_memory_v1 + strategy_rules_v1: higher or similar with better strategy distribution
```

则进入：

```text
Phase 1.4: stable candidate freeze / test generation
```

如果 strategy_rules_v1 无效：

```text
score drops or strategy distribution becomes worse
```

则回到 trace analysis，准备进入 minimal SkillFlow：

```text
Step 1: mechanism classification
Step 2: strategy classification
Step 3: risk + response generation
Step 4: contract normalization
```

不要因为 strategy_rules_v1 一次无效就直接上 dynamic RAG。
