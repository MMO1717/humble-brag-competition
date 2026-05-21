# Phase 1.1: LLM Prompt Calibration and Contract Postprocess

## 1. 背景

Phase 1 已经完成了 minimal LLM backend 的工程接入。

当前 LLM full dev 结果：

```text
backend: llm
model: glm4:9b
prompt_version: llm_a_minimal_v1
input rows: 45
format valid: True
fallback_count: 0
parse_failure_count: 0
invalid_label_count: 0
proxy_dev_score: 35.983
mechanism_accuracy: 0.2667
strategy_score: 0.4444
risk_label_f1: 0.0481
response_reference_token_f1: 0.2087
```

对照 heuristic baseline：

```text
proxy_dev_score: 49.223
mechanism_accuracy: 0.2667
strategy_score: 0.6333
risk_label_f1: 0.5785
response_reference_token_f1: 0.1324
```

结论：

- Phase 1 工程链路成功。
- LLM 输出可解析，0 fallback，format checker 通过。
- 但 LLM 的策略选择和风险表达不贴合当前 evaluator。
- 下一步不是回滚 LLM，也不是立刻上 RAG / memory，而是做小范围 prompt calibration 和 postprocess 约束。

## 2. Phase 1.1 目标

Phase 1.1 的目标是保留当前 LLM pipeline，并修正三个主要问题：

1. `response_strategy` 过度塌缩到 `light_acknowledgment`。
2. `risk_assessment` 写得自然但没有命中 evaluator 可识别的风险标签。
3. `response_text` 在 `stay_neutral` / `avoid_sycophancy` 场景中经常过度夸奖。

本阶段目标不是追求最高 dev 分数，而是让 LLM 行为更符合比赛契约，并保持泛化安全。

## 3. 当前问题诊断

### 3.1 Strategy 塌缩

在 full dev 45 条中，LLM 选择分布明显不健康：

```text
light_acknowledgment: 41
humor_tease: 4
```

这说明 minimal prompt 对 `response_strategy` 的指导不足。模型默认倾向于礼貌承认或轻微夸奖，但官方 gold 中策略分布更分散，包括：

```text
light_acknowledgment
neutral_observation
ask_followup
humor_tease
validate
redirect
```

### 3.2 Risk 标签未命中

当前 `risk_label_f1` 只有：

```text
0.0481
```

主要原因是模型输出自然语言风险描述，例如：

```text
Responding with humor or direct acknowledgment may be perceived as validating the bragging.
```

这种表达人类可读，但不稳定命中 evaluator 期待的风险类型。需要让 `risk_assessment` 明确包含风险标签式短语。

### 3.3 过度夸奖

Trace 中多次出现：

```text
I'm impressed
Impressive multitasking
That's quite a feat
```

这些回复在 `avoid_sycophancy` 和 `stay_neutral` 场景下会伤害策略质量。当前 `contract.py` 的 overpraise 过滤还不够。

## 4. 实现范围

本阶段只做小范围校准：

- 新增 prompt version：`llm_b_label_definition_v1`
- 保留 `llm_a_minimal_v1`
- 允许 CLI 指定 prompt version
- 增加 strategy selection rules
- 增加 risk label expression rules
- 增强 anti-sycophancy postprocess
- 增强 trace / RES.md 中 prompt version 记录

不要做：

- 不要接 RAG。
- 不要接 memory。
- 不要引入 `data/Bragging_data.json` 检索。
- 不要加入大量 few-shot examples。
- 不要为了 dev gold 写逐样本规则。
- 不要改官方 `format_checker.py` / `evaluate_dev.py` 评分逻辑。
- 不要删除 `llm_a_minimal_v1` 或 heuristic baseline。

## 5. Prompt v2 设计

新增 prompt：

```text
llm_b_label_definition_v1
```

建议在 `humble_brag/prompts.py` 中新增：

```python
def build_label_definition_prompt_v1(row: dict[str, Any]) -> str:
    ...
```

Prompt v2 相比 v1 增加三类信息：

1. 每个 `bragging_mechanism` 的一句话定义。
2. 每个 `response_strategy` 的一句话定义。
3. 根据 `interaction_goal` / `relationship` / `platform` 的策略选择规则。

