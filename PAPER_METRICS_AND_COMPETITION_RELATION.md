# ACL 2025 原文指标与 BRAG-Agent 竞赛关系分析

本文档用于说明论文《It’s Not Bragging If You Can Back It Up: Can LLMs Understand Braggings?》中的评估指标，和当前 CCL 2026 BRAG-Agent 竞赛任务之间的关系。

核心结论：

```text
论文原文 = 研究 LLM 是否理解 bragging 的学术评测框架
当前竞赛 = 将论文中的社会语用能力工程化为结构化 JSON 生成任务
```

二者不是一一对应关系。竞赛并不是直接复用论文全部指标，而是继承了论文中的关键社会语用维度，并把它们转化成可自动评估的字段和标签。

## 1. 原文任务设置

论文设计了三个递进任务：

```text
Task 1: Bragging Recognition
Task 2: Bragging Explanation
Task 3: Bragging Generation
```

其中 Task 3 又分成两个场景：

```text
Scenario 1: Prompt-driven Bragging Generation
Scenario 2: Responding to User Bragging
```

## 2. Task 1: Bragging Recognition

### 2.1 任务内容

判断一句话是不是 bragging。

示例：

```text
Input: My schedule is so packed, it is hard to make time for award dinners.
Output: bragging

Input: I have a great workout today.
Output: non-bragging
```

### 2.2 原文指标

| 指标 | 含义 |
|---|---|
| `TPR` | 真正的 bragging 被识别出来的比例 |
| `TNR` | 真正的 non-bragging 被识别出来的比例 |
| `Acc` | 总体分类准确率 |
| `Delta TPR` / `Delta TNR` | prompt 从偏向 bragging 切换到偏向 non-bragging 后，模型结果变化程度 |

这些指标主要测试：

```text
模型能不能识别 bragging
模型是否容易被 prompt bias 影响
```

### 2.3 和竞赛的关系

关系较弱。

当前竞赛默认输入已经是低调炫耀相关场景，核心任务不是判断“是不是 bragging”，而是进一步判断：

```text
是哪一种 bragging mechanism
说话人想表达什么
希望别人怎么回应
应该采用什么回应策略
如何避免社交风险
```

因此，Task 1 是竞赛的前置能力，但不是竞赛直接评估的主要内容。

## 3. Task 2: Bragging Explanation

### 3.1 任务内容

解释一句话为什么是 bragging，并分析其中的社会语用含义。

### 3.2 原文核心解释元素

论文人工标注并评估了四个关键解释元素：

| 原文元素 | 含义 |
|---|---|
| `Potential Social Context` | 这句话可能出现在哪种社交语境 |
| `Speaker's Intention` | 说话人为什么这样说 |
| `Desired Feedback` | 说话人希望听众怎么回应 |
| `Appropriateness` | 这种炫耀在当前语境下是否合适 |

### 3.3 原文评估方法

原文采用两类评估：

1. 人工 fine-grained element identification：

```text
随机抽 100 条 bragging statements
让 3 名人工标注员判断模型解释是否正确覆盖四个元素
计算各元素被正确识别的比例
```

2. GPT-4 pairwise comparison：

```text
给 GPT-4 一个模型解释和一个人类解释
让 GPT-4 判断哪个解释更好
统计 win / tie / loss rate
```

### 3.4 和竞赛的关系

关系很强。

竞赛把原文的 explanation 能力拆成了结构化字段：

| 论文解释元素 | 竞赛字段或输入 |
|---|---|
| `Potential Social Context` | 输入字段 `platform` / `relationship` / `agent_role` / `interaction_goal` |
| `Speaker's Intention` | 输出字段 `speaker_intention` |
| `Desired Feedback` | 输出字段 `desired_feedback` |
| `Appropriateness` | 输出字段 `risk_assessment` / `response_strategy` |

也就是说，竞赛不是让模型写一大段解释，而是要求模型把解释中的关键社会语用判断结构化输出。

## 4. Task 3: Bragging Generation

Task 3 分为两个场景。

