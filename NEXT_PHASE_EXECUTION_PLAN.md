# BRAG-Agent 下一阶段执行规划

本文档用于指导当前阶段之后的实验顺序、代码 Agent 分工和版本取舍。当前项目已经证明：盲目扩大 prompt、多 Agent 复杂化、端到端 reranker 都容易带来不稳定收益。因此下一阶段的核心原则是：

```text
先定最终候选模型
再固定 baseline 架构
然后做小步 prompt / validator 校准
最后再考虑架构增强或微调
```

## 1. 当前状态

当前主线代码应视为：

```text
multi_v1 架构 + qwen3.6-27b 临时开发模型
```

其中 `multi_v1` 架构是：

```text
Input JSONL
-> BraggingResponseAgent 生成完整 7 字段 JSON
-> official_validator 本地校验
-> 如果通过，直接输出
-> 如果存在 hard issue，调用 Rewriter 最多修一次
-> 最终输出官方 JSONL
```

当前模型配置：

```text
QWEN_MODEL=qwen3.6-27b
```

说明：

- `qwen3.6-27b` 只是临时开发模型，不作为最终提交模型。
- 最终模型必须重新按官方限制确认，尤其是参数规模是否小于 20B。
- 当前不要继续为了 27B 深度调 prompt，因为 27B 上有效的规则不一定能迁移到最终小模型。

## 2. 已经验证过但不保留的实验

### 2.1 multi_v1.1

改动：

- 加重 social pragmatic checklist
- 加 RoT social norms
- 加 strategy matrix
- 增强 context-aware validator

结果：

```text
proxy_dev_score 明显下降
risk_label_f1 明显下降
```

结论：

```text
不保留。prompt 变重会稀释模型对核心标签和 risk label 的注意力。
```

### 2.2 multi_v1.1-lite-a

改动：

- 只加强 `understated_flex` vs `achievement_drop` 的边界提示。

结果：

```text
总分小涨，但 risk_label_f1 下降，understated_flex 命中数没有提升。
```

结论：

```text
不保留。即使小 prompt 改动也可能误伤 risk 和 strategy。
```

### 2.3 multi_v1.2 mechanism reranker

改动：

- 加 mechanism-only reranker。
- 只处理 `understated_flex` 和 `achievement_drop`。
- 只允许改 `bragging_mechanism`。

结果：

```text
reranker changed = 0
端到端分数下降主要来自重新调用 generator 的随机漂移
```

结论：

```text
不保留。后处理类实验必须 offline 跑在固定输出上，不能重新生成一遍。
```

### 2.4 qwen3.6-27b calib_a

改动：

- 针对 27B 做 strategy prompt calibration。

结果：

```text
总分比 27B 原始结果高，但 strategy_score 下降。
收益主要来自 mechanism 随机波动，不是目标修复。
```

结论：

```text
不保留。不要继续围绕 27B 做深度 prompt tuning。
```

## 3. 下一阶段总目标

下一阶段目标不是马上追求单次最高 dev 分，而是建立一个稳定、可迁移、符合最终提交限制的系统。

优先目标：

1. 明确最终可用的 `<20B` 候选模型池。
2. 用同一个 `multi_v1` 架构横评候选模型。
3. 选出一个主模型和一个备选模型。
4. 围绕主模型做小步校准。
5. 判断是否需要升级到轻量两阶段或局部后处理。
6. 只有在数据足够时再考虑微调。

## 4. 推荐执行路线

### Phase 1: 模型池确认

目标：先确定哪些模型可以作为最终候选。

需要确认：

- 官方是否严格要求 `<20B`。
- 是否允许闭源 API。
- 是否允许多次模型调用。
- 是否允许不同模型组合。
- 是否限制推理时间、成本或并发。

候选模型建议至少包括：

```text
qwen 系列 <= 14B
qwen 系列 7B
其他中文/英文强指令模型 <= 20B
当前 qwen3.6-27b 仅作为临时参考，不进入最终候选
```

输出文档：

```text
analysis/model_candidate_pool.md
```

文档内容：

- 模型名
- 参数规模
- 是否符合官方限制
- 调用方式
- 预估速度
- 预估成本
- 是否支持当前 OpenAI-compatible API
- 是否进入 dev 横评

### Phase 2: 固定 multi_v1 做模型横评

目标：用完全相同的代码和 prompt 比较候选模型。

固定项：

- 架构：`multi_v1`
- prompt：当前 v1 prompt
- validator：当前 v1 validator
- runner：`run_multi_agent_official.py`
- dev 数据：官方 45 条 dev
- 评估脚本：官方 `format_checker.py` 和 `evaluate_dev.py`

每个模型输出：

```text
outputs/dev_submission_model_<model_name>.jsonl
outputs/dev_score_report_model_<model_name>.json
```

横评报告：

```text
analysis/model_selection_report.md
```

必须比较：

- `proxy_dev_score`
- `mechanism_accuracy`
- `strategy_score`
- `risk_label_f1`
- `response_reference_token_f1`
- `format_checker errors`
- rewrite triggered
- 平均耗时
- 是否稳定

主模型选择标准：

```text
优先选 format 稳、strategy 稳、risk 稳、总体分高的模型。
不要只看单次 proxy_dev_score。
```

### Phase 3: 主模型 bad case 分析

目标：只针对最终主模型分析，不再围绕 27B 深调。

输出：

```text
analysis/main_model_badcases.md
```

必做分析：

- mechanism confusion matrix
- strategy confusion / acceptable hit
- risk label missing pattern
- response_text 风格问题
- Bloom 风险人工抽查

重点判断：

