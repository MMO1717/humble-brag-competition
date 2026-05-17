# 不增加过拟合风险的下一步增强规划

本文档目标：在当前 `v6d_generalized` 基础上继续增强系统，但不回到 public dev 专属规则、固定答案模板或 reference 贴合式优化。

当前判断：

- `v6d_response_only`：public dev 分数最高，但过拟合风险高。
- `v6d_generalized`：dev 分数较低，但隐藏集风险更可控，适合作为下一步主线。
- 下一步不应继续追求 public dev proxy 极限，而应提升 hidden Core + Bloom 稳健性。

## 1. 论文给我们的核心启发

### 1.1 Bragging 理解论文

参考：

- `paper_pdfs/01_its_not_bragging_if_you_can_back_it_up.pdf`
- `paper_pdfs/04_bragging_in_social_media.pdf`

核心启发：

bragging 不是简单关键词分类，而是由以下因素共同决定：

- self-presentation：说话人是否在构建正面自我形象。
- social context：平台、关系、角色和目标是否改变回应方式。
- speaker intention：说话人为什么这样说。
- desired feedback：说话人希望别人怎么回应。
- appropriateness：回应是否过度奉承、说教、冷淡或不合语境。

对当前系统的启发：

不要用具体 post 文本规则去判断机制，而应强化一个通用理解链：

```text
post
-> self-presentation signal
-> disguise / mask
-> social context
-> speaker intention
-> desired feedback
-> response risk
-> strategy and response
```

这可以增强模型理解能力，同时不会绑定 dev 样本。

### 1.2 Humblebragging 论文

参考：

- `paper_pdfs/02_exposing_humblebragging_brags_in_disguise.pdf`
- `paper_pdfs/03_humblebragging_distinct_ineffective_strategy.pdf`

核心启发：

humblebragging 的关键不是“说了成就”，而是“用谦虚、抱怨或自嘲包装自我展示”。这类表达通常容易让听众产生反感，因为它同时追求谦逊和炫耀。

对当前系统的启发：

机制判断要继续围绕通用 disguise 类型，而不是实体或话题：

| 抽象线索 | 可能机制 |
|---|---|
| 成就被顺手带出 | `achievement_drop` |
| 表面谦虚但实际高成就 | `faux_modesty` |
| 抱怨中隐藏优势 | `humble_complaint` |
| 显式承认自己在炫耀 | `self_aware_brag` |
| 把优势说得像平常事 | `understated_flex` |
| 稀缺经历、名人、机会、准入门槛 | `scarcity_flex` |
| 和别人比较来凸显自己 | `comparison_superiority` |

这类规则可以写进模型理解层或 judge rubric，但不要写成具体词触发。

### 1.3 Self-Refine / DECRIM / Feedback Control

参考：

- `paper_pdfs/05_self_refine.pdf`
- `paper_pdfs/06_decrim.pdf`
- `paper_pdfs/07_self_correction_as_feedback_control.pdf`

核心启发：

自纠错不是越多越好。多轮 rewrite 可能引入新错误。更稳妥的是：

- 先分解约束。
- 再只检查明确违反约束的部分。
- 只在 hard issue 出现时重写。
- 重写后必须 verify。
- 如果重写变差，应回退原答案。

对当前系统的启发：

当前 multi-agent 不应升级成复杂辩论系统，而应升级成“verify-first 的受控修复系统”：

```text
Generator output
-> Local validator
-> Paper-rubric judge only if needed
-> Constrained rewrite once
-> Verify
-> accept or rollback
```

这能增强稳定性，同时避免每条样本都被 LLM 改坏。

### 1.4 ESConv / ProsocialDialog

参考：

- `paper_pdfs/08_esconv_towards_emotional_support_dialog_systems.pdf`
- `paper_pdfs/09_prosocialdialog.pdf`

核心启发：

高质量回应不是简单附和，而是遵守社会规范：

- 承认对方情绪或意图，但不要盲目赞美。
- 根据关系和平台调整语气。
- 避免道德审判。
- 避免鼓励不合适的自我展示。
- 对高风险内容使用 redirect / neutral observation / boundary。

对当前系统的启发：

可以引入一个通用 Prosocial Response Rubric，而不是 dev-specific 模板：

```text
Does the response:
1. recognize the bragging intent lightly?
2. avoid excessive praise?
3. avoid moralizing?
4. match relationship and platform?
5. match selected response_strategy?
6. stay short and socially natural?
```