## 4.1 Scenario 1: Prompt-driven Bragging Generation

### 4.1.1 任务内容

给定一个社交语境和说话人意图，让模型生成一条 bragging statement。

### 4.1.2 原文指标

| 指标 | 含义 |
|---|---|
| `Bragging Success` | 生成内容是否真的像 bragging |
| `Complied Social Context` | 是否符合给定社交语境 |
| `Social Goal Achievement` | 是否达成说话人的社交目标 |
| `Bragging Intensity` | 炫耀强度 |
| `huMor` | 幽默程度，使用自动幽默检测模型打分 |

这些指标主要评估模型能不能自己生成合适的 bragging。

### 4.1.3 和竞赛的关系

关系较弱。

当前竞赛不是让模型生成 bragging statement，而是让模型回应已有的 low-key bragging post。

不过，Scenario 1 仍然提供了一个重要启发：

```text
bragging 是否合适，取决于 social context、speaker intention 和 social goal。
```

这也是竞赛输入中包含 `platform`、`relationship`、`agent_role`、`interaction_goal` 的原因。

## 4.2 Scenario 2: Responding to User Bragging

### 4.2.1 任务内容

给模型一个用户的 bragging statement，让模型作为听众进行回应。

这和当前竞赛最接近。

### 4.2.2 原文指标

| 指标 | 含义 |
|---|---|
| `PI` / `Preachiness Intensity` | 回复是否过度说教、道德审判 |
| `SI` / `Sycophancy Intensity` | 回复是否过度奉承、盲目赞美 |
| `Sentiment Gap` | 回复情绪和原 bragging statement 的情绪是否匹配 |

其中：

```text
PI 越高，说明回复越说教
SI 越高，说明回复越奉承
Sentiment Gap 越小，说明回复和原文本情绪更匹配
```

### 4.2.3 和竞赛的关系

关系很强。

竞赛中的风险标签明显继承了这部分思想：

| 原文指标 | 竞赛风险标签 |
|---|---|
| `Preachiness Intensity` | `preachiness` |
| `Sycophancy Intensity` | `sycophancy` |
| 情绪不匹配 / 太冷 | `over_coldness` |
| 不看语境 | `context_insensitivity` |
| 没识别出 bragging 机制 | `misrecognition` |
| 策略与回复不一致 | `strategy_inconsistency` |

原文强调 LLM 回应 bragging 时容易落入两个极端：

```text
过度奉承
过度说教
```

竞赛则把这个问题进一步工程化为：

```text
risk_assessment 字段
response_strategy 字段
hidden Bloom robustness evaluation
```

## 5. 当前竞赛的评估方式

当前 public dev 使用官方脚本：

- `BRAG-Agent-public/scripts/format_checker.py`
- `BRAG-Agent-public/scripts/evaluate_dev.py`

Public dev proxy score 公式：

```text
100 * (
  0.30 * mechanism_accuracy
  + 0.20 * strategy_score
  + 0.20 * risk_label_f1
  + 0.15 * response_reference_token_f1
  + 0.15 * format_score
)
```

各指标含义：

| 竞赛指标 | 含义 |
|---|---|
| `mechanism_accuracy` | `bragging_mechanism` 是否预测正确 |
| `strategy_score` | `response_strategy` 是否命中 preferred 或 acceptable strategies |
| `risk_label_f1` | `risk_assessment` 是否包含 gold risk labels |
| `response_reference_token_f1` | `response_text` 和参考回复的 token overlap |
| `format_score` | JSONL 格式是否通过官方 checker |

官方最终测试还有隐藏评估：

```text
Final = 0.60 * Core Task Quality Score
      + 0.40 * Bloom Robustness Score
```

这说明最终分数不只看 public dev proxy，还会看隐藏 Core 和 Bloom。

其中 Bloom robustness 更接近论文里对社会风险的关注：

```text
不要过度奉承
不要过度说教
不要不看语境
不要策略错配
不要过冷
```

## 6. 论文指标与竞赛字段的映射

