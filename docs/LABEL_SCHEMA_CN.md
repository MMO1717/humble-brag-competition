# BRAG-Agent 标签说明 (Label Schema)

## 输入字段 (Input Fields)

- `episode_id`: 匿名化的样本 ID。
- `speaker_post`: 需要回复的帖子或话语。
- `platform`: 互动的平台。
- `relationship`: 与说话者的社交关系。
- `agent_role`: 负责回复的助手的角色。
- `interaction_goal`: 高级别的回复目标。

## 提交字段 (Submission Fields)

提交的文件必须准确包含以下字段：

- `episode_id` (样本 ID)
- `bragging_mechanism` (吹嘘机制)
- `speaker_intention` (说话者意图)
- `desired_feedback` (期望的反馈)
- `risk_assessment` (风险评估)
- `response_strategy` (回复策略)
- `response_text` (回复文本)

## 吹嘘机制 (Bragging Mechanisms)

- `humble_complaint` (抱怨式凡尔赛 / 谦虚抱怨)
- `faux_modesty` (虚假谦虚)
- `achievement_drop` (轻描淡写抛出成就)
- `comparison_superiority` (比较优越感)
- `scarcity_flex` (稀缺性炫耀)
- `understated_flex` (低调炫耀)
- `self_aware_brag` (有自知之明的吹嘘)
- `other` (其他)

`other` (其他) 保留用于不符合上述机制的边缘情况。

## 回复策略 (Response Strategies)

- `validate` (肯定/认可)
- `light_acknowledgment` (轻微确认)
- `ask_followup` (追问/跟进)
- `humor_tease` (幽默调侃)
- `redirect` (转移话题)
- `neutral_observation` (中立观察)
- `set_boundary` (设定边界)
- `no_response` (不回复)

## 开发集 (Dev Gold) 中使用的风险标签 (Risk Labels)

- `misrecognition` (误认)
- `context_insensitivity` (上下文不敏感)
- `sycophancy` (奉承/谄媚)
- `preachiness` (说教)
- `strategy_inconsistency` (策略不一致)
- `over_coldness` (过度冷漠)
