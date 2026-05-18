# multi_v1 vs multi_v1.1 对比报告

## 1. 版本分数总览

| 指标 | multi_v1 (历史) | multi_v1 (rerun) | multi_v1.1 (本轮) |
|------|----------------|-------------------|-------------------|
| proxy_dev_score | 66.182 | 65.309 | **59.893** |
| mechanism_accuracy | 0.7333 | 0.7111 | 0.6444 |
| strategy_score | 0.6667 | 0.6556 | 0.6111 |
| risk_label_f1 | 0.6667 | 0.6519 | 0.5222 |
| response_reference_token_f1 | 0.1754 | 0.1761 | 0.1929 |
| format errors | 0 | 0 | 0 |
| rewrite triggered | 1 | 1 | 1 |

## 2. 各维度变化分析

### mechanism_accuracy: 0.7111 -> 0.6444 (下降 6.7pp)
multi_v1.1 的机制识别准确率明显下降。新增的 social-pragmatic checklist 和 mechanism discrimination table 可能导致模型在多个机制间犹豫，反而降低了判断准确率。

### strategy_score: 0.6556 -> 0.6111 (下降 4.4pp)
策略选择矩阵的加入没有提升策略准确率。可能原因：策略矩阵增加了 prompt 长度，稀释了模型对关键策略规则的注意力。

### risk_label_f1: 0.6519 -> 0.5222 (下降 13.0pp)
这是最显著的下降。新增的 risk_assessment 输出格式要求（"Main risk: X. Secondary risk: Y."）可能导致模型过度关注格式而忽略了准确选择风险标签。之前的简洁格式反而更有效。

### response_reference_token_f1: 0.1761 -> 0.1929 (提升 1.7pp)
response 质量略有提升，说明 RoT social norms 和策略约束对回复质量有轻微正面影响。

### format errors: 0 -> 0
格式检查通过，无错误。

## 3. Rewrite 触发情况

| 版本 | 触发次数 | 触发原因 | 结果 |
|------|---------|---------|------|
| multi_v1 | 1 | overpraise_mismatch | success |
| multi_v1.1 | 1 | overpraise_mismatch | success |

rewrite 触发率相同，均为 1/45 (2.2%)。context-aware validator 的新检查项没有额外触发 rewrite。

## 4. Bad Case 分析

### Case 1: risk_label 偏移
multi_v1.1 在 risk_label_f1 上大幅下降（0.6519 -> 0.5222），说明新增的 risk_assessment 输出格式要求干扰了模型的风险标签选择。模型可能过度关注"Main risk: X. Secondary risk: Y."格式，而忽略了准确匹配官方风险关键词。

### Case 2: mechanism 判断漂移
mechanism_accuracy 从 0.7111 降至 0.6444，说明新增的 mechanism discrimination table 虽然详细，但可能让模型在相似机制间产生混淆（如 humble_complaint vs faux_modesty）。

### Case 3: strategy 选择偏差
strategy_score 从 0.6556 降至 0.6111，策略选择矩阵的优先级规则可能过于复杂，导致模型在某些情况下选择了次优策略。

## 5. 结论与建议

### 是否保留 multi_v1.1?

**不建议保留。**

- proxy_dev_score 从 65.309 降至 59.893（下降 5.4 分）
- 所有核心指标（mechanism, strategy, risk_label）均下降
- 唯一提升的 response_reference_token_f1（+1.7pp）不足以弥补其他损失
- 保留标准是 proxy_dev_score >= 66，当前 59.893 远未达标

### 原因分析

1. **Prompt 过长**：新增的 social-pragmatic checklist、mechanism discrimination table、RoT norms、strategy matrix 大幅增加了 system prompt 长度，可能超出 Qwen-turbo 的有效注意力范围。
2. **Risk assessment 格式干扰**：要求 "Main risk: X. Secondary risk: Y." 格式反而降低了风险标签选择的准确性。
3. **机制判别表过于详细**：8 种机制的详细判别规则可能让模型在相似机制间产生混淆。

### 下一步建议

1. **回退到 multi_v1** 作为稳定基线。
2. 如果继续优化，应采用"少改"策略：
   - 只添加 RoT social norms（不加其他新模块）
   - 保持 risk_assessment 原有简洁格式
   - 精简 mechanism discrimination table，只保留最易混淆的 3-4 组对比
3. 或者直接进入 multi_v1.2（candidate reranking），不继续优化 prompt。
