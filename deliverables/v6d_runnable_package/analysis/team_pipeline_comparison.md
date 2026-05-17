# 队友 Pipeline 与当前 v6e 架构对比报告

日期：2026-05-17

对比对象：

- 队友 demo：`BRAG-Pipeline-main`
- 当前候选：`deliverables/v6d_runnable_package` 里的 `v6e_generalized`

## 总结

`BRAG-Pipeline-main` 是一个结构清楚的最小可运行工程 demo。它最大的优点是模块拆得比较干净：LLM 调用、prompt、策略规则、后处理、字段校验、运行输出、官方检查都分开了，适合作为后续多人协作和模型/prompt 实验的框架。

但它目前还不是一个可直接替换当前提交方案的高分版本。主要差距在：

- `bragging_mechanism` 稳定性还没有验证和校准。
- `response_strategy` 规则树偏粗。
- `risk_assessment` 没有充分利用官方 evaluator 的风险关键词机制。
- 没有当前 v6e 里的 no-overfit social judge、stress set 和保留门槛。
- 本地没有找到完整 dev run 的结果文件，所以暂时不能给它真实分数。

一句话判断：队友代码适合当“实验平台”，当前 `v6e_generalized` 更适合作为“可提交候选”。

## 高层对比

| 维度 | `BRAG-Pipeline-main` | 当前 `v6e_generalized` |
|---|---|---|
| 主要定位 | 最小可运行 OpenAI-compatible demo | 已评分、已验证的提交候选 |
| 主流程 | mechanism LLM -> understanding LLM -> 规则选 strategy -> response LLM | base 输出 -> generalized 后处理 -> v6e response -> social judge |
| 策略选择 | `strategy_rules.py` 里的小规则树 | v6c/v6d 演化出的 generalized 策略/风险层 |
| 机制判断 | 单独 LLM 分类器 | qwen 基线输出 + generalized 后处理；v6e 不新增具体文本硬规则 |
| 回复生成 | LLM 生成，再清洗 | 抽象模板池 + 稳定 slot 组合 + hard issue 才安全重写 |
| 校验 | 本地 schema validator + 官方 checker | 官方 checker + social-rubric judge + stress set |
| 分数证据 | 当前目录下没找到完整 run 结果 | dev proxy `76.894`，format 0 errors |
| 过拟合姿态 | 规则少，天然不太贴 dev，但效果未校准 | 明确做了 no-overfit 约束和门槛验证 |

## 队友代码写得好的地方

| 模块 | 优点 |
|---|---|
| 项目结构 | `llm_client.py`、`prompts.py`、`strategy_rules.py`、`postprocess.py`、`validators.py`、`pipeline.py` 职责清楚。 |
| 输出管理 | 每次运行生成独立 timestamp 文件夹，包含 `submission.jsonl`、report、manifest、`RES.md`，避免覆盖历史结果。 |
| API 抽象 | 用 OpenAI-compatible 的 `base_url`、`api_key`、`model`，方便切本地或远程模型。 |
| 官方工具接入 | 自动调用官方 `format_checker.py` 和 `evaluate_dev.py`，并保存完整报告。 |
| 清洗逻辑 | 会清理 code fence、`<think>`、`analysis:`、role prefix、JSON wrapper 等脏输出。 |
| 最终 JSONL 生成 | 不让模型直接写最终提交文件，而是 Python dict 组装 7 字段，这个工程选择是对的。 |

## 当前主要弱点

| 问题 | 影响 |
|---|---|
| 没有完整 dev 结果 | 现在只能做代码级审查，不能判断实际分数。 |
| `MAX_ITEMS = 3` 是默认值 | 容易误跑成 smoke test，然后误以为是完整 dev 分数。 |
| 策略树太粗 | 很多 public/professional 场景都会变成 `neutral_observation`，很多私聊场景默认 `light_acknowledgment`，strategy 分可能被限制。 |
| risk 文本不够 evaluator-oriented | `risk_assessment` 主要依赖模型文本或 generic fallback，risk F1 可能不稳定。 |
| mechanism prompt 示例太少 | 目前只有少量定义和例子，机制分类大概率是最大风险点。 |
| response 仍高度依赖模型 | 自然度可能更好，但可复现性、过度夸赞、context mismatch 更难控制。 |
| 本地 validator 弱于官方 checker | 对 `set_boundary`、`light_acknowledgment`、`no_response` 的 praise/overpraise 约束没有完全复刻官方。 |
| 缺少 conditional rewriter | 输出格式合法但社交上不合适时，当前 pipeline 会直接接受。 |

