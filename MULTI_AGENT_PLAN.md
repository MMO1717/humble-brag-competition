# BRAG-Agent v6 Multi-Agent Upgrade Plan

本文档规划如何在当前 BRAG-Agent v6 单模型 Prompt baseline 之上，逐步尝试多 Agent 架构。目标不是直接复用历史 `phase2/phase2_5` 的逻辑题多智能体系统，而是吸收其中的 Generator-Critic-Curator 思想，改造成适合“低调炫耀社会化回应生成”的轻量多 Agent 流水线。

## 1. 当前状态

当前官方 v6 提交流水线是单 Agent 架构：

```text
Input episode
  -> BraggingResponseAgent
  -> Qwen/DashScope chat completion
  -> JSON extraction
  -> enum validation
  -> JSONL submission
  -> format_checker / evaluate_dev
```

当前 v1 dev baseline：

```text
proxy_dev_score: 44.628
mechanism_accuracy: 0.5778
strategy_score: 0.5667
preferred_strategy_accuracy: 0.4444
acceptable_strategy_rate: 0.6889
risk_label_f1: 0.0444
response_reference_token_f1: 0.0048
format_checker: 0 errors
```

主要问题：

- `risk_assessment` 没有显式包含官方风险标签，导致 `risk_label_f1` 极低。
- 当前输出偏中文，而官方 dev gold/reference 是英文，导致 `response_reference_token_f1` 极低。
- `faux_modesty`、`scarcity_flex` 等 mechanism 容易混淆。
- 当前系统没有独立的 Critic/Rewriter 来检查 strategy-response 一致性和 Bloom 风险。

## 2. 历史多 Agent 资产

仓库中已有历史多 Agent 探索：

```text
phase2/
  agents.py
  mas_controller.py
  curator.py

phase2_5/
  agents.py
  mas_controller.py
  curator.py
  evaluator.py
  eeg_sensor.py
```

历史架构包含：

- Alpha: Proposer
- Beta: Challenger
- Gamma: Curator
- 多轮辩论
- Curator 干预
- Lazy agreement 检测
- Node Dropout
- Emotional FSM

这些机制适合逻辑题/KKS 推理纠偏，但不应原样迁移到 BRAG-Agent v6。当前任务更需要：

- 机制分类准确
- 风险标签覆盖
- 策略选择合理
- 回复短、自然、英文、不过度吹捧
- 输出严格符合官方 JSONL schema

因此本轮建议采用轻量多 Agent，而不是完整辩论式 MAS。

## 3. 总体目标

多 Agent 改造的目标是验证：

```text
single-generator + conditional critic + constrained rewriter
```

是否能比当前单 Agent baseline 提升：

- `risk_label_f1_from_risk_assessment`
- `mechanism_accuracy`
- `strategy_score`
- `response_reference_token_f1`
- hidden Bloom robustness 的潜在表现

同时必须保持：

- `format_checker` 0 errors
- JSONL 输出稳定
- 不显著增加失败率
- 不破坏当前单 Agent baseline 文件

## 4. 推荐架构

### 4.1 Pipeline

```text
Official input row
  -> Generator Agent
      生成官方 7 字段 JSON 初稿
  -> Rule Validator
      执行硬规则和轻量启发式检查
  -> Conditional Critic Agent
      仅在必要时分析初稿问题
  -> Constrained Rewriter Agent
      按 Critic 反馈修正 JSON
  -> Final Validator
      硬校验 schema/enums/format
  -> JSONL output
```

### 4.2 Agent 职责

#### Generator Agent

职责：

- 读取 `speaker_post`、`platform`、`relationship`、`agent_role`、`interaction_goal`。
- 生成官方 7 字段。
- 输出英文。
- 初步判断 mechanism、strategy、risk、response。

实现建议：

- 复用当前 `BraggingResponseAgent`。
- 后续可命名为 `GeneratorAgent`，但第一版不需要大重构。

#### Rule Validator

职责：

- 不调用模型。
- 快速发现明确问题。

检查项：

- 必须包含 7 字段。
- 不能有 extra fields。
- `bragging_mechanism` 必须在官方 8 类中。
- `response_strategy` 必须在官方 8 类中。
- `risk_assessment` 必须包含至少一个官方风险标签原词。
- `response_text` 应为英文。
- `response_text` 不超过官方 word limit。
- `no_response` 的回复必须为空或极短。
- `light_acknowledgment` / `set_boundary` 不应出现明显 overpraise。
- `response_strategy` 与 `response_text` 不能明显冲突。

官方风险标签：

```text
sycophancy
strategy_inconsistency
context_insensitivity
misrecognition
preachiness
over_coldness
```

#### Critic Agent

职责：

- 只在 Rule Validator 发现问题时调用。
- 不重新生成完整答案。
- 输出诊断 JSON。

建议输出格式：

```json
{
  "needs_revision": true,
  "issues": [
    {
      "type": "risk_label_missing",
      "explanation": "risk_assessment does not mention any official risk label.",
      "suggested_fix": "Add misrecognition or context_insensitivity explicitly."
    }
  ],
  "recommended_mechanism": "faux_modesty",
  "recommended_strategy": "light_acknowledgment",
  "rewrite_instructions": "Keep the response brief and English. Avoid overpraise."
}
```

Critic 重点检查：

- mechanism 是否可能混淆。
- risk label 是否缺失。
- strategy 是否不符合关系/平台/目标。
- response 是否过度吹捧、太冷、说教、与策略不一致。
- response 是否为英文。

