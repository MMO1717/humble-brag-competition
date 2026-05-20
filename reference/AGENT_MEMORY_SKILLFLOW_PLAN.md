# Agent Memory + Skills + SkillFlow 架构规划

## 一、总体思路

本项目后续采用 Agent Memory + Skills + SkillFlow 的工程增强架构，而不是优先进行 LoRA 微调。

核心目标是把 BRAG-Agent 任务拆成多个可控模块，让模型不是一次性完成全部生成，而是按照固定流程逐步完成：

```text
语境理解 -> 机制判断 -> 意图理解 -> 风险判断 -> 策略选择 -> 回复生成 -> 校验修复
```

同时，引入 Agent Memory 机制，将训练集、错例分析和策略优化中沉淀出的经验保存下来，供后续样本动态检索使用。

整体架构如下：

```text
Input Sample
  ↓
Memory Retriever
  ↓
SkillFlow Controller
  ↓
Skills
  ↓
Checker & Repair
  ↓
Output JSONL
  ↓
Debug Log
  ↓
Error Analysis
  ↓
Candidate Memory
  ↓
Local LLM Judge / Human Review
  ↓
Active Memory
```

需要特别明确的是：离线评审 candidate memory 是否值得进入 active memory 同样完全由本地大模型（Local LLM Judge）完成，无需调用任何外部大模型 API。最终提交阶段只使用本地合规模型、规则、SkillFlow、few-shot 和已经固化的 active memory。

更严格地说，本地模型 Judge 只能处理 train/dev 阶段产生的 candidate memory，不能读取 `test_input.jsonl`、test debug log、test 中间输出或 test 候选回复。整个流程均在本地环境离线闭环，不涉及任何外部 API 的数据传输。正式 test 前需要冻结 active memory、prompt、SkillFlow、few-shot index 和 decoding settings，整个提交链路完全离线。

## 二、Skills 模块设计

### 1. Context Understanding Skill

负责理解输入样本的社交语境。

输入字段：

- `speaker_post`
- `platform`
- `relationship`
- `agent_role`
- `interaction_goal`

输出中间信息：

```json
{
  "platform_context": "当前平台语境",
  "relationship_closeness": "关系亲密度",
  "interaction_goal": "互动目标",
  "social_risk_level": "低 / 中 / 高",
  "tone_hint": "建议语气"
}
```

作用是先判断这是职场、朋友、公开平台还是私聊场景，避免后续回复出现语境不敏感的问题。

### 2. Bragging Mechanism Skill

负责判断低调炫耀机制。

输出：

```json
{
  "bragging_mechanism": "humble_complaint / faux_modesty / achievement_drop / ...",
  "reason": "判断依据"
}
```

该 Skill 会调用：

- Label Definition Memory
- Failure Pattern Memory
- Few-shot examples

主要解决：

- `humble_complaint` 和 `achievement_drop` 混淆
- `faux_modesty` 和 `understated_flex` 混淆
- `comparison_superiority` 和 `achievement_drop` 混淆

### 3. Speaker Intention Skill

负责判断说话人的真实意图。

输出：

```json
{
  "speaker_intention": "说话人希望展示成就、寻求认可、维持谦虚形象等"
}
```

作用是避免只看字面意思，而忽略低调炫耀背后的潜台词。

### 4. Desired Feedback Skill

负责判断说话人希望得到什么反馈。

输出：

```json
{
  "desired_feedback": "希望得到轻度认可、祝贺、追问、幽默接梗或中性回应"
}
```

这个模块会直接影响最终回复是否自然。

### 5. Risk Assessment Skill

负责判断回应风险。

重点识别：

- `sycophancy`：过度吹捧
- `preachiness`：说教
- `over_coldness`：过冷
- `context_insensitivity`：语境不敏感
- `misrecognition`：误读
- `strategy_inconsistency`：策略不一致

输出：

