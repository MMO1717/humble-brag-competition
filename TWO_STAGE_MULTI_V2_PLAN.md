# BRAG-Agent multi_v2 两阶段架构实现规划

本文档用于指导当前程序从 `multi_v1` 演进到 `multi_v2`。核心思路是采用方案 2：`Understander -> Responder` 两阶段架构，并保留现有 `Rule Validator -> Conditional Rewriter` 的质量兜底能力。

## 1. 当前程序状态

当前主线已经不是纯单 Agent，而是：

```text
输入 JSONL
-> run_multi_agent_official.py
-> MultiAgentBraggingAgent
-> BraggingResponseAgent 生成完整 7 字段 JSON
-> official_validator.py 本地规则校验
-> 如果通过，直接输出
-> 如果不通过，调用 Rewriter 修复一次
-> 输出官方 JSONL
```

当前核心文件：

```text
src/BraggingResponseAgent.py
src/MultiAgentBraggingAgent.py
src/official_validator.py
src/system.py
src/system_prompt_sections.py
run_multi_agent_official.py
```

当前架构的问题：

- `BraggingResponseAgent` 一次性负责理解、策略选择和回复生成，任务负担过重。
- mechanism 识别错误会直接污染后续 strategy 和 response。
- strategy 选择容易只看帖子文本，而没有充分利用 `platform / relationship / agent_role / interaction_goal`。
- Rewriter 目前主要修格式和显性 hard issue，对“理解错了但格式正确”的样本不够敏感。

## 2. multi_v2 目标架构

目标流程：

```text
输入样本
-> Understander Agent
-> 生成理解字段：
   bragging_mechanism
   speaker_intention
   desired_feedback
   risk_assessment
-> Understanding Validator
-> Responder Agent
-> 生成回应字段：
   response_strategy
   response_text
-> 合并官方 7 字段 JSON
-> official_validator.py
-> 必要时 Conditional Rewriter
-> Final Validator
-> 官方 JSONL 输出
```

一句话：

```text
先让模型看懂“这句话如何低调炫耀”，再让模型根据场景决定“应该怎么回”。
```

## 3. 模块职责

### 3.1 Understander Agent

新增建议文件：

```text
src/TwoStageBraggingAgent.py
```

或拆分为：

```text
src/UnderstandingAgent.py
src/ResponseRealizerAgent.py
src/TwoStageBraggingAgent.py
```

为了减少文件复杂度，第一版建议只新增 `src/TwoStageBraggingAgent.py`。

Understander 只输出 4 个字段：

```json
{
  "bragging_mechanism": "understated_flex",
  "speaker_intention": "...",
  "desired_feedback": "...",
  "risk_assessment": "Main risk: misrecognition. Secondary risk: context_insensitivity. ..."
}
```

重点约束：

- `bragging_mechanism` 必须是官方 8 类之一。
- `speaker_intention` 必须解释说话人想展示什么。
- `desired_feedback` 必须解释说话人希望得到什么回应。
- `risk_assessment` 必须包含至少一个官方风险标签关键词。
- 全部字段使用英文。

官方机制枚举：

```text
humble_complaint
faux_modesty
achievement_drop
comparison_superiority
scarcity_flex
understated_flex
self_aware_brag
other
```

官方风险标签：

```text
sycophancy
strategy_inconsistency
context_insensitivity
misrecognition
preachiness
over_coldness
```

### 3.2 Understanding Validator

第一版可以复用 `official_validator.py` 中的部分规则，也可以在 `TwoStageBraggingAgent.py` 内部实现轻量检查。

检查项：

- 4 个理解字段是否齐全。
- `bragging_mechanism` 是否在官方枚举内。
- `risk_assessment` 是否包含官方风险标签。
- 文本是否明显为英文。
- 字段是否过长。

如果理解阶段失败：

- 可以重试 Understander 一次。
- 不要直接进入 Responder。

### 3.3 Responder Agent

Responder 输入：

```text
原始 input:
episode_id
speaker_post
platform
relationship
agent_role
interaction_goal

Understander 输出:
bragging_mechanism
speaker_intention
desired_feedback
risk_assessment
```

Responder 只输出：

```json
{
  "response_strategy": "neutral_observation",
  "response_text": "Fair point that screen reading can affect pace, so that context does matter for interpreting the score."
}
```

重点约束：

- `response_strategy` 必须是官方 8 类之一。
- `response_text` 必须英文、短、自然。
- `response_text` 必须与 `response_strategy` 一致。
- 不要过度奉承，不要说教，不要过冷。

