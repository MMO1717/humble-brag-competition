# BRAG-Agent 后续优化与代码执行规划

本文档用于统一后续实验版本命名、改进方向和代码 Agent 的执行任务。当前项目目标不是单纯生成“好听回复”，而是构建一个能通过官方评估的结构化社交回应系统。

## 1. 最终系统主线

目标流程：

```text
输入样本
-> 机制识别
-> 意图与期望反馈分析
-> 风险识别
-> 策略选择
-> 英文社交回复生成
-> 规则校验
-> 必要时重写
-> 官方 JSONL 输出
```

当前主线应围绕官方 v6 数据、官方 7 字段输出和官方 format checker / dev evaluator 迭代。

## 2. 版本命名

后续统一使用以下命名，避免 ablation 混乱：

```text
single_v3_1 = 当前最强单 Agent baseline
multi_v1    = 当前已实现的多 Agent 初版
multi_v2    = 下一轮要优化的多 Agent 版本
```

不要再混用“单 Agent v2”作为当前基准名称。历史版本可以保留在 archive 中，但当前实验报告应以上述版本名为准。

## 3. 当前项目状态

### 已完成

当前项目已经具备：

- 官方数据集接入：`BRAG-Agent-public/data/*.jsonl`
- 官方格式检查脚本：`BRAG-Agent-public/scripts/format_checker.py`
- 官方 dev proxy 评估脚本：`BRAG-Agent-public/scripts/evaluate_dev.py`
- 主生成 Agent：`src/BraggingResponseAgent.py`
- Prompt 模块：`src/system.py`、`src/system_prompt_sections.py`
- 规则校验器：`src/official_validator.py`
- 多 Agent 初版：`src/MultiAgentBraggingAgent.py`
- 多 Agent runner：`run_multi_agent_official.py`
- 当前多 Agent dev 输出：`outputs/dev_submission_multi_v1.jsonl`
- 当前多 Agent dev 分数报告：`outputs/dev_score_report_multi_v1.json`
- 当前多 Agent 对比报告：`analysis/multi_agent_ablation.md`

说明：如果历史文档中提到 `run_official.py`，应视为旧版或计划中的单 Agent runner。当前活跃主入口是 `run_multi_agent_official.py`。

### 下一步不是从零实现

后续工作重点是迭代增强：

- 强化 `src/official_validator.py`
- 优化 `src/MultiAgentBraggingAgent.py` 的 rewrite 触发条件
- 优化 Critic/Rewriter 的重写策略
- 做 `single_v3_1` vs `multi_v1` vs `multi_v2` 对比

## 4. 核心优化路线

### 4.1 固定 single_v3_1 作为 baseline

先不要频繁改动当前最强单 Agent baseline。它是所有后续实验的参照物。

每次新版本都至少比较：

```text
single_v3_1
multi_v1
multi_v2
```

对比指标：

- `proxy_dev_score`
- `mechanism_accuracy`
- `strategy_score`
- `risk_label_f1_from_risk_assessment`
- `response_reference_token_f1`
- `format_checker` errors
- rewrite 触发率
- Bloom 风险人工抽查结果

### 4.2 强化 mechanism 判别表

目标不是让模型背定义，而是让模型学会根据文本线索做判断。

重点继续修：

```text
faux_modesty vs understated_flex
scarcity_flex
comparison_superiority
achievement_drop
humble_complaint
```

推荐加入或强化以下判别线索：

| 机制 | 关键线索 | 典型判断问题 |
| --- | --- | --- |
| `faux_modesty` | 表面谦虚、抱歉、不好意思、降低姿态 | 是否在用谦虚包装成就？ |
| `understated_flex` | 轻描淡写提到高价值事实 | 是否没有明显谦虚包装，但事实本身在炫耀？ |
| `scarcity_flex` | 稀缺机会、特殊待遇、名人接触、独家邀请 | 是否强调“少数人才能得到”的经历？ |
| `comparison_superiority` | 和别人比较、暗示更强、更快、更优秀 | 是否通过比较制造优越感？ |
| `achievement_drop` | 顺手丢出成绩、奖项、身份、成果 | 是否把成就作为背景信息带出来？ |
| `humble_complaint` | 把好事包装成负担、麻烦、疲惫 | 是否在抱怨一个其实令人羡慕的事情？ |