```json
{
  "risk_assessment": "需要避免过度吹捧，同时保持轻度认可",
  "risk_tags": ["sycophancy", "context_insensitivity"],
  "avoid": ["夸张赞美", "讽刺", "说教"]
}
```

### 6. Response Strategy Skill

负责选择回应策略。

输出标签必须从官方标签中选择：

- `validate`
- `light_acknowledgment`
- `ask_followup`
- `humor_tease`
- `redirect`
- `neutral_observation`
- `set_boundary`
- `no_response`

输出：

```json
{
  "response_strategy": "light_acknowledgment",
  "strategy_reason": "职场语境下应轻度认可，不宜过度吹捧"
}
```

### 7. Response Generation Skill

负责生成最终英文回复。

要求：

1. 回复自然
2. 以 1-2 句为主
3. 不过度吹捧
4. 不说教
5. 不暴露分析过程
6. 与 `response_strategy` 一致

输出：

```json
{
  "response_text": "Sounds like a hectic trip, but congratulations on the recognition."
}
```

### 8. Checker & Repair Skill

负责最终检查和修复。

检查内容：

1. 是否包含 exactly 7 个字段
2. `episode_id` 是否正确
3. `bragging_mechanism` 是否合法
4. `response_strategy` 是否合法
5. `response_text` 是否与 strategy 一致
6. 是否存在过度吹捧、过冷、说教
7. 是否有多余字段
8. 是否有 hidden reasoning

修复流程：

```text
错误输出
  ↓
定位错误
  ↓
只修复错误字段
  ↓
重新检查
  ↓
输出最终 JSON
```

## 三、SkillFlow 执行流程

推荐 SkillFlow 如下：

1. 读取输入样本
2. 检索相关 memory 和 few-shot examples
3. 执行 Context Understanding Skill
4. 执行 Bragging Mechanism Skill
5. 执行 Speaker Intention Skill
6. 执行 Desired Feedback Skill
7. 执行 Risk Assessment Skill
8. 执行 Response Strategy Skill
9. 执行 Response Generation Skill
10. 执行 Checker & Repair Skill
11. 输出最终 JSONL
12. 记录 Debug Log
13. 执行错误分析与 candidate memory 生成
14. 使用外部 API 模型或人工评审 candidate memory
15. 合格 memory 进入 active memory

核心逻辑是：

```text
Memory 提供经验
Skills 执行子任务
SkillFlow 控制顺序
Checker 保证输出稳定
Debug Log 支持后续优化
```

## 四、Agent Memory 设计

Agent Memory 不直接等于聊天历史，而是一个面向该比赛任务的经验库。

建议分为以下几类：

| Memory 类型 | 作用 |
| --- | --- |
| Label Definition Memory | 保存机制标签定义和边界 |
| Context Strategy Memory | 保存不同平台、关系下的策略规则 |
| Risk Avoidance Memory | 保存风险规避规则 |
| Response Style Memory | 保存回复风格要求 |
| Failure Pattern Memory | 保存错例中总结出的失败模式 |
| Retrieval Policy Memory | 保存 few-shot 检索策略 |

## 五、Memory 生命周期设计

每条 memory 应该经历以下状态：

```text
candidate -> judged -> ablation_validated -> active / rejected / disabled / archived
```

### 1. Candidate Memory

Candidate Memory 由错误分析模块生成，尚未正式使用。

示例：

```json
{
  "memory_id": "candidate_humble_complaint_001",
  "type": "label_definition",
  "trigger": "complaint framing plus positive status signal",
  "content": "When a speaker complains about an inconvenience that itself reveals achievement, privilege, or recognition, prefer humble_complaint over achievement_drop.",
  "source_episode_ids": ["dev_012", "dev_021"],
  "possible_overfit_risk": "May over-classify all negative wording as humble_complaint.",
  "status": "candidate"
}
```

### 2. Local LLM Judge

判断 memory 是否保留时，接入本地大模型（Local LLM Judge）作为评审器。

