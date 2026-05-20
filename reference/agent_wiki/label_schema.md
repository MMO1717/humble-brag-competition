# 标签体系 / Label Schema

## English Prompt Notes

Final output must contain exactly these fields: episode_id, bragging_mechanism, speaker_intention, desired_feedback, risk_assessment, response_strategy, response_text.

Copy episode_id exactly from the input. Do not let the model invent it.

bragging_mechanism must be one of: humble_complaint, faux_modesty, achievement_drop, comparison_superiority, scarcity_flex, understated_flex, self_aware_brag, other.

response_strategy must be one of: validate, light_acknowledgment, ask_followup, humor_tease, redirect, neutral_observation, set_boundary, no_response.

risk_assessment must be a non-empty English string, not a list.

response_text must be short, natural English and must not mention labels, JSON, analysis, risk labels, or the word bragging.

## 中文说明

最终提交必须且只能包含官方 7 个字段。`episode_id` 必须从输入原样复制，不能交给模型生成。

`risk_assessment` 最终必须是字符串，不要输出数组。