### 4.3 强化 strategy matrix

策略选择必须绑定：

```text
platform + relationship + agent_role + interaction_goal
```

不要只看 `speaker_post` 内容。

推荐矩阵：

| 条件 | 优先策略 |
| --- | --- |
| `avoid_sycophancy` | `neutral_observation` / `redirect` |
| `stay_neutral` | `neutral_observation` |
| `close_friend` + playful context | `humor_tease` / `light_acknowledgment` |
| `academic_forum` | `neutral_observation` / `ask_followup` |
| `be_supportive_without_overpraising` | `light_acknowledgment` / `validate` |
| `deescalate_awkwardness` | `humor_tease` / `redirect` |
| `workplace_channel` + professionalism | `neutral_observation` / `redirect` |
| pressure for praise / comparison | `set_boundary` / `redirect` |

注意：`validate` 不能在 `avoid_sycophancy` 场景中过度使用；`set_boundary` 不能在普通轻松分享中滥用。

### 4.4 强化 Rule Validator

`src/official_validator.py` 已经存在，下一步不是新建，而是增强。

重点检查：

- `risk_assessment` 是否包含官方风险标签
- `response_text` 是否为英文
- `response_strategy` 和 `response_text` 是否一致
- 是否过度奉承
- 是否说教
- 是否过冷
- 是否把普通分享误判成强炫耀
- `no_response` 是否真的短或空
- `set_boundary` 是否被滥用
- `validate` 是否在 `avoid_sycophancy` 场景过度使用

Validator 的目标不是替模型打分，而是筛出“必须修”的 hard issue。

### 4.5 优化 MultiAgentBraggingAgent

`multi_v2` 的重点是：少改、只改坏样本。

推荐触发逻辑：

```text
没有 hard issue -> 直接保留 Generator 输出
有 hard issue -> 调用 Critic/Rewriter
soft issue 太多 -> 可选重写
重写最多 1 次
重写后如果变差 -> 回退原答案
```

不要每条都重写。多 Agent 最容易的问题是把原本好的输出改坏，或者让回复变得啰嗦、模板化、过度安全。

### 4.6 加 Bloom 风险 gate

官方最终分：

```text
Final = 0.60 * Core + 0.40 * Bloom
```

因此，即使某个版本 dev proxy 更高，只要它明显更容易出现以下问题，也不能直接作为最终提交：

```text
sycophancy
strategy_inconsistency
context_insensitivity
misrecognition
preachiness
over_coldness
```

最终选择要同时看：

- dev proxy 高
- format 稳
- Bloom 风险低
- 输出风格稳定

不能只看 public dev 分数。

## 5. 代码 Agent 执行任务

### Task 1: 汇总现有版本指标

目标：确认 `single_v3_1` 和 `multi_v1` 的完整指标。

需要产出：

- `analysis/current_baseline_summary.md`

内容包括：

- `single_v3_1` 指标
- `multi_v1` 指标
- 当前最主要 bad cases
- 当前 rewrite 触发率
- 当前 format checker 结果

如果缺少单 Agent 最新输出，需要先确认历史文件是否在 `archive/outputs/` 中。

### Task 2: 强化 official_validator.py

目标：让 Validator 能识别更多“必须修”的 hard issue。

建议新增检查函数：

```text
detect_strategy_context_mismatch(row, input_context)
detect_response_strategy_mismatch(row)
detect_over_coldness(row)
detect_preachiness(row)
detect_validate_in_avoid_sycophancy(row, input_context)
detect_set_boundary_overuse(row, input_context)
```

注意：

- 保持纯本地规则，不调用模型。
- 不要让 Validator 变成复杂打分器。
- hard issue 要少而准，避免误触发大量重写。

