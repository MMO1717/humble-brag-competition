# BRAG-Agent v6 Next Steps

本文档用于规划接下来 BRAG-Agent v6 比赛备赛与工程开发流程。

## 1. 当前判断

当前项目已经具备早期 Agent 原型、并发调用、LLM-as-Judge 评估和 Prompt 模块化能力。但官方 v6 参赛包已经更新，后续主线应切换到官方数据和官方提交格式。

当前最重要的目标不是继续直接调 Prompt，而是先打通完整官方链路：

```text
dev_input.jsonl -> Agent -> dev_submission.jsonl -> format_checker -> evaluate_dev
```

只有这条链路跑通，后续优化才有稳定的分数反馈。

## 2. 阶段一：适配官方 v6 格式

目标：让当前 Agent 能直接读取官方 JSONL 输入，并输出可提交的 JSONL 文件。

需要完成：

- 将 `bragging_mechanism` 从中文自然语言描述改为官方枚举。
- 增加官方机制标签校验。
- 更新 `system_prompt_sections.py` 中的机制定义和 few-shot 示例。
- 新增官方 runner，例如 `run_official.py`。
- 支持读取：

```text
BRAG-Agent-public/data/dev_input.jsonl
BRAG-Agent-public/data/test_input.jsonl
```

- 输出 JSONL，而不是 JSON 数组。
- 每行只包含官方要求的 7 个字段：

```text
episode_id
bragging_mechanism
speaker_intention
desired_feedback
risk_assessment
response_strategy
response_text
```

阶段产物：

```text
outputs/dev_submission.jsonl
outputs/test_submission.jsonl
```

## 3. 阶段二：建立 Baseline 分数

目标：知道当前系统在官方 dev 集上的真实表现。

执行流程：

```bash
python run_official.py \
  --input BRAG-Agent-public/data/dev_input.jsonl \
  --output outputs/dev_submission.jsonl
```

先做格式检查：

```bash
python BRAG-Agent-public/scripts/format_checker.py \
  outputs/dev_submission.jsonl \
  BRAG-Agent-public/data/dev_input.jsonl
```

再跑官方 dev proxy scorer：

```bash
python BRAG-Agent-public/scripts/evaluate_dev.py \
  BRAG-Agent-public/data/dev_input.jsonl \
  BRAG-Agent-public/data/dev_gold.jsonl \
  outputs/dev_submission.jsonl
```

需要记录的指标：

- `mechanism_accuracy`
- `preferred_strategy_accuracy`
- `acceptable_strategy_rate`
- `strategy_score`
- `risk_label_f1_from_risk_assessment`
- `response_reference_token_f1`
- `proxy_dev_score`

阶段产物：

```text
outputs/dev_score_report.json
```

## 4. 阶段三：Bad Case 分析

目标：找出最影响分数的问题，而不是凭感觉改 Prompt。

重点分析：

- 哪些 `bragging_mechanism` 最容易分类错误。
- `response_strategy` 是否过度集中在 `validate`。
- `risk_assessment` 是否缺少官方风险标签关键词。
- `response_text` 是否与参考回复风格差距过大。
- 是否出现以下 Bloom 风险：

```text
sycophancy
strategy_inconsistency
context_insensitivity
misrecognition
preachiness
over_coldness
```

阶段产物：

```text
analysis/bad_cases.md
```

## 5. 阶段四：Prompt 调优

目标：提升 dev proxy 分数，同时降低隐藏 Bloom 测试风险。

优先优化方向：

- 机制分类：
  - 明确区分 `humble_complaint`、`faux_modesty`、`achievement_drop`、`understated_flex`。
  - 从 `train.jsonl` 中挑选高质量 few-shot。

- 策略选择：
  - 降低 `validate` 滥用。
  - 普通朋友、职场、群聊场景优先考虑 `light_acknowledgment` 或 `neutral_observation`。
  - 高风险语境优先考虑 `redirect`、`set_boundary` 或 `no_response`。

- 风险评估：
  - 在 `risk_assessment` 中显式体现官方风险标签。
  - 特别关注 `sycophancy`、`context_insensitivity`、`misrecognition`。

- 回复风格：
  - 简短自然。
  - 避免过度夸赞。
  - 避免说教。
  - 避免过冷。
  - 保证 `response_text` 与 `response_strategy` 一致。

## 6. 阶段五：正式 Test 生成

当 dev 分数稳定后，再生成正式测试提交文件。

执行：

```bash
python run_official.py \
  --input BRAG-Agent-public/data/test_input.jsonl \
  --output outputs/test_submission.jsonl
```

提交前必须检查：

```bash
python BRAG-Agent-public/scripts/format_checker.py \
  outputs/test_submission.jsonl \
  BRAG-Agent-public/data/test_input.jsonl
```

通过后准备：

```text
test_submission.jsonl
submission_metadata.md
```

## 7. 阶段六：Official <=20B Track 决策

需要尽早决定是否参加官方 <=20B 赛道。

如果继续使用 DashScope/Qwen closed API：

- 可以作为 reference baseline。
- 但不符合官方 <=20B track。

如果要进入官方 <=20B track：

- 必须使用开源或自托管模型。
- 模型总参数量必须 <=20B。
- 任何生成、筛选、重排、编辑 test answers 的模型都必须 <=20B。
- 可以考虑 LoRA、SFT、规则增强或轻量 reranker。

## 8. 推荐下一步

建议立即执行：

```text
1. 修改当前 Agent，使其输出官方 v6 schema。
2. 新增 run_official.py。
3. 跑 dev_input.jsonl。
4. 通过 format_checker.py。
5. 跑 evaluate_dev.py。
6. 得到第一版 baseline 分数。
```

完成这一步后，再根据 dev bad cases 做有针对性的 Prompt 和策略优化。
