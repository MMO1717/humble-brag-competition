# BRAG-Agent 当前项目汇报

## 1. 项目目标

目标是让模型理解社交语境中的低调炫耀现象，并根据官方定义的机制类别、回应策略和风险要求，生成结构化 JSONL 输出。

需要完成的任务：

```text
凡尔赛机制识别
-> 说话人意图分析
-> 期望反馈判断
-> 社交风险识别
-> 回应策略选择
-> 英文社交回复生成
-> 官方格式校验
```

最终输出需要符合官方 7 字段格式：

```json
{
  "episode_id": "...",
  "bragging_mechanism": "...",
  "speaker_intention": "...",
  "desired_feedback": "...",
  "risk_assessment": "...",
  "response_strategy": "...",
  "response_text": "..."
}
```

## 2. 当前 Baseline 架构

当前主线保留的是 `multi_v1` 架构。它是一个轻量的“生成 + 校验 + 必要时重写”框架。

当前流程：Generator Agent + Rewriter Agent

```text
Input JSONL
-> BraggingResponseAgent
-> build_system_prompt()
-> build_user_prompt()
-> 调用 Qwen / DashScope API
-> 模型一次性生成完整 7 字段 JSON
-> JSON 解析与基础校验
-> official_validator 本地规则校验
-> 如果通过，直接输出
-> 如果存在 hard issue，调用 Rewriter 最多修一次
-> 最终输出官方 JSONL
```

核心文件：

- `run_multi_agent_official.py`：官方 dev/test 批量运行入口。
- `src/BraggingResponseAgent.py`：主生成 Agent，负责调用模型生成完整 JSON。
- `src/system.py`：组装 system prompt 和 user prompt。
- `src/system_prompt_sections.py`：存放模块化 prompt 内容。
- `src/official_validator.py`：本地规则校验器。
- `src/MultiAgentBraggingAgent.py`：封装 Generator -> Validator -> optional Rewriter 流程。

当前模型配置：

```text
QWEN_MODEL=qwen3.6-27b
```

说明：`qwen3.6-27b` 目前只是临时的测试模型（电脑带不动本地模型）。所以调用了API进行的baseline测试

## 3. 当前架构特点

### 3.1 优点

- 官方 JSONL 格式稳定，format checker 能保持 0 errors。
- 架构简单，可控，便于横向比较不同模型。
- Validator 能兜底 schema、枚举、风险标签等硬错误。
- Rewriter 只在必要时触发，避免每条样本都被二次生成改坏。
- 适合作为后续模型选择和 prompt calibration 的统一 baseline。

### 3.2 局限

- 目前主要是“一次性生成 7 字段”，没有显式拆成 Understander -> Planner -> Responder。
- Validator 仍偏规则检查，对语境级风险理解有限。
- Rewriter 只处理 hard issue，不主动修复细粒度策略错误。
- 不同模型对同一 prompt 的反应差异较大，说明 prompt 还需要针对最终模型校准。

## 4. 已完成实验与测试结果

### 4.1 multi_v1 baseline

`multi_v1` 是目前保留的主线版本。



历史最好一次 multi_v1 结果：

| 指标 | 结果 |
|---|---:|
| proxy_dev_score | 66.182 |
| mechanism_accuracy | 0.7333 |
| strategy_score | 0.6667 |
| risk_label_f1 | 0.6593 |
| response_reference_token_f1 | 0.1776 |
| format errors | 0 |

结论：

```text
multi_v1 是目前最稳定、最适合作为后续实验基线的版本。
```

### 4.2 multi_v1.1（曾经做过的探索）

实验内容：

- 增加 social pragmatic checklist。
- 增加 RoT social norms。
- 增加 strategy selection matrix。
- 增强 context-aware validator。

结果：

| 指标 | multi_v1 rerun | multi_v1.1 | 变化 |
|---|---:|---:|---:|
| proxy_dev_score | 65.309 | 59.893 | -5.4 |
| mechanism_accuracy | 0.7111 | 0.6444 | -6.7pp |
| strategy_score | 0.6556 | 0.6111 | -4.4pp |
| risk_label_f1 | 0.6519 | 0.5222 | -13.0pp |
| response_token_f1 | 0.1761 | 0.1929 | +1.7pp |
| format errors | 0 | 0 | - |

结论：

```text
不保留。大幅扩展 prompt 会稀释模型对机制、策略和风险标签的注意力。
```

### 4.3 multi_v1.1-lite-a

实验内容：

- 只对 `understated_flex` 和 `achievement_drop` 的边界加入短提示。

结果：