### Task 3: 优化 MultiAgentBraggingAgent 触发逻辑

目标：让 `multi_v2` 只重写明显有问题的样本。

建议改动：

- 记录 generator 初稿 validation 结果
- 只在 hard issue 存在时触发 Rewriter
- soft issue 超过阈值时可选触发
- Rewriter 输出后再次校验
- 如果 Rewriter 后 hard issue 更多，回退原输出
- 输出 metadata 记录 rewrite 原因

### Task 4: 生成 multi_v2 输出

运行：

```bash
python run_multi_agent_official.py \
  --input BRAG-Agent-public/data/dev_input.jsonl \
  --output outputs/dev_submission_multi_v2.jsonl \
  --concurrency 3
```

格式检查：

```bash
python BRAG-Agent-public/scripts/format_checker.py \
  outputs/dev_submission_multi_v2.jsonl \
  BRAG-Agent-public/data/dev_input.jsonl
```

dev 评估：

```bash
python BRAG-Agent-public/scripts/evaluate_dev.py \
  BRAG-Agent-public/data/dev_input.jsonl \
  BRAG-Agent-public/data/dev_gold.jsonl \
  outputs/dev_submission_multi_v2.jsonl
```

### Task 5: 生成对比报告

新增：

```text
analysis/single_v3_1_vs_multi_v1_vs_multi_v2.md
```

报告必须包含：

- 三个版本的完整指标表
- 每个版本的 format checker 结果
- `mechanism_accuracy` 变化
- `strategy_score` 变化
- `risk_label_f1` 变化
- `response_reference_token_f1` 变化
- rewrite 触发率
- 最常见 bad case 类型
- Bloom 风险人工抽查结论
- 最终推荐提交版本

## 6. 最终执行顺序

```text
1. 固定 single_v3_1 为 baseline
2. 汇总 single_v3_1 的完整 dev 指标和 bad case
3. 汇总 multi_v1 的完整 dev 指标和 bad case
4. 强化 official_validator.py
5. 调整 MultiAgentBraggingAgent 的 rewrite 触发条件
6. 生成 multi_v2
7. 跑 dev 45 条
8. 跑 format_checker
9. 跑 evaluate_dev
10. 生成 analysis/single_v3_1_vs_multi_v1_vs_multi_v2.md
11. 人工抽查 Bloom 高风险样本
12. 决定最终提交 single_v3_1 还是 multi_v2
```

## 7. 最终判断规则

推荐决策规则：

```text
如果 multi_v2 dev proxy 明显高于 single_v3_1，且 Bloom 风险没有变高：
    选 multi_v2

如果 multi_v2 只提升 risk_label_f1，但 mechanism/strategy 明显下降：
    不选 multi_v2，继续调触发条件

如果 single_v3_1 分数最高且输出稳定：
    选 single_v3_1，Validator 仅作为离线检查工具

如果 multi_v2 dev 分略低，但 Bloom 人工抽查明显更稳：
    谨慎优先考虑 multi_v2，因为隐藏 Bloom 占 40%
```

## 8. 模型合规提醒

如果参加官方 `<=20B` track：

- 所有 Generator / Critic / Rewriter / Reranker 使用的模型都必须单独 `<=20B`。
- 使用闭源 API 生成、筛选、重写或蒸馏 test 输出，可能只能作为 non-eligible reference baseline。
- 如果使用 DashScope/Qwen API 做开发，应在最终提交前确认官方是否允许该模型与调用方式进入正式赛道。

## 9. 总结

最现实的高分路线：

```text
单 Agent prompt 打准核心判断
+ Rule Validator 保证格式和风险标签
+ Conditional Rewriter 修少数硬错误
+ bad case 驱动小步迭代
+ Bloom 风险 gate 控制隐藏集风险
```

当前阶段不需要推翻现有系统。重点是让 `multi_v2` 在不改坏好样本的前提下，稳定修复 `multi_v1` 暴露出的 hard issues。