官方策略枚举：

```text
validate
light_acknowledgment
ask_followup
humor_tease
redirect
neutral_observation
set_boundary
no_response
```

### 3.4 Strategy Matrix

Responder 必须显式参考以下策略矩阵：

| 条件 | 推荐策略 |
| --- | --- |
| `avoid_sycophancy` | `neutral_observation` / `redirect` |
| `stay_neutral` | `neutral_observation` |
| `close_friend` + playful context | `humor_tease` / `light_acknowledgment` |
| `academic_forum` | `neutral_observation` / `ask_followup` |
| `be_supportive_without_overpraising` | `light_acknowledgment` / `validate` |
| `deescalate_awkwardness` | `humor_tease` / `redirect` |
| `workplace_channel` + professionalism | `neutral_observation` / `redirect` |
| praise pressure / comparison pressure | `set_boundary` / `redirect` |

注意：

- `validate` 不应在 `avoid_sycophancy` 场景中过度使用。
- `set_boundary` 不应在普通轻松分享中过度使用。
- `humor_tease` 主要适合 close_friend、group_chat、playful context。
- `neutral_observation` 是 academic/workplace/public 场景的稳健默认选择。

## 4. 建议新增输出版本

不要覆盖现有结果。

multi_v2 输出路径：

```text
outputs/dev_submission_multi_v2.jsonl
outputs/dev_score_report_multi_v2.json
outputs/dev_submission_multi_v2.errors.jsonl
```

对比报告：

```text
analysis/single_v3_1_vs_multi_v1_vs_multi_v2.md
```

## 5. Runner 设计

建议新增：

```text
run_two_stage_official.py
```

参数尽量兼容 `run_multi_agent_official.py`：

```text
--input
--output
--limit
--concurrency
--model
```

默认输出：

```text
outputs/dev_submission_multi_v2.jsonl
```

也可以在第一版中直接扩展 `run_multi_agent_official.py` 增加：

```text
--pipeline multi_v1|two_stage
```

为了减少破坏当前主线，推荐第一版新增 `run_two_stage_official.py`，不改现有 runner。

## 6. 实现细节建议

### 6.1 数据类

可以新增：

```python
@dataclass
class UnderstandingOutput:
    bragging_mechanism: str
    speaker_intention: str
    desired_feedback: str
    risk_assessment: str

@dataclass
class ResponsePlanOutput:
    response_strategy: str
    response_text: str
```

最终仍然返回现有：

```python
AgentOutput
```

### 6.2 API 调用次数

正常路径：

```text
Understander: 1 次模型调用
Responder: 1 次模型调用
Validator: 本地函数
```

异常路径：

```text
Understander retry: 最多 1 次
Responder retry: 最多 1 次
Conditional Rewriter: 最多 1 次
```

为了控制成本：

- 第一版每个阶段最多重试 1 次。
- Rewriter 只在 final validator 出现 hard issue 时触发。

### 6.3 回退策略

如果 two-stage pipeline 失败：

```text
优先回退到 BraggingResponseAgent 当前完整生成逻辑
再经过 official_validator.py
必要时再走现有 Rewriter
```

不要因为 two-stage 单条失败导致整个 batch 中断。

## 7. 实验协议

### 7.1 跑 dev

```bash
python run_two_stage_official.py \
  --input BRAG-Agent-public/data/dev_input.jsonl \
  --output outputs/dev_submission_multi_v2.jsonl \
  --concurrency 3
```

### 7.2 格式检查

```bash
python BRAG-Agent-public/scripts/format_checker.py \
  outputs/dev_submission_multi_v2.jsonl \
  BRAG-Agent-public/data/dev_input.jsonl
```

### 7.3 dev 评估

```bash
python BRAG-Agent-public/scripts/evaluate_dev.py \
  BRAG-Agent-public/data/dev_input.jsonl \
  BRAG-Agent-public/data/dev_gold.jsonl \
  outputs/dev_submission_multi_v2.jsonl
```

### 7.4 对比报告

新增：

```text
analysis/single_v3_1_vs_multi_v1_vs_multi_v2.md
```

必须包含：

- `single_v3_1` 指标
- `multi_v1` 指标
- `multi_v2` 指标
- format checker 结果
- rewrite 触发率
- two-stage 失败/回退次数
- mechanism bad cases
- strategy bad cases
- Bloom 风险人工抽查结论
- 最终推荐提交版本

## 8. 验收标准

