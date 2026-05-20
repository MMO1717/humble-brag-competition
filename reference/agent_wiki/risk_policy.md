# 风险策略 / Risk Policy

## English Prompt Notes

Use one or two risk labels when possible. Avoid listing every risk.

misrecognition: the reply may misread the speaker's intent, over-assume expertise, or miss the subtle self-presentation.

context_insensitivity: the reply may ignore platform, audience, relationship, or formality.

sycophancy: the reply may overpraise, flatter, or blindly validate the speaker.

preachiness: the reply may sound moralizing, judgmental, or like a lecture.

strategy_inconsistency: the reply may conflict with the chosen response strategy or interaction goal.

over_coldness: the reply may sound too curt, dismissive, or emotionally flat.

risk_assessment should be a short English sentence that explicitly includes evaluator-detectable risk wording. Prefer these phrases in the sentence: sycophancy, preachiness, misrecognition, context insensitivity, strategy inconsistency, over-coldness.

## 中文说明

公开 dev evaluator 会从 `risk_assessment` 字符串中抽取风险关键词，所以最终文本需要显式包含关键词。
