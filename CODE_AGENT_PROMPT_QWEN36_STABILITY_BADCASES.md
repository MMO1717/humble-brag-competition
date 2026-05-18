# Code Agent Prompt: qwen3.6-27b 稳定 Bad Case 分析

你现在负责 BRAG-Agent 的下一轮分析任务。请注意：本轮任务是 **只分析，不改核心代码**。

## 背景

当前项目主线：

```text
multi_v1 架构 + qwen3.6-27b 临时开发模型
```

当前已知：

- `qwen3.6-27b` 不是最终官方 `<20B` 提交模型，只是当前开发参考模型。
- `<20B` 模型横评暂时暂停。
- `qwen36_27b_calib_a` 不保留，因为它虽然提高了总分，但 `strategy_score` 下降，收益主要来自随机机制波动。
- 现在不要继续直接改 prompt。

已有 qwen3.6-27b dev 结果：

| run | output | proxy_dev_score | mechanism_accuracy | strategy_score | risk_label_f1 | response_reference_token_f1 |
|---|---|---:|---:|---:|---:|---:|
| original | `outputs/dev_submission_multi_v1_qwen36_27b.jsonl` | 61.213 | 0.6222 | 0.6222 | 0.6037 | 0.2019 |
| rerun | `outputs/dev_submission_multi_v1_qwen36_27b_rerun.jsonl` | 62.805 | 0.6667 | 0.6000 | 0.6259 | 0.2191 |

这说明 27B 存在明显随机波动。因此下一步必须先找 **两次运行都稳定出错的样本和错误类型**，不能根据单次结果改 prompt。

## 本轮目标

分析 qwen3.6-27b 在 `multi_v1` 架构下的稳定错误模式，回答：

1. 哪些样本在 original 和 rerun 中都错？
2. 哪些 `bragging_mechanism` 混淆是稳定的？
3. 哪些 `response_strategy` 误选是稳定的？
4. 哪些 risk label 缺失是稳定的？
5. 是否存在值得下一轮做“小步 calibration”的稳定模式？

## 严格限制

本轮不要修改任何核心代码：

- 不要改 `src/system_prompt_sections.py`
- 不要改 `src/system.py`
- 不要改 `src/BraggingResponseAgent.py`
- 不要改 `src/MultiAgentBraggingAgent.py`
- 不要改 `src/official_validator.py`
- 不要改 `run_multi_agent_official.py`

可以新增独立分析脚本和分析报告。

## 输入文件

请使用：

- `outputs/dev_submission_multi_v1_qwen36_27b.jsonl`
- `outputs/dev_submission_multi_v1_qwen36_27b_rerun.jsonl`
- `BRAG-Agent-public/data/dev_input.jsonl`
- `BRAG-Agent-public/data/dev_gold.jsonl`

如果文件不存在，请先用 `ls outputs` 和 `ls BRAG-Agent-public/data` 确认实际文件名，不要猜。

## 允许新增文件

可以新增：

- `scripts/analyze_qwen36_stability_badcases.py`
- `analysis/qwen36_27b_stability_badcases.md`

## 必做分析

### 1. 两次运行指标对比

复核并列出：

- `proxy_dev_score`
- `mechanism_accuracy`
- `strategy_score`
- `risk_label_f1`
- `response_reference_token_f1`
- `format errors`

### 2. 一致性分析

统计 45 条 dev 中：

- 两次 `bragging_mechanism` 完全一致的数量
- 两次 `response_strategy` 完全一致的数量
- 两次 `risk_assessment` 提取出的 risk labels 完全一致的数量
- 两次 `response_text` token F1 的平均差异

### 3. 稳定错误样本

列出两次运行都错的样本：

- mechanism 两次都错
- strategy 两次都低于 gold preferred / acceptable
- risk labels 两次都漏

每个样本包含：

- `episode_id`
- `speaker_post`
- gold mechanism / strategy / risk labels
- original prediction
- rerun prediction
- 错误是否一致
- 简短原因判断

### 4. 稳定 mechanism 混淆

生成两次运行共同出现的 mechanism confusion pairs，例如：

```text
gold understated_flex -> predicted achievement_drop
gold scarcity_flex -> predicted understated_flex
gold faux_modesty -> predicted self_aware_brag
```

只关注两次运行都出现或至少高频出现的混淆。不要根据只出现一次的错误提规则。

### 5. 稳定 strategy 错误

分析两次运行中是否稳定存在：

- 过度使用 `light_acknowledgment`
- 过度使用 `neutral_observation`
- 少用 `ask_followup`
- 少用 `humor_tease`
- 在 `avoid_sycophancy` 场景误用 `validate`
- 在 close friend / playful 场景过于冷淡

需要区分：

```text
稳定错误 = 两次都错，或同类错误重复出现
随机错误 = 只在一次运行里出现
```

### 6. 稳定 risk label 错误

统计两次运行都漏掉的 gold risk label：

- `misrecognition`
- `context_insensitivity`
- `sycophancy`
- `preachiness`
- `strategy_inconsistency`
- `over_coldness`

重点判断：

- qwen3.6-27b 是否稳定漏 `context_insensitivity`
- 是否稳定过度写 `sycophancy`
- 是否稳定漏 `misrecognition`

### 7. 下一轮 calibration 候选

根据稳定错误，最多提出 3 个候选。

每个候选必须包含：

| priority | target | evidence | proposed_change | expected_gain | risk | decision |
|---|---|---|---|---|---|---|

要求：

- 只允许建议“小步 prompt calibration”或“offline postprocess 分析”。
- 不允许建议大改架构。
- 不允许建议 full multi-agent debate。
- 不允许建议直接微调。
- 如果没有稳定错误模式，请明确建议不进入实现。

## 报告输出

新增：

- `analysis/qwen36_27b_stability_badcases.md`

报告结构：

```md
# qwen3.6-27b Stability Bad Case Analysis

## Summary

## Files Used

## Metrics Comparison

## Run-to-Run Consistency

## Stable Error Cases

## Stable Mechanism Confusions

## Stable Strategy Errors

## Stable Risk Label Errors

## Calibration Candidates

## Recommendation
```

## 最终汇报格式

最后请按下面格式汇报：

```text
qwen3.6-27b stability badcase analysis 完成

新增文件：
- ...

核心发现：
- ...

两次运行一致性：
- mechanism consistency:
- strategy consistency:
- risk label consistency:

稳定错误模式：
- mechanism:
- strategy:
- risk:

是否建议进入下一轮实现：
- 是 / 否

如果建议，下一轮最小实现范围：
- ...
```