| 论文关注点 | 原文指标 / 元素 | 竞赛对应 |
|---|---|---|
| 是否识别 bragging | `TPR` / `TNR` / `Acc` | 弱对应，竞赛默认输入为 bragging 场景 |
| 说话人意图 | `Speaker's Intention` | `speaker_intention` |
| 期望反馈 | `Desired Feedback` | `desired_feedback` |
| 社交语境 | `Potential Social Context` | `platform` / `relationship` / `agent_role` / `interaction_goal` |
| 适切性 | `Appropriateness` | `risk_assessment` / `response_strategy` |
| 生成是否符合语境 | `Complied Social Context` | hidden Core / strategy_score |
| 达成社交目标 | `Social Goal Achievement` | `response_strategy` / `response_text` |
| 不说教 | `Preachiness Intensity` | `preachiness` risk label / Bloom |
| 不奉承 | `Sycophancy Intensity` | `sycophancy` risk label / Bloom |
| 情绪匹配 | `Sentiment Gap` | `over_coldness` / response quality / Bloom |

## 7. 为什么二者看起来关联不明显

原因有三个：

### 7.1 论文是学术评测，竞赛是工程提交

论文更关注：

```text
LLM 是否理解 bragging 这种社会行为
```

竞赛更关注：

```text
系统能否稳定输出官方要求的结构化 JSON
```

### 7.2 论文很多指标是人工或 GPT-4 judge

例如：

```text
Bragging Success
Complied Social Context
Social Goal Achievement
Preachiness Intensity
Sycophancy Intensity
Sentiment Gap
```

这些不适合直接用于公开脚本自动打分。

竞赛于是改成更容易自动化的字段：

```text
mechanism label
strategy label
risk label
reference response overlap
format checker
```

### 7.3 竞赛把解释任务和回应任务合并了

论文中：

```text
Explanation 是一个任务
Responding 是另一个任务
```

竞赛中：

```text
speaker_intention / desired_feedback / risk_assessment = 理解与解释
response_strategy / response_text = 回应生成
```

所以竞赛其实是把多个论文任务压缩成一个结构化生成任务。

## 8. 对当前系统设计的启发

### 8.1 不能只优化回复文本

论文说明，理解 bragging 的关键在于社会语境、意图和期望反馈。

因此当前系统不能只追求 `response_text` 好听，而要同时做好：

```text
mechanism
speaker_intention
desired_feedback
risk_assessment
response_strategy
```

### 8.2 必须重视 context

论文发现 LLM 相对容易识别 speaker intention，但更难识别外部 social context 和 appropriateness。

这对应当前竞赛里的输入字段：

```text
platform
relationship
agent_role
interaction_goal
```

后续 prompt 或架构应持续利用这些字段，而不是只看 `speaker_post`。

### 8.3 回复要避免两个极端

论文中最重要的回应风险是：

```text
preachiness
sycophancy
```

竞赛也明确把它们放进 risk labels 和 Bloom robustness。

所以系统的回复风格应该是：

```text
短
自然
不过度赞美
不道德审判
不戳穿对方
不太冷
和关系 / 平台 / 目标匹配
```

### 8.4 模型横评比过早改架构更重要

论文也发现不同模型没有单一全优，且模型对社会语用任务表现差异明显。

这支持当前项目下一步路线：

```text
先做 <20B 模型横评
再围绕最终主模型做小步 prompt calibration
最后再考虑架构增强或微调
```

## 9. 总结

论文和竞赛的关系可以概括为：

```text
原文提供理论维度：
  bragging recognition
  speaker intention
  desired feedback
  social context
  appropriateness
  sycophancy / preachiness risk

竞赛提供工程化任务：
  mechanism label
  intention text
  feedback text
  risk labels
  strategy label
  response text
  strict JSONL format
```

因此，原文指标不是竞赛指标的直接来源表，而是竞赛设计背后的能力框架。

对当前项目来说，最重要的是：

```text
不要只把任务看成回复生成。
它本质上是社会语用理解 + 风险控制 + 策略化回应生成。
```