这个本地模型评审器只用于离线 memory 选择，不进入最终提交模型链路的实时逻辑（虽然和推理模型共享相同的本地客户端，但在 test-time 的推理链路中绝对不会调用该评审器）。也就是说：

- 使用本地大模型判断 candidate memory 是否泛化、是否过拟合、是否冲突。
- 本地模型 Judge 只能处理 train/dev 产生的 candidate memory。
- 绝不在最终 test submission 生成时调用 Judge 评审逻辑。
- 评审器的输出必须固化为静态 active memory 后，才可以被本地提交推理链路检索读取。

评审维度：

| 维度 | 判断内容 |
| --- | --- |
| 泛化性 | 是否适用于一类样本，而不是只针对单个 dev 样本 |
| 正确性 | 规则是否符合任务定义 |
| 过拟合风险 | 是否在背 dev 答案 |
| 冲突风险 | 是否与已有 memory 冲突 |
| 实用性 | 是否能改善机制判断、风险判断或策略选择 |
| 安全性 | 是否会导致回复过冷、过保守或模板化 |

本地模型 Judge 输出：

```json
{
  "memory_id": "candidate_humble_complaint_001",
  "decision": "accept / revise / reject",
  "score": {
    "generality": 4,
    "correctness": 5,
    "overfit_risk": 2,
    "usefulness": 5,
    "conflict_risk": 1
  },
  "reason": "This memory captures a general distinction between humble complaint and achievement drop.",
  "revised_content": "When complaint framing highlights an inconvenience that also signals recognition, privilege, or achievement, prefer humble_complaint, unless the negative experience has no positive status signal."
}
```

推荐接受标准：

```text
accept 条件：
- 本地模型 Judge 输出 accept，或 revise 后再次 accept
- generality >= 4
- correctness >= 4
- usefulness >= 3
- overfit_risk <= 2
- conflict_risk <= 2
- 不和已有 active memory 冲突
- dev ablation 不导致核心指标明显下降
- 不增加 sycophancy / preachiness / over_coldness 等 Bloom 风险
- 不包含具体 dev 答案复述
- 不包含 reference_response 的直接改写
- 不绑定单个 episode_id 才成立
```

因此，本地模型 Judge 不是最终准入门槛。Candidate Memory 被本地模型 Judge 接受后，还需要临时加入实验分支，运行 dev ablation 对比。只有在关键指标没有明显下降、风险行为没有增加时，才可以进入 active memory。

### 3. Active Memory

通过评审后进入正式 memory 库。

示例：

```json
{
  "memory_id": "label_humble_complaint_001",
  "type": "label_definition",
  "content": "When complaint framing highlights an inconvenience that also signals recognition, privilege, or achievement, prefer humble_complaint, unless the negative experience has no positive status signal.",
  "status": "active",
  "approved_by": "external_api_judge",
  "version": 1
}
```

### 4. Disabled / Archived Memory

如果加入后效果下降，可以禁用或归档。

示例：

```json
{
  "memory_id": "label_humble_complaint_001",
  "status": "disabled",
  "disabled_reason": "Caused over-classification of negative posts as humble_complaint."
}
```

## 六、Candidate Memory 触发机制

不是每个样本都生成 memory。每个样本都会生成 debug log，但只有有价值的错误才生成 candidate memory。

| 情况 | 是否生成 candidate memory |
| --- | --- |
| 普通正确样本 | 不生成 |
| 普通格式错误 | 不生成，交给 checker 修复 |
| 单次偶然错误 | 暂不生成，只记录 |
| 同类错误重复出现 >= 2 次 | 生成 |
| 机制标签边界混淆 | 生成 |
| 风险判断失败 | 生成 |
| 策略与回复不一致 | 生成 |
| few-shot 检索误导模型 | 生成 |
| 外部 API 模型认为有泛化价值 | 生成 |
| 人工标记为高价值错例 | 生成 |

## 七、Memory 更新流程

完整流程如下：

