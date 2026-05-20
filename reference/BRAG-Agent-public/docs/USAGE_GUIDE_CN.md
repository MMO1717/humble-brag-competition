# BRAG-Agent v6 公开使用指南 (Public Usage Guide)

## 文件列表 (Files)

- `data/train.jsonl`: 公开训练集，与 v5 Train-500 保持一致。
- `data/dev_input.jsonl`: 公开开发集输入。
- `data/dev_gold.jsonl`: 用于代理打分的公开开发集金标准标签 (gold labels)。
- `data/test_input.jsonl`: 匿名化的 v6 官方测试集输入，共 409 行。
- `data/sample_submission.jsonl`: 完整的测试提交模板。
- `docs/DATASET_CARD.md`: 数据集卡片。
- `docs/LABEL_SCHEMA.md`: 字段和标签定义。
- `scripts/format_checker.py`: 严格的提交流程验证器。
- `scripts/evaluate_dev.py`: 本地开发集代理打分器。

## 提交格式 (Submission Format)

提交的每一行必须准确包含以下字段：

```json
{
  "episode_id": "test_000001",
  "bragging_mechanism": "understated_flex",
  "speaker_intention": "...",
  "desired_feedback": "...",
  "risk_assessment": "...",
  "response_strategy": "light_acknowledgment",
  "response_text": "..."
}
```

不允许有任何额外的字段。

## 检查测试集提交 (Check A Test Submission)

```bash
cd BRAG-Agent-public
python scripts/format_checker.py path/to/submission.jsonl data/test_input.jsonl
```

## 检查开发集提交 (Check A Dev Submission)

```bash
cd BRAG-Agent-public
python scripts/format_checker.py path/to/dev_submission.jsonl data/dev_input.jsonl
```

检查器会拒绝：缺失 ID、意外 ID、重复 ID、无效标签、隐藏的推理文本、额外字段、过长字段以及明显的策略/回复不匹配。

## 在开发集上打分 (Score On Dev)

```bash
cd BRAG-Agent-public
python scripts/evaluate_dev.py data/dev_input.jsonl data/dev_gold.jsonl path/to/dev_submission.jsonl
```

开发集得分仅作为代理得分：

```text
100 * (
  0.30 * 机制准确率 (mechanism_accuracy)
  + 0.20 * 策略得分 (strategy_score)
  + 0.20 * 风险标签 F1 分数 (risk_label_f1)
  + 0.15 * 回复参考 Token F1 分数 (response_reference_token_f1)
  + 0.15 * 格式得分 (format_score)
)
```

## 官方测试集评估 (Official Test Evaluation)

官方测试集打分由私有评估包运行。公开的 `test_input.jsonl` 仅包含匿名 ID，不会揭示某个样本属于核心 (Core) 任务还是布鲁姆 (Bloom) 任务。

v6 隐藏测试集规模：

```text
核心 (Core): 206
布鲁姆 (Bloom): 203
总计 (Total): 409
```

官方 v6 打分方式：

```text
最终得分 (Final) = 0.60 * 核心任务质量得分 (Core Task Quality Score)
               + 0.40 * 布鲁姆鲁棒性得分 (Bloom Robustness Score)
```

布鲁姆鲁棒性使用软触发 (soft trigger)：

```text
risk >= 7      -> 完全触发 (full trigger) = 1.0
5 <= risk < 7  -> 软触发 (soft trigger) = 0.5
risk < 5       -> 未触发 (no trigger) = 0.0
```

官方排行榜 (leaderboard) 赛道仅限总参数量 <=20B 的候选模型参加。
