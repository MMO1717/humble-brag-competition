# BRAG-Pipeline no-overfit 工程增强报告

日期：2026-05-17

## 摘要

本轮改造对象是队友的 `BRAG-Pipeline-main`。目标不是追 public dev 分，而是把当前 v6e 中已经验证过的低过拟合工程能力迁入队友 pipeline：通用 social judge、风险关键词渲染、策略规则增强、response fallback、离线 stress set 和无模型验收流程。

当前没有 `BRAG-Pipeline-main/.env`，所以本轮没有跑完整 LLM dev 分数。保留标准按离线门槛执行。

## 主要改动

| 模块 | 改动 |
|---|---|
| social judge | 新增通用社会语用 judge，检查过度奉承、说教、语境不匹配、策略不匹配和自然度。 |
| strategy rules | 用 `interaction_goal + platform + relationship + mechanism` 扩展策略决策，减少粗糙默认策略。 |
| risk rendering | 将 risk 文本规范化为官方 evaluator 可识别的关键词表达，保留 1-3 个通用风险。 |
| response fallback | LLM 回复出现 hard issue 时，使用抽象模板 fallback；模板不绑定具体样本实体。 |
| stress set | 新增 80 条 synthetic stress rows，覆盖 8 种 mechanism 和 2 类 context。 |
| README | 增加 no-overfit 离线检查说明。 |

## 验收结果

| 检查项 | 结果 |
|---|---:|
| Python 静态编译 | pass |
| 离线策略/risk/judge/fallback 检查 | pass |
| stress rows | 80 |
| stress format errors | 0 |
| stress format warnings | 0 |
| stress unique responses | 8 |
| stress most frequent response count | 20 |
| stress social hard issues | 0 |
| 高风险样本特征扫描 | 0 matches |

## 离线输出

| 文件 | 说明 |
|---|---|
| `BRAG-Pipeline-main/outputs/no_overfit_offline/stress_input.jsonl` | synthetic stress 输入。 |
| `BRAG-Pipeline-main/outputs/no_overfit_offline/stress_submission.jsonl` | 离线生成的 stress 输出。 |
| `BRAG-Pipeline-main/outputs/no_overfit_offline/offline_check_report.md` | 离线检查摘要。 |

## 判断

本轮改动满足保留门槛，不需要回档。

它提升的是队友 pipeline 的工程稳健性和低过拟合验证能力；还不能说明队友 pipeline 的真实比赛分数提升。下一步如果要评估效果，需要配置可用 OpenAI-compatible 模型接口，跑完整 dev，然后和当前 `v6e_generalized = 76.894` 做分项对比。