```text
运行 dev 样本
  ↓
生成模型输出
  ↓
记录 Debug Log
  ↓
对比 gold answer 或使用评估器评分
  ↓
抽取高错误样本
  ↓
错误分析模块总结失败原因
  ↓
触发 Candidate Memory Generator
  ↓
生成 candidate memory
  ↓
本地模型 Judge / Human Review 评审
  ↓
accept -> 临时加入实验 memory
revise -> 修改后再评审
reject -> 丢弃
  ↓
Dev Ablation Validation
  ↓
重新运行 dev
  ↓
对比 before / after
  ↓
进入 active、禁用或回滚 memory
```

## 八、本地模型评审机制

本地评审模型主要负责：

1. 判断 candidate memory 是否值得保留
2. 判断是否有 dev 过拟合风险
3. 判断是否与已有 memory 冲突
4. 必要时重写 memory，使其更抽象、更泛化
5. 给出 `accept / revise / reject` 决策

API Judge Prompt 可以设计为：

```text
You are a memory quality judge for a BRAG-Agent system.
Your task is to evaluate whether a candidate memory should be added to the active memory bank.

Important constraint:
The local LLM judge is used only for offline memory selection.
It must not participate in final test-time inference, response generation, reranking, repair, or submission generation.
It must only review candidate memories produced from train/dev analysis.
It must not read test_input.jsonl, test debug logs, test intermediate outputs, test candidate replies, or any test generation results.

Evaluate the candidate memory based on:
1. Generality: Is it reusable across multiple cases?
2. Correctness: Is it consistent with the label schema and task goal?
3. Overfit risk: Does it look like it memorizes a dev example?
4. Usefulness: Can it improve mechanism classification, risk assessment, strategy selection, or response generation?
5. Conflict risk: Does it conflict with existing active memories?

Return JSON only:
{
  "decision": "accept | revise | reject",
  "generality": 1-5,
  "correctness": 1-5,
  "overfit_risk": 1-5,
  "usefulness": 1-5,
  "conflict_risk": 1-5,
  "reason": "...",
  "revised_memory": "..."
}
```

## 九、Memory 调用方式

推理时不要把所有 memory 全部塞进 prompt，而是应该动态检索：

```text
输入样本
  ↓
提取关键词和语境特征
  ↓
从 memory bank 检索 top-k 相关 memory
  ↓
按 Skill 类型分配 memory
  ↓
注入对应 Skill prompt
```

不同 Skill 调用不同 memory：

| Skill | 调用 Memory |
| --- | --- |
| Mechanism Skill | Label Definition Memory、Failure Pattern Memory |
| Risk Skill | Risk Avoidance Memory |
| Strategy Skill | Context Strategy Memory |
| Response Skill | Response Style Memory |
| Retriever | Retrieval Policy Memory |
| Checker | Format / Consistency Memory |

这样可以避免 memory 太多导致 prompt 噪音过大。

Memory Retriever 的排序不应该只看文本相似度，建议综合以下特征：

1. `skill_type` 是否匹配
2. `platform` 是否匹配
3. `relationship` 是否匹配
4. `interaction_goal` 是否匹配
5. `risk_tags` 是否匹配
6. `trigger` 语义相似度
7. memory 历史效果
8. memory 冲突风险

每个 Skill 注入的 memory 数量也需要限制：

| Skill | 建议 top-k |
| --- | --- |
| Mechanism Skill | 3-5 |
| Risk Skill | 2-4 |
| Strategy Skill | 2-4 |
| Response Skill | 2-3 |
| Checker Skill | 固定规则为主，不建议注入太多动态 memory |

Memory Retriever 不以数量取胜，而以相关性、低冲突和历史有效性为优先。

## 十、建议代码组织

当前工程已经具备 `src/skillflow.py`、`src/skills/`、`src/fewshot.py`、`src/debug_logger.py`、`src/error_analyzer.py` 和 `agent_wiki/`，不建议推倒重来。

建议在现有结构上增量加入：