最低验收：

```text
dev 45 条全部成功
format_checker 0 errors
outputs/dev_submission_multi_v2.jsonl 存在
analysis/single_v3_1_vs_multi_v1_vs_multi_v2.md 存在
不破坏 run_multi_agent_official.py 和 multi_v1 输出能力
```

理想目标：

```text
multi_v2 proxy_dev_score > multi_v1
mechanism_accuracy >= multi_v1
strategy_score >= multi_v1 - 0.02
risk_label_f1 >= multi_v1
response_reference_token_f1 不明显下降
Bloom 风险人工抽查不高于 multi_v1
```

如果 `multi_v2` dev proxy 略低，但 Bloom 风险明显更稳，需要保留为候选提交方案，因为官方隐藏 Bloom 占 40%。

## 9. 代码 Agent 执行 Prompt

下面这段可以直接发给代码 Agent。

```text
你现在负责把 BRAG-Agent 当前 multi_v1 系统升级为 multi_v2 的 two-stage pipeline。请先阅读项目根目录的 TWO_STAGE_MULTI_V2_PLAN.md、FUTURE_IMPROVEMENT_PLAN.md、src/BraggingResponseAgent.py、src/MultiAgentBraggingAgent.py、src/official_validator.py、run_multi_agent_official.py。

工作目录：
/Users/mm/Desktop/Bragging_acl2025-main

目标：
实现 Understander -> Responder 两阶段架构，并保留现有 Rule Validator + Conditional Rewriter 兜底能力。不要破坏当前 multi_v1。

硬性要求：
1. 不删除任何文件。
2. 不修改 .env 或任何密钥。
3. 不覆盖 outputs/dev_submission_multi_v1.jsonl。
4. 不破坏 run_multi_agent_official.py 当前能力。
5. 新增文件优先，必要修改要保持向后兼容。
6. 最终输出必须通过官方 format_checker.py。

建议实现：
1. 新增 src/TwoStageBraggingAgent.py。
2. 在其中实现：
   - UnderstandingOutput dataclass
   - ResponsePlanOutput dataclass
   - TwoStageBraggingAgent class
   - arun(inp: AgentInput) -> tuple[AgentOutput, dict]
3. Understander Agent 只生成：
   - bragging_mechanism
   - speaker_intention
   - desired_feedback
   - risk_assessment
4. Responder Agent 只生成：
   - response_strategy
   - response_text
5. 合并两个阶段结果为 AgentOutput。
6. 使用 official_validator.validate_official_row 做最终校验。
7. 如果最终校验出现 hard issue，可复用 MultiAgentBraggingAgent 的 rewriter 思路，或先回退到现有 BraggingResponseAgent 生成结果。
8. 新增 run_two_stage_official.py，参数兼容 run_multi_agent_official.py：
   --input
   --output
   --limit
   --concurrency
   --model

输出文件：
outputs/dev_submission_multi_v2.jsonl
outputs/dev_submission_multi_v2.errors.jsonl
outputs/dev_score_report_multi_v2.json
analysis/single_v3_1_vs_multi_v1_vs_multi_v2.md

实验步骤：
1. 跑 dev 45 条：
   python run_two_stage_official.py \
     --input BRAG-Agent-public/data/dev_input.jsonl \
     --output outputs/dev_submission_multi_v2.jsonl \
     --concurrency 3

2. 跑 format checker：
   python BRAG-Agent-public/scripts/format_checker.py \
     outputs/dev_submission_multi_v2.jsonl \
     BRAG-Agent-public/data/dev_input.jsonl

3. 跑 evaluate_dev：
   python BRAG-Agent-public/scripts/evaluate_dev.py \
     BRAG-Agent-public/data/dev_input.jsonl \
     BRAG-Agent-public/data/dev_gold.jsonl \
     outputs/dev_submission_multi_v2.jsonl

4. 生成对比报告：
   analysis/single_v3_1_vs_multi_v1_vs_multi_v2.md

对比报告必须说明：
- 新增/修改了哪些文件
- dev 是否 45/45 成功
- format_checker 是否 0 errors
- evaluate_dev 完整指标
- multi_v2 相比 multi_v1 和 single_v3_1 哪些指标提升/下降
- two-stage 是否减少了 mechanism/strategy 错误
- rewrite 或 fallback 触发了多少次
- 是否推荐 multi_v2 作为最终提交方案

注意：
如果 two-stage 效果不如 multi_v1，不要强行调到不可解释。保留结果，写清失败原因。
```