```text
哪些错误是稳定模式？
哪些错误只是随机波动？
哪些适合 prompt 小改？
哪些适合本地 validator？
哪些不值得修？
```

### Phase 4: 小步 prompt calibration

只有在 bad case 分析发现稳定模式时才改 prompt。

每轮只允许：

```text
一个目标
一个文件
不超过 120 英文词
完整 dev 复测
和主模型 baseline 对比
```

优先级：

1. strategy 边界校准
2. mechanism 混淆边界校准
3. risk label 输出稳定性
4. response_text 风格压缩

不建议：

- 大幅增加 few-shot
- 加完整 strategy matrix
- 加长 social norm checklist
- 一次性改多个字段逻辑

版本命名：

```text
main_model_calib_a
main_model_calib_b
main_model_calib_c
```

保留标准：

```text
format_checker = 0 errors
proxy_dev_score 高于主模型 baseline
目标指标提升
risk_label_f1 不下降超过 1pp
strategy_score 不下降超过 1pp
人工抽查 Bloom 风险不变差
```

### Phase 5: 轻量架构增强

只有在主模型 prompt calibration 到达瓶颈后，才考虑架构增强。

推荐顺序：

```text
local validator enhancement
-> offline postprocess
-> conditional rewriter
-> soft two-stage understander/responder
-> candidate reranking
-> full multi-agent debate
```

当前不建议直接做 full multi-agent debate。

如果做两阶段，推荐先做 soft two-stage：

```text
一次模型调用中显式要求：
1. understand: mechanism / intention / desired feedback / risk
2. plan: strategy
3. respond: response_text
4. output: final JSON only
```

不要一开始拆成多次 LLM 调用。多次调用会增加随机性、成本和格式风险。

### Phase 6: 微调判断

微调不应该现在开始。

只有满足以下条件才考虑微调：

- 最终主模型已经确定。
- 有足够多高质量训练样本。
- 有 dev 之外的验证集或交叉验证方案。
- 已经明确 prompt 无法解决某类稳定错误。
- 微调成本和提交环境允许。

如果官方训练数据只有少量 dev/gold，直接微调风险很高：

```text
容易过拟合 public dev
容易损害 response_text 自然度
容易学到错误的 strategy 偏好
```

更现实的微调方向：

```text
只微调 mechanism / strategy 分类器
或用弱监督数据做轻量 LoRA
不要一开始微调整个 JSON 生成器
```

## 5. 近期具体任务清单

### Task A: 确认模型限制和候选模型池

负责人：规划 Agent + 代码 Agent

产出：

```text
analysis/model_candidate_pool.md
```

验收：

- 至少 3 个 `<20B` 候选模型
- 每个模型写清楚是否符合官方限制
- 标明调用方式和运行命令

### Task B: 用 multi_v1 横评候选模型

负责人：代码 Agent

产出：

```text
outputs/dev_submission_model_*.jsonl
outputs/dev_score_report_model_*.json
analysis/model_selection_report.md
```

验收：

- 每个模型 45 条 dev 全部跑完
- format_checker 0 errors
- evaluate_dev 有完整结果
- 报告给出主模型和备选模型建议

### Task C: 主模型 bad case 分析

负责人：代码 Agent

产出：

```text
analysis/main_model_badcases.md
```

验收：

- mechanism confusion matrix
- strategy 错误分析
- risk label 缺失分析
- 至少 10 个代表性 bad case
- 明确下一步是否值得 prompt calibration

### Task D: 小步 calibration 实验

负责人：代码 Agent

产出：

```text
analysis/main_model_calib_a_report.md
outputs/dev_submission_main_model_calib_a.jsonl
outputs/dev_score_report_main_model_calib_a.json
```

验收：

- 只改一个点
- 完整复测
- 明确保留或回退

### Task E: 最终提交候选锁定

负责人：规划 Agent + 代码 Agent

产出：

```text
analysis/final_submission_decision.md
```

验收：

- 明确最终模型
- 明确最终架构
- 明确最终运行命令
- 明确是否保留 calibration
- 明确风险和备选方案

## 6. 给代码 Agent 的当前推荐任务

下一步最适合让代码 Agent 做：

```text
不要改核心代码。
先整理 model_candidate_pool.md。
然后用当前 multi_v1 对 2-3 个 <20B 候选模型跑 dev 横评。
最后生成 model_selection_report.md。
```

建议代码 Agent prompt：

```text
你现在负责 BRAG-Agent 的模型选择阶段。当前架构固定为 multi_v1，不允许修改 src/ 下核心代码，不允许改 prompt，不允许加新 agent。

任务：
1. 确认可用的 <20B 候选模型池，写入 analysis/model_candidate_pool.md。
2. 对每个候选模型使用 run_multi_agent_official.py 跑官方 dev 45 条。
3. 每个模型都运行 format_checker.py 和 evaluate_dev.py。
4. 生成 analysis/model_selection_report.md。
5. 报告中比较 proxy_dev_score、mechanism_accuracy、strategy_score、risk_label_f1、response_reference_token_f1、format errors、rewrite triggered、平均耗时。
6. 只给出主模型和备选模型建议，不要修改代码。

注意：
- qwen3.6-27b 只作为临时参考，不作为最终候选。
- 不要为了某个模型调 prompt。
- 如果某个模型跑不通，记录失败原因，不要伪造结果。
```

## 7. 当前决策

当前阶段的关键决策是：

```text
先选最终 <20B 主模型。
在主模型确定前，不继续改架构，不做微调，不继续为 27B 调 prompt。
```

这是为了避免把时间花在不能最终提交的模型或不可迁移的 prompt 调整上。