```text
src/memory/
  schemas.py
  memory_store.py
  memory_retriever.py
  candidate_generator.py
  memory_judge.py

agent_memory/
  active_memory.jsonl
  candidate_memory.jsonl
  rejected_memory.jsonl
  disabled_memory.jsonl
  memory_update_logs.jsonl

runs/
  run_YYYYMMDD_HHMM/
    config.json
    submission.jsonl
    dev_eval_report.json
    format_report.json
    memory_usage.jsonl
    error_report.md
```

其中：

- `memory_store.py` 负责读取、写入和状态管理。
- `memory_retriever.py` 负责按输入样本和 Skill 类型检索 memory。
- `candidate_generator.py` 负责从 error analysis 中生成 candidate memory。
- `memory_judge.py` 负责离线调用本地大模型进行评审判定。
- `active_memory.jsonl` 是最终推理链路唯一读取的 memory 文件。
- `memory_usage.jsonl` 记录每条 memory 在本次运行中的使用次数、影响样本和正负效果。
- `config.json` 记录模型名、prompt version、SkillFlow version、active memory version、few-shot index version、decoding settings 和 commit hash。

## 十一、实验规划

### 实验 1：Baseline

配置：

```text
固定 prompt
无 memory
无 few-shot
```

目的：得到初始分数和错误分布。

### 实验 2：Few-shot Retriever

配置：

```text
固定 prompt + few-shot examples
```

目的：验证相似样本检索是否提升结果。

### 实验 3：Skills + SkillFlow

配置：

```text
多 Skill 分步执行
无 memory
```

目的：验证模块化流程是否降低策略不一致和格式错误。

### 实验 4：SkillFlow + Active Memory

配置：

```text
SkillFlow + 人工 / API 筛选后的 active memory
```

目的：验证 memory 是否提升机制判断和风险控制。

### 实验 5：Memory Ablation

配置：

```text
无 memory
只用 label memory
只用 risk memory
只用 context memory
全量 memory
```

目的：判断哪类 memory 最有效。

每次实验都需要记录以下指标：

| 指标 | 作用 |
| --- | --- |
| `dev proxy total score` | 公开 dev 代理总分 |
| `mechanism_accuracy` | 判断机制分类是否改善 |
| `strategy_score` | 判断策略选择是否改善 |
| `risk_label_f1` | 判断风险识别是否改善 |
| `response_reference_token_f1` | 判断回复和参考答案的 token overlap |
| `format_score` | 判断格式是否有效 |
| `format_checker pass rate` | 判断提交稳定性 |
| `strategy-response inconsistency rate` | 判断策略和回复是否一致 |
| `overpraise / preachiness / over_coldness rate` | 判断是否增加 Bloom 风险 |
| `average inference time` | 判断推理成本 |
| `failure rate` | 判断运行稳定性 |

公开 dev scorer 只是 proxy，最终 leaderboard 由 hidden evaluation 决定。因此实验不能只围绕 dev 分数贪心优化，还要观察风险行为、格式稳定性、策略一致性和 hidden test 泛化风险。

## 十二、最终推荐开发顺序

当前本地工程已经完成基础 SkillFlow、Wiki、few-shot、debug log、error analysis 和 Ollama qwen3:8b 接入。后续建议按下面顺序推进：

| 优先级 | 任务 | 目标 |
| --- | --- | --- |
| P0 | 跑通 baseline 和 JSONL 输出 | 已基本完成 |
| P1 | 加入 debug log | 已基本完成 |
| P2 | 拆分 Skills + SkillFlow | 已基本完成 |
| P3 | 加入 few-shot retriever | 已基本完成 |
| P4 | 建立 active memory schema + memory retriever | 让 Skill 能读取受控 memory |
| P5 | 建立 candidate memory 生成机制 | 从错误分析中产出候选经验 |
| P6 | 接入本地大模型 judge | 只用于离线判断 memory 是否保留 |
| P7 | 建立 dev ablation validation | 验证 memory 加入后不降核心指标、不增加风险 |
| P8 | 建立 active / disabled / rejected memory 管理 | 支持回滚和版本控制 |
| P9 | 建立 Memory Freeze 流程 | 正式 test 前冻结 memory、prompt、SkillFlow、few-shot 和解码参数 |
| P10 | 做 memory ablation 实验 | 判断哪类 memory 真正有效 |
| P11 | 再考虑是否需要微调 | 仅在工程增强收益到顶后再评估 |