这个 rubric 可用于 judge 或离线抽查，不依赖 dev gold。

## 2. 下一步主线：Generalized v2

建议新版本命名：

```text
v6e_generalized
```

目标不是冲 public dev，而是提升隐藏集稳健性。

### 2.1 不该做的事

明确禁止：

- 不恢复 `TOPIC_RULES`。
- 不恢复具体 post/entity 触发规则。
- 不用 `dev_gold.jsonl` 生成任何提交内容。
- 不根据 `reference_response` 写模板。
- 不按 `episode_id` 修 label。
- 不针对 `lollapalooza`、`4.0`、`political art`、`Bobby Lopez` 等 dev 实体写规则。
- 不把 mechanism 修正写成关键词硬覆盖。

允许：

- 使用 `episode_id` 做 deterministic template pool 的稳定选择，但不能让 `episode_id` 决定标签或语义。
- 使用 abstract features，例如 `theme`、`mask`、`context`、`mechanism`、`strategy`。
- 使用官方 label schema 和论文级通用社会规范。

## 3. 可执行增强方向

### 3.1 增强一：Paper-Rubric Social Judge

新增一个不直接看 dev gold 的 judge，用论文抽象原则检查输出。

输入：

```text
input row + generated output row
```

输出：

```json
{
  "hard_issues": [],
  "soft_issues": [],
  "rubric_scores": {
    "context_fit": 0-2,
    "strategy_fit": 0-2,
    "anti_sycophancy": 0-2,
    "anti_preachiness": 0-2,
    "naturalness": 0-2
  }
}
```

hard issue 示例：

- `response_strategy = no_response` 但 `response_text` 很长。
- `avoid_sycophancy` 场景里回复大量夸赞。
- `workplace_channel` 使用过度亲密或玩笑语气。
- `response_strategy` 和 `response_text` 明显不一致。
- `risk_assessment` 没有官方风险关键词。

soft issue 示例：

- 回复略模板化。
- 回复略冷。
- 回复没有轻微承认对方意图。

关键原则：

Judge 只判断通用社会规范，不允许使用 dev gold 或 dev reference。

### 3.2 增强二：Verify-First Conditional Rewriter

参考 Self-Refine / DECRIM / Feedback Control，重写必须满足：

```text
only hard issue -> rewrite
no hard issue -> keep original
rewrite at most once
verify after rewrite
if rewritten output fails validator or judge worse -> rollback
```

不要每条都重写。

建议触发条件：

| 条件 | 是否触发 rewrite |
|---|---|
| format/schema 错误 | 是 |
| risk label 缺失 | 是 |
| response_strategy 与 response_text 明显冲突 | 是 |
| 明显 sycophancy/preachiness/context mismatch | 是 |
| 只是 dev 分数可能更低 | 否 |
| 只是回复不够像 reference | 否 |
| 只是 mechanism 可能不是 dev gold | 否 |

### 3.3 增强三：Response Naturalness Without Topic Overfit

当前 `v6d_generalized` 已经用 deterministic template pool 降低重复。下一步只优化自然度，不恢复 topic 规则。

建议增加模板维度：

```text
strategy + mechanism + context + mask + tone
```

其中 tone 只允许通用类别：

- `warm`
- `neutral`
- `playful`
- `professional`
- `boundary`

不要使用具体话题文本作为模板条件。

建议每种 strategy 至少 5-8 个通用模板，每个模板必须符合：

- 短句。
- 不夸张。
- 不说教。
- 不戳穿“你在炫耀”。
- 不复述过多 post 内容。
- 不出现 dev 特定实体。

示例：

```text
light_acknowledgment:
- "That is worth a small nod without making it a huge thing."
- "Fair enough, that does sound like something you are pleased about."
- "I get why that would feel good to mention."

neutral_observation:
- "That is useful context, though I would keep the focus pretty grounded."
- "There is a real point there, even if it does not need a big reaction."

humor_tease:
- "That is a very specific flex, but I see the angle."
- "I will allow the small flex, lightly."
```

### 3.4 增强四：Mechanism Boundary Rubric，不做硬覆盖

不要恢复 mechanism keyword patch。可以加入一个离线分析或 judge 维度：

```text
Is this a direct achievement, a disguised achievement, a complaint-mask, or a comparison?
```

仅在以下情况下才允许改 mechanism：

- judge 明确给出 high confidence。
- 改动依据是抽象机制边界，不是具体 post 文本。
- 改动后不降低 strategy/risk coherence。

