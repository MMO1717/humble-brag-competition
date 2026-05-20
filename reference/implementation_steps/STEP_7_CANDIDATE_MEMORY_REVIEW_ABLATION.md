# Step 7：Candidate Memory Review + Ablation

## 目标

建立从错误分析到 candidate memory，再到本地模型 / 人工评审，再到 active memory 的闭环，并通过 ablation 判断 memory 是否真的有效。

这是整个 memory 系统最关键的一步。

## 实现范围

建议新增：

```text
src/memory/candidate_generator.py
src/memory/memory_judge.py
src/memory/ablation.py

agent_memory/candidate_memory.jsonl
agent_memory/rejected_memory.jsonl
agent_memory/disabled_memory.jsonl
agent_memory/memory_update_logs.jsonl
```

## Candidate Memory 生成条件

| 情况 | 是否生成 |
| --- | --- |
| 普通正确样本 | 不生成 |
| 普通格式错误 | 不生成，交给 checker |
| 单次偶然错误 | 暂不生成，只记录 |
| 同类错误重复出现 >= 2 次 | 生成 |
| 机制标签边界混淆 | 生成 |
| 风险判断失败 | 生成 |
| 策略与回复不一致 | 生成 |
| few-shot 检索误导模型 | 生成 |
| memory 检索误导模型 | 生成 |
| 人工标记为高价值错例 | 生成 |

Candidate Memory schema：

```json
{
  "memory_id": "candidate_humble_complaint_001",
  "type": "label_definition",
  "skill": "mechanism",
  "trigger": "complaint framing plus positive status signal",
  "content": "When a speaker complains about an inconvenience that itself reveals achievement, privilege, or recognition, prefer humble_complaint over achievement_drop.",
  "source_episode_ids": ["dev_012", "dev_021"],
  "possible_overfit_risk": "May over-classify all negative wording as humble_complaint.",
  "status": "candidate"
}
```

## Local LLM Judge 边界

离线评审工作已迁移至本地大模型（Local LLM Judge）。为绝对防止测试集数据泄露或过拟合，本地 Judge 同样需要遵循严格的离线隔离边界：

允许：

- 读取 train/dev 错例总结出的 candidate memory
- 判断 memory 是否泛化
- 判断是否过拟合 dev
- 判断是否与已有 active memory 冲突
- 必要时重写 memory，使其更抽象

禁止：

- 读取 `test_input.jsonl`，或读取任何测试集相关的 debug logs。
- 参与测试集评估推理（Test Inference）的实时生成、分类、rerank、checker、repair 等链路。

Judge 输出：

```json
{
  "memory_id": "candidate_humble_complaint_001",
  "decision": "accept",
  "generality": 4,
  "correctness": 5,
  "overfit_risk": 2,
  "usefulness": 5,
  "conflict_risk": 1,
  "reason": "This captures a general label boundary rather than a single dev answer.",
  "revised_memory": "When complaint framing highlights an inconvenience that also signals recognition, privilege, or achievement, prefer humble_complaint unless no positive status signal is present."
}
```

推荐接受标准：

```text
generality >= 4
correctness >= 4
usefulness >= 3
overfit_risk <= 2
conflict_risk <= 2
不包含具体 dev 答案复述
不包含 reference_response 的直接改写
不绑定单个 episode_id 才成立
```

## Ablation 设计

至少跑以下实验：

| 实验 | 配置 |
| --- | --- |
| no_memory | 不使用 memory |
| label_only | 只使用 label_definition / failure_pattern |
| risk_only | 只使用 risk_avoidance |
| strategy_only | 只使用 context_strategy |
| response_only | 只使用 response_style |
| all_memory | 使用全部 active memory |

每个实验保存：

```text
outputs/<run_id>/RES.md
outputs/<run_id>/dev_eval_report.json
outputs/<run_id>/error_analysis/error_report.md
```

建议汇总表：

| Run | Memory | Score | Mechanism | Strategy | Risk | Response | Format |
| --- | --- | --- | --- | --- | --- | --- | --- |
| no_memory | off | | | | | | |
| label_only | label | | | | | | |
| risk_only | risk | | | | | | |
| strategy_only | strategy | | | | | | |
| response_only | response | | | | | | |
| all_memory | all | | | | | | |

## 通过标准

- candidate memory 能自动生成
- 本地大模型 Judge 或人工 review 能输出 accept/revise/reject
- accept 的 memory 能进入 active memory
- reject 的 memory 能保留在 rejected memory 中
- disabled memory 不参与推理
- ablation 能证明某类 memory 的收益或风险
- 如果 all_memory 分数提升但某类指标明显下降，必须进一步拆解而不是直接保留

## 风险点

- 本地大模型 Judge 把 dev-specific 规则误判为泛化 memory
- Memory 提升 dev score 但损害 hidden test 泛化
- all_memory 看似提升，但来自 response token F1 的表面收益
- ablation 样本太少，结论不稳定

## 完成标志

当 candidate memory 的生成、评审、晋升、禁用、ablation 都能闭环运行，并能证明哪些 memory 类型有收益时，进入 Step 8。