## 十三、提交链路合规边界

为了避免外部 API 使用边界不清，最终提交链路需要固定为：

```text
test_input.jsonl
  ↓
本地合规模型
  ↓
SkillFlow
  ↓
active memory 检索
  ↓
few-shot 检索
  ↓
规则策略选择
  ↓
Checker & Repair
  ↓
submission.jsonl
```

最终提交链路中不包含：

- 外部 API 模型
- 外部 API reranker
- 外部 API checker
- 外部 API repair
- 外部 API 对 test 样本的任何实时判断
- 外部 API 对 test debug log、中间输出或候选回复的任何读取

离线 memory 评审由本地评审模型完成：

```text
dev/train 错例
  ↓
candidate memory
  ↓
Local LLM Judge
  ↓
active / rejected / disabled memory
```

换句话说，本地评审模型（Local LLM Judge）的作用是帮助选择和改写经验，不是帮助生成最终提交答案。整个流程均完全离线。

## 十四、补强后的最终架构

补强后的完整闭环如下：

```text
Train / Dev Data
  ↓
Baseline Generation
  ↓
Debug Log
  ↓
Error Analysis
  ↓
Candidate Memory Generator
  ↓
Local LLM Judge / Human Review
  ↓
Static Conflict Check
  ↓
Dev Ablation Validation
  ↓
Active Memory Bank
  ↓
Memory Freeze
  ↓
Test-time Local Inference Only
  ↓
Submission JSONL
```

正式 test 阶段固定为：

```text
test_input.jsonl
  ↓
Frozen Prompt + Frozen SkillFlow + Frozen Active Memory + Frozen Few-shot Index
  ↓
Local <=20B Model
  ↓
Checker & Repair
  ↓
format_checker.py
  ↓
test_submission.jsonl
```

## 十五、Local LLM Judge 使用边界

虽然评判工作已迁移至本地大模型（Local LLM Judge），但为了绝对防止对测试集信息的泄漏或过拟合，本地 Judge 的使用边界仍然按照严格隔离原则收紧。

允许：

1. 读取 train/dev 错例分析产生的 candidate memory。
2. 判断 candidate memory 的泛化性、正确性、过拟合风险、实用性和冲突风险。
3. 对 candidate memory 做抽象化改写，使其更像通用规则，而不是 dev 样本答案。
4. 输出 `accept / revise / reject` 决策。

不允许：

1. 在测试集评估阶段（Test Inference）被实时调用。
2. 读取 `test_input.jsonl`，或读取任何测试集相关的 debug logs。
3. 基于 test 样本表现更新 active memory。

结论是：本地大模型 Judge 只允许在 train/dev 阶段离线评审 memory。正式 test 前冻结 active memory，测试阶段完全关闭评审逻辑。

## 十六、Memory Freeze 与版本管理

正式生成 `test_submission.jsonl` 前，需要进入 Memory Freeze 阶段。

冻结对象：

| 对象 | 说明 |
| --- | --- |
| Frozen Active Memory | 冻结后的 `active_memory.jsonl` |
| Frozen Prompt | 冻结 prompt builder 或 prompt template version |
| Frozen SkillFlow | 冻结 SkillFlow 执行顺序和 fallback 逻辑 |
| Frozen Few-shot Index | 冻结 train 检索索引和检索参数 |
| Frozen Decoding Settings | 冻结 temperature、max tokens、top-p 等解码参数 |
| Frozen Model | 冻结本地 <=20B 模型名称、量化版本和运行后端 |