### 5.1 Bragging Mechanism 简短定义

建议定义：

```text
achievement_drop: directly mentions an accomplishment, score, status, output, award, or performance.
comparison_superiority: frames the speaker as better than others or contrasts their achievement with others.
faux_modesty: uses modest or self-effacing wording while still highlighting an achievement.
humble_complaint: complains about a burden, inconvenience, or problem caused by success or high ability.
scarcity_flex: highlights rare access, exclusivity, elite opportunity, or limited availability.
self_aware_brag: explicitly signals awareness of bragging, such as "not to brag", "humblebrag", or "flex".
understated_flex: indirectly makes the speaker look impressive without a direct brag cue.
other: use only when none of the above fits.
```

### 5.2 Response Strategy 简短定义

建议定义：

```text
neutral_observation: acknowledge the situation or context without praise, validation, or follow-up.
light_acknowledgment: brief, low-intensity acknowledgment without strong praise.
ask_followup: ask a grounded follow-up question that shifts toward substance.
humor_tease: use light playful teasing only when relationship and platform make it safe.
validate: explicitly affirm the achievement; use sparingly when validation is appropriate.
redirect: move the conversation away from the brag or toward a practical topic.
set_boundary: politely limit engagement when the brag is socially uncomfortable or inappropriate.
no_response: choose silence only when responding would likely be harmful or unnecessary.
```

### 5.3 Strategy Selection Rules

Prompt 中加入短规则，不要写成长篇推理。

建议规则：

```text
Strategy selection rules:
- If interaction_goal is stay_neutral, prefer neutral_observation unless a warmer response is clearly required.
- If interaction_goal is avoid_sycophancy, avoid validate and avoid praise-heavy light_acknowledgment.
- If the relationship is acquaintance or the platform is direct_message, ask_followup can be safer than praise.
- If the relationship is close_friend or online_peer and the tone is playful, humor_tease can be acceptable.
- If the post creates awkwardness or the best response is to move on, use redirect.
- Do not default to light_acknowledgment for every case.
- Do not use validate unless the interaction_goal and relationship clearly support explicit affirmation.
```

### 5.4 Risk Assessment Rules

Prompt 中要求 `risk_assessment` 明确包含 1-3 个风险类型短语。

建议风险短语集合：

```text
misrecognition
context_insensitivity
sycophancy_risk
overvalidation
relationship_mismatch
tone_mismatch
escalation_risk
awkwardness
dismissiveness
```

Prompt 中可写：

```text
In risk_assessment, explicitly name 1-3 likely risk types from this list and briefly explain them:
misrecognition, context_insensitivity, sycophancy_risk, overvalidation, relationship_mismatch, tone_mismatch, escalation_risk, awkwardness, dismissiveness.
```

注意：这不是让模型输出单独字段，仍然输出 `risk_assessment` 字符串。

## 6. Postprocess 增强

修改 `humble_brag/contract.py`。

### 6.1 扩展 overpraise 过滤词

当前过滤词不够，需要覆盖：

```text
impressive
impressed
great
awesome
congrats
congratulations
well done
quite a feat
nice work
proud of you
```

建议只在以下策略或目标下更强过滤：

```text
response_strategy in {"light_acknowledgment", "neutral_observation", "redirect", "set_boundary"}
```

如果实现时能拿到原始输入 `interaction_goal`，则对以下目标也强过滤：

```text
interaction_goal in {"stay_neutral", "avoid_sycophancy"}
```

如果当前 `normalize_output_row` 没有 input context，可以先只按 `response_strategy` 过滤。

### 6.2 防止 neutral_observation 变成夸奖

当 `response_strategy == "neutral_observation"` 时，`response_text` 应避免：

```text
impressive
amazing
great
awesome
congrats
well done
```

可以替换成更中性的表达：

```text
That context helps explain the situation.
That gives useful context without overstating it.
That is a relevant detail for the discussion.
```

### 6.3 可选：risk_assessment 后处理补强

如果 `risk_assessment` 没有任何风险标签式短语，可以根据策略补一个通用风险：

```text
Potential risks include misrecognition and context_insensitivity.
```

如果策略是 `validate` 或 `light_acknowledgment`，可补：

```text
Potential risks include sycophancy_risk and overvalidation.
```