## 架构差异

### 队友 Pipeline

```text
official input
-> mechanism_classifier_messages()
-> understanding_messages()
-> choose_strategy()
-> response_messages()
-> postprocess cleanup
-> local validator
-> official format/eval scripts
```

这个架构适合快速测试不同模型和 prompt，是一个不错的 MVP。

### 当前 v6e

```text
v6b/v6c base outputs
-> postprocess_full_generalized.py
-> postprocess_response_text_v6e_generalized.py
-> paper-rubric social judge
-> only hard issue rewrite once
-> dev/test/stress gates
```

这个架构没有队友版本那么通用，但更接近比赛提交形态：有稳定分数、有格式验证、有过拟合审计、有 stress set。

## 分数证据

| 版本 | Proxy Dev | Mechanism | Strategy | Risk F1 | Response F1 | Format |
|---|---:|---:|---:|---:|---:|---:|
| 队友 pipeline | 未在本地测到 | 未测 | 未测 | 未测 | 未测 | 静态编译通过 |
| v6e_generalized | 76.894 | 0.9556 | 0.8333 | 0.7481 | 0.1065 | 0 errors |

我对队友项目做了静态检查：

```text
python3 -m py_compile BRAG-Pipeline-main/*.py BRAG-Pipeline-main/src/*.py
pass
```

但 `BRAG-Pipeline-main/outputs/` 下面没有找到实际运行生成的 `submission.jsonl` 或 `dev_eval_report.json`，所以现在不能直接对比分数。

## 最适合怎么合并两边思路

不建议现在用队友 pipeline 替换 `v6e_generalized`。更合理的做法是：把队友 pipeline 当成实验框架，把你这边已经验证过的 no-overfit 模块迁进去。

| 优先级 | 建议动作 | 原因 |
|---|---|---|
| 1 | 把 `judge_social_rubric.py` 接到 `BRAG-Pipeline-main` | 给 demo 加上 no-overfit 社会语用校验。 |
| 2 | 用 `postprocess_full_generalized.py` 的通用规则增强 `strategy_rules.py` | 低风险提升 strategy 稳定性。 |
| 3 | 增加官方风险关键词渲染 | 可能提升 `risk_label_f1`，且不需要 dev-specific 规则。 |
| 4 | 加完整 dev run 报告表 | 没有完整 dev 分数就无法比较方案。 |
| 5 | 加 stress set 支持 | 避免只看 public dev。 |
| 6 | 再用这个框架比较不同 <=20B 模型 | 这是队友 pipeline 真正适合发挥的地方。 |

## 可以给队友提的 PR 方向

| PR 名称 | 范围 |
|---|---|
| `add-social-rubric-judge` | 移植 `judge_social_rubric.py`，生成后做 social hard/soft issue 检查。 |
| `improve-risk-rendering` | 把模型 risk 文本转换成带官方 evaluator 关键词的风险描述。 |
| `strategy-rules-v2` | 用 goal/platform/relationship/mechanism 扩展 `choose_strategy()`。 |
| `v6e-response-fallback` | 当 LLM 回复不通过 judge 时，用 v6e 抽象模板 fallback。 |
| `full-dev-report-table` | 每次完整 dev run 自动输出 mechanism/strategy/risk/response 分项表。 |

## 结论

当前提交候选仍建议用 `v6e_generalized`。

`BRAG-Pipeline-main` 值得保留，但定位应该是“多人协作实验平台”，不是当前最高优先级的提交版本。它的工程结构比当前 v6e 脚本化方案更适合长期扩展；但在机制分类、策略规则、risk 渲染、social judge、stress set 和完整分数验证补齐前，不能直接替代当前方案。