最终 test 链路应该是：

```text
Frozen Active Memory
+ Frozen SkillFlow
+ Frozen Prompt
+ Frozen Few-shot Index
+ Frozen Decoding Settings
+ Local <=20B Model
-> submission.jsonl
```

每次正式或候选提交都需要记录元数据：

```json
{
  "run_id": "test_20260518_001",
  "model_name": "qwen3:8b",
  "model_parameter_count": "8.2B",
  "prompt_version": "prompt_v3",
  "skillflow_version": "skillflow_v2",
  "active_memory_version": "memory_v4_frozen",
  "fewshot_index_version": "train500_index_v2",
  "decoding_settings": {
    "temperature": 0.3,
    "max_tokens": 256
  },
  "date": "2026-05-18",
  "commit_hash": "..."
}
```

## 十七、SkillFlow Failure Handling

SkillFlow 不能只依赖线性执行，还需要失败回退机制。

| 失败类型 | 处理策略 |
| --- | --- |
| JSON parse failure | 先 repair 一次；失败后 fallback prompt 重新生成；再失败则使用规则默认值 |
| Low confidence mechanism | 调用 label boundary memory，增加边界 few-shot，重新判断一次 |
| Strategy-response inconsistency | 保留 strategy，只重写 `response_text`，不重新生成全部字段 |
| Risk-response conflict | 如果风险要求避免 sycophancy 但回复过度夸奖，则强制触发 response repair |
| Format checker failure | 定位非法字段，只修复错误字段，再重新检查 |
| Hidden reasoning leakage | 删除 reasoning 文本；如果无法清理，使用策略对应默认回复 |
| LLM call failure | 重试；仍失败则使用规则 fallback，避免整条样本崩溃 |

核心原则是：能局部修复就局部修复，不因为一个字段错误重生成整行输出。这样可以减少连锁漂移，也更容易定位是哪一个 Skill 出了问题。

## 十八、Memory Effectiveness Report

每条 active memory 都需要记录实际效果，避免 memory bank 只增不减。

建议记录格式：

```json
{
  "memory_id": "label_humble_complaint_001",
  "used_count": 128,
  "affected_episode_ids": ["dev_001", "dev_018"],
  "positive_cases": 12,
  "negative_cases": 2,
  "net_effect": "+0.8 dev proxy score",
  "risk_delta": {
    "sycophancy": 0,
    "preachiness": 0,
    "over_coldness": 1
  },
  "decision": "keep"
}
```

评估维度：

1. 使用次数是否足够。
2. 正向影响是否大于负向影响。
3. 是否提升机制、策略、risk 或 response 指标。
4. 是否增加 sycophancy、preachiness、over_coldness 等风险。
5. 是否只对极少数 dev 样本有效。
6. 是否与已有 memory 冲突。

Memory 的最终处理建议：

| 判断 | 动作 |
| --- | --- |
| 明显正向且风险低 | keep |
| 有正向但触发条件过宽 | revise |
| 无明显收益 | disable |
| 引入明显风险或冲突 | reject / archive |

## 十九、总结

最终系统应该形成一个闭环：

```text
模型生成
  ↓
日志记录
  ↓
错误分析
  ↓
候选 memory 生成
  ↓
外部 API 模型离线评审
  ↓
active memory 更新
  ↓
SkillFlow 再次调用
  ↓
性能评估
```

这个架构的优势是：

1. 比固定 prompt 更可控
2. 比直接微调更容易调试
3. 可以沉淀错例经验
4. 可以降低 dev 过拟合风险
5. 可以通过本地评审模型筛掉低质量 memory
6. 支持回滚和 ablation
7. 更适合当前数据规模较小、评分机制复杂的比赛任务

一句话概括：

```text
用 Skills 拆任务，用 SkillFlow 控流程，用 Agent Memory 存经验，
用本地评审模型离线筛选 memory，最终提交链路只使用本地合规模型和固化后的 active memory。
```