#### Rewriter Agent

职责：

- 根据原输入、Generator 初稿、Critic 反馈，修正 JSON。
- 只输出最终官方 7 字段 JSON。
- 不输出解释、analysis、reasoning。

约束：

- 尽量保留 Generator 正确部分。
- 只修必要字段。
- 优先保证 format_checker 通过。

## 5. 分阶段实验路线

### Stage A: 单 Agent v2 先修明显问题

在多 Agent 前，建议先完成单 Agent v2：

- 全部输出改英文。
- `risk_assessment` 显式包含官方风险标签。
- 强化 mechanism 定义和 few-shot。

原因：

- 当前 v1 的最大问题无需多 Agent 即可修复。
- 多 Agent 应该和强单 Agent baseline 对比，而不是和明显未对齐的 v1 对比。

产物：

```text
outputs/dev_submission_v2.jsonl
outputs/dev_score_report_v2.json
analysis/dev_bad_cases_v2.md
analysis/dev_v1_v2_comparison.md
```

### Stage B: Rule Validator + Postprocess

先不加模型 Critic，只加规则层。

目标：

- 确保 risk label 不缺失。
- 修复明显中英文问题。
- 捕获 strategy-response mismatch。

产物：

```text
src/official_validator.py
```

建议函数：

```python
validate_official_row(row: dict) -> list[dict]
has_risk_label(text: str) -> bool
looks_english(text: str) -> bool
detect_strategy_response_mismatch(row: dict) -> list[str]
```

### Stage C: Conditional Critic

只有当 Rule Validator 发现软问题时，才调用 Critic。

触发条件：

- 缺少 risk label。
- response 非英文。
- mechanism 为 `other` 且文本明显可分类。
- strategy-response 可能不一致。
- response_text 出现 overpraise。
- `validate` 用于高风险/弱关系场景。

目标：

- 降低额外 token 成本。
- 避免多 Agent 过度干预正确样本。

产物：

```text
src/MultiAgentBraggingAgent.py
```

### Stage D: Rewriter

Critic 发现问题后，调用 Rewriter 修正。

第一版只允许一次 revision：

```text
Generator -> Validator -> Critic -> Rewriter -> Final Validator
```

不要做多轮辩论，避免成本、延迟和不稳定。

### Stage E: A/B Evaluation

同一 dev set 上比较：

```text
v2_single_agent
v3_multi_agent
```

必须比较：

- proxy_dev_score
- mechanism_accuracy
- strategy_score
- risk_label_f1
- response_reference_token_f1
- format error count
- API error count
- average latency
- estimated token cost
- Critic trigger rate
- Rewriter trigger rate

产物：

```text
analysis/multi_agent_ablation.md
```

## 6. 文件设计建议

建议新增文件：

```text
src/official_validator.py
src/MultiAgentBraggingAgent.py
run_multi_agent_official.py
analysis/multi_agent_ablation.md
```

不要直接修改：

```text
BRAG-Agent-public/
```

尽量少改：

```text
src/BraggingResponseAgent.py
```

第一版多 Agent 可以组合现有 `BraggingResponseAgent`，而不是重写它。

## 7. 官方赛道合规风险

如果目标是 official <=20B track：

- Generator、Critic、Rewriter 任何读输入、生成候选、筛选、编辑输出的模型都必须 <=20B。
- closed API 不 eligible。
- 多 Agent 中不能混入 >20B 或 closed model 来筛选/改写 test answers。

当前如果继续使用 DashScope/Qwen API：

- 可以作为 reference baseline。
- 不应宣称 eligible official <=20B submission。

## 8. 成功标准

多 Agent v3 至少需要满足：

```text
format_checker errors = 0
dev success count = 45/45
risk_label_f1 > v2
strategy_score >= v2 - 0.02
mechanism_accuracy >= v2 - 0.02
proxy_dev_score > v2
```

如果多 Agent 提升很小或下降，应回退到单 Agent v2。

## 9. 风险与控制

### 风险 1: 多 Agent 自信改错

控制：

- Critic 只在触发条件下运行。
- Rewriter 只修必要字段。
- 保留原始 Generator 输出用于分析。

### 风险 2: 成本和延迟上升

控制：

- Conditional trigger。
- 最多一次 Critic + 一次 Rewriter。
- 记录 trigger rate。

### 风险 3: 输出变得冗长

控制：

- Rewriter prompt 强制短回复。
- Final Validator 检查 word limit。

### 风险 4: dev proxy 过拟合

控制：

- 不只追 token F1。
- 同时人工抽查 Bloom 风险。
- 保留 v2/v3 对比样本。

## 10. 推荐下一步

给执行 Agent 的下一步应是：

```text
先完成单 Agent v2 Prompt 对齐，
再基于 v2 新增 Rule Validator，
最后尝试 Conditional Critic + Rewriter。
```

不要直接从 v1 跳到复杂多轮 MAS。

第一条执行任务建议：

```text
实现 src/official_validator.py，并在 run_official.py 或新的 run_multi_agent_official.py 中以 dry-run 方式统计 v2/v1 输出中的触发问题，不调用额外模型。
```

第二条执行任务建议：

```text
实现 MultiAgentBraggingAgent 的 Generator -> Validator -> Critic -> Rewriter 单轮链路，并在 dev set 上与单 Agent v2 做 A/B 对比。
```