短期建议：先不要在 `v6e_generalized` 改 mechanism。因为现在 `v6d_generalized` mechanism 已经是 0.9556，继续硬调收益小，过拟合风险高。

### 3.5 增强五：构造非 dev 的压力测试集

为了避免只看 public dev，应该做一个小型 synthetic stress set。

来源：

- 根据论文中的 mechanism 定义人工写 5-10 条每类样本。
- 每条改写 2-3 个不同 platform / relationship / goal。
- 不使用 public dev 的实体、话题、reference。

规模：

```text
8 mechanisms * 5 examples = 40
每条 2 个 context 变体 = 80
```

评估方式：

- format 是否通过。
- mechanism 是否符合人工预期。
- strategy 是否符合 context。
- risk 是否覆盖 sycophancy / preachiness / context_insensitivity。
- response 是否自然、不过度模板化。

这个 stress set 比继续榨 public dev 更能反映隐藏集风险。

## 4. v6e_generalized 实施顺序

### Step 1：冻结当前候选

保留：

- `v6d_response_only`
- `v6d_generalized`
- 当前 overfit audit

不要覆盖旧结果。

### Step 2：新增 paper-rubric judge

建议文件：

```text
deliverables/v6d_runnable_package/scripts/judge_social_rubric.py
```

只输出报告，不直接改提交。

输出：

```text
analysis/v6d_generalized_social_rubric_report.md
```

### Step 3：人工或脚本抽查 test 输出

抽查维度：

- 重复模板。
- 过度抽象。
- response_strategy 不匹配。
- 过度奉承。
- 过冷。
- 不看平台/关系。

### Step 4：只优化 response template pool

在不引入具体 post 触发的前提下，增强模板自然度。

保留 deterministic 选择：

```text
theme + mask + context + mechanism + strategy + episode_id
```

但模板内容更自然，不要全部围绕 `the accomplishment / the point`。

### Step 5：复测

必须跑：

```bash
python3 BRAG-Agent-public/scripts/format_checker.py \
  deliverables/v6d_runnable_package/outputs/dev_submission_v6e_generalized.jsonl \
  BRAG-Agent-public/data/dev_input.jsonl

python3 BRAG-Agent-public/scripts/evaluate_dev.py \
  BRAG-Agent-public/data/dev_input.jsonl \
  BRAG-Agent-public/data/dev_gold.jsonl \
  deliverables/v6d_runnable_package/outputs/dev_submission_v6e_generalized.jsonl

python3 BRAG-Agent-public/scripts/format_checker.py \
  deliverables/v6d_runnable_package/outputs/test_submission_v6e_generalized.jsonl \
  BRAG-Agent-public/data/test_input.jsonl
```

额外检查：

```text
dev-specific keyword scan
exact reference response count
test unique responses
most frequent response count
strategy distribution
risk label distribution
manual Bloom-risk sample review
```

## 5. 保留门槛

`v6e_generalized` 只有满足以下条件才保留：

| 指标 | 保留门槛 |
|---|---:|
| dev format errors | 0 |
| test format errors | 0 |
| dev proxy | >= 75.738 |
| test unique responses | >= 150 / 409 |
| test most frequent response count | <= 20 |
| dev exact reference response | 0 / 45 |
| dev-specific keyword scan | 0 high-risk matches |
| mechanism accuracy | 不明显低于 0.9556 |
| strategy score | 不明显低于 0.8333 |
| risk F1 | 不明显低于 0.7481 |

如果 dev proxy 小降但人工 Bloom 风险更低，可以保留为 hidden-test candidate。

如果 dev proxy 上升但出现 dev-specific 规则，不能保留为 generalized 主线。

## 6. 最推荐的下一步

最稳妥的下一步不是改标签、不是改机制、也不是恢复 topic 规则，而是：

```text
新增 paper-rubric judge
+ 人工/脚本抽查 generalized 输出
+ 只优化通用 response template pool 的自然度
```

这条路线的收益：

- 不依赖 public dev reference。
- 不引入具体实体规则。
- 能降低隐藏 Bloom 风险。
- 能改善当前 generalized 的模板化问题。
- 保留当前 format 稳定性。

最终推荐路线：

```text
v6d_generalized
-> paper-rubric judge
-> no-overfit naturalness template improvement
-> v6e_generalized
-> dev/test format + dev proxy + overfit audit + manual Bloom review
```