| 指标 | multi_v1 rerun | lite-a | 变化 |
|---|---:|---:|---:|
| proxy_dev_score | 65.309 | 65.478 | +0.17 |
| mechanism_accuracy | 0.7111 | 0.7333 | +2.2pp |
| strategy_score | 0.6556 | 0.6444 | -1.1pp |
| risk_label_f1 | 0.6519 | 0.6259 | -2.6pp |
| response_reference_token_f1 | 0.1761 | 0.2047 | +2.9pp |
| format errors | 0 | 0 | - |

结论：

```text
不保留。总分小涨但目标机制没有实际提升，risk_label_f1 下降超出容忍范围。
```





## 5. 当前主要经验结论

### 5.1 大 prompt 不一定更好

`multi_v1.1` 证明，加入过多 social checklist、strategy matrix、RoT 规则，会让模型注意力分散，导致机制识别和风险标签下降。

### 5.2 小 prompt 也可能误伤

`multi_v1.1-lite-a` 说明，即使只加一小段机制边界提示，也可能影响 risk 和 strategy。

### 5.3 后处理实验必须 offline

`multi_v1.2` 说明，如果重新调用 generator，分数变化会被随机漂移污染。后续 postprocess / reranker 应该先跑在固定输出文件上。



## 6. 理想最终系统目标

最终希望形成的系统不是简单的单次生成，而是一个稳定的结构化社交回应系统：

```text
输入样本
-> Understander: 识别凡尔赛机制、说话人意图、期望反馈、风险
-> Planner: 根据 platform / relationship / agent_role / interaction_goal 选择回应策略
-> Responder: 生成自然、短、英文、高情商的社交回复
-> Validator: 检查 schema、枚举、风险标签、策略一致性、Bloom 风险
-> Conditional Rewriter: 只在 hard issue 时修复
-> Final JSONL
```

理想目标：

- `format_checker = 0 errors`
- `mechanism_accuracy` 稳定高于当前 baseline
- `strategy_score` 稳定高于当前 baseline
- `risk_label_f1` 不因 prompt 调整明显下降
- `response_text` 简短、自然、不过度奉承、不说教、不太冷
- 对 hidden Bloom 测试更加稳健
- 最终模型符合官方 `<20B` 限制

## 7. 下一步计划

### Step 1: 确认最终候选模型池



需要整理：

- 模型名
- 参数规模
- 是否符合 `<20B`
- 是否支持当前 API
- 速度和成本
- 是否进入 dev 横评

产出：

```text
analysis/model_candidate_pool.md
```

### Step 2: 固定 multi_v1 横评模型

用完全相同的架构和 prompt，对 2-3 个 `<20B` 候选模型跑 dev。

固定：

```text
架构 = multi_v1
prompt = v1 prompt
validator = v1 validator
runner = run_multi_agent_official.py
```

产出：

```text
outputs/dev_submission_model_<model_name>.jsonl
outputs/dev_score_report_model_<model_name>.json
analysis/model_selection_report.md
```

### Step 3: 选择主模型和备选模型

选择标准：

- format 是否稳定
- mechanism 是否稳定
- strategy 是否稳定
- risk label 是否稳定
- response_text 是否自然
- 推理速度和成本是否可接受

不要只看单次 `proxy_dev_score`。

### Step 4: 针对主模型做 bad case 分析

只对最终主模型做深度分析。

产出：

```text
analysis/main_model_badcases.md
```

重点分析：

- mechanism confusion matrix
- strategy 误选模式
- risk label 缺失模式
- response_text 风格问题
- Bloom 风险人工抽查

### Step 5: 小步 prompt calibration

只有在 bad case 分析发现稳定错误模式时才改 prompt。

规则：

```text
每轮只改一个点
只改一个文件
新增 prompt 不超过 120 英文词
完整 dev 复测
明确保留或回退
```

### Step 6: 必要时再做架构增强

如果主模型 + 小步 prompt 已经到瓶颈，再考虑：

```text
local validator enhancement
-> offline postprocess
-> conditional rewriter
-> soft two-stage understander/responder
```

暂时不建议直接做复杂 debate-style multi-agent。

### Step 7: 最后再考虑微调

微调不是当前优先级。

只有满足以下条件才考虑：

- 最终主模型已确定。
- 有足够高质量训练样本。
- 有 dev 之外的验证方式。
- prompt 和轻量架构已到瓶颈。
- 微调后的模型仍符合官方限制。

更现实的微调方向是：

```text
优先微调 mechanism / strategy 分类器
不要一开始微调整个 JSON 生成器
```
### PS：可以进行另外的尝试
使用规划 Agent + 代码 Agent的方案，但是效果不好，可以同时进行尝试
在识别场景和输出的话分别调用两次模型