这一步要保持通用，不要按 episode_id 写规则。

## 7. CLI 与 Runner 修改

### 7.1 新增 `--prompt-version`

修改 `main.py` / `humble_brag/runner.py`，支持：

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_a_minimal_v1 --max-items 10
python3 main.py --mode dev --backend llm --prompt-version llm_b_label_definition_v1 --max-items 10
```

默认：

```text
llm_a_minimal_v1
```

这样可以保留 Phase 1 原始结果作为对照。

### 7.2 Trace 中记录 prompt version

每条 trace 必须记录实际使用的 prompt version：

```json
{
  "prompt_version": "llm_b_label_definition_v1"
}
```

### 7.3 RES.md 中记录 prompt version

`RES.md` summary 继续记录：

```text
prompt_version
fallback_count
parse_failure_count
invalid_label_count
proxy_dev_score
strategy_score
risk_label_f1
```

## 8. 验收流程

### 8.1 保证旧版本不坏

```bash
python3 main.py --mode dev --backend heuristic --max-items 3
python3 main.py --mode dev --backend llm --prompt-version llm_a_minimal_v1 --max-items 3
```

### 8.2 跑新 prompt v2 小样本

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_b_label_definition_v1 --max-items 10
```

检查：

- format valid 是否为 True。
- fallback_count 是否仍接近 0。
- parse_failure_count 是否仍接近 0。
- strategy 是否不再大量塌缩到 `light_acknowledgment`。
- risk_assessment 是否出现风险标签短语。
- response_text 是否减少过度夸奖。

### 8.3 跑 full dev

如果 max 10 结果正常，再跑：

```bash
python3 main.py --mode dev --backend llm --prompt-version llm_b_label_definition_v1
```

### 8.4 编译检查

```bash
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py
```

## 9. 验收标准

Phase 1.1 完成标准：

- `heuristic` backend 仍可运行。
- `llm_a_minimal_v1` 仍可运行。
- 新增 `llm_b_label_definition_v1` 并可通过 CLI 选择。
- `llm_b_label_definition_v1` 的 format checker 通过。
- `trace.jsonl` 正确记录 prompt version、raw output、parsed output、normalized output。
- `strategy` 分布不再极端集中在 `light_acknowledgment`。
- `risk_assessment` 明确包含风险标签式短语。
- `response_text` 中明显减少 `impressive` / `impressed` / `great` 等过度夸奖。
- full dev 至少不应出现工程退化，例如 fallback 激增、parse failure 激增、format invalid。

建议目标：

```text
risk_label_f1 明显高于 0.0481
strategy_score 不低于 0.4444
proxy_dev_score 高于 35.983
```

注意：这只是 Phase 1.1 的改进目标，不要求一次超过 heuristic baseline。

## 10. 不要做的事情

- 不要为了 dev gold 写 episode_id 级别规则。
- 不要把 `reference/BRAG-Agent-public/data/dev_gold.jsonl` 用进推理链路。
- 不要把 evaluator 的 gold 答案塞进 prompt。
- 不要在提交模式依赖 dev gold。
- 不要引入 RAG / memory。
- 不要加入大量 few-shot examples。
- 不要删除已有 Phase 1 输出和 trace。
- 不要修改官方评测脚本逻辑。

## 11. 推荐提交信息

```bash
git add main.py humble_brag README.md report.md task.md phase1.md phase1_1.md
git add humble_brag/prompts.py humble_brag/runner.py humble_brag/contract.py
git commit -m "Calibrate LLM prompt and response postprocess"
```

如果 Phase 1 相关新增文件还未提交，也一并纳入：

```bash
git add humble_brag/llm_client.py humble_brag/json_repair.py
```

## 12. 后续方向

Phase 1.1 完成后，根据 trace 再决定是否进入 Phase 2。

建议顺序：

```text
Phase 1: Minimal LLM backend
Phase 1.1: Prompt v2 + risk label + anti-sycophancy postprocess
Phase 1.2: Trace-based error analysis
Phase 2: SkillFlow split, e.g. mechanism -> strategy -> response generation
Phase 3: RAG / memory / few-shot
```

不要跳过 trace analysis 直接上 RAG。当前主要问题还在 prompt 和策略控制层。
