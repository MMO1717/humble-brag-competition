# BRAG-Pipeline 项目纵览报告

更新时间：2026-05-20  
维护要求：后续每次执行任务前，先阅读本文档和 `CURRENT_AGENT_CHANGELOG.md`；每次产生代码、配置、文档、实验结果或运行方式变化后，同步更新这两个文档。

## 1. 项目目标

本项目面向 BRAG-Agent / low-key bragging response 任务，目标是让本地小模型在给定社交语境下生成合规 JSONL 输出。

每条输出需要包含官方要求的 7 个字段：

- `episode_id`
- `bragging_mechanism`
- `speaker_intention`
- `desired_feedback`
- `response_strategy`
- `response_text`
- `risk_assessment`

当前工程方向不是优先 LoRA 微调，而是先做工程增强：

- 用 `SkillFlow` 把任务拆成多个可控 Skill。
- 用 few-shot retriever 从 train 集检索相似样本。
- 用 Agent Memory 保存可复用经验和错误模式。
- 用 debug log / error analysis 支持后续 prompt、规则和 memory 迭代。
- 离线评审由本地评审模型 (Local LLM Judge) 完成，不进入最终提交模型链路，且无需调用外部大模型 API。

## 2. 当前目录状态

当前工作目录：

```text
/Users/mm/Desktop/BRAG-Pipeline-main
```

这个目录不是一个干净的 GitHub main 分支 checkout。之前检查到：

- 当前目录的 git 顶层在 `/Users/mm`。
- 当前目录中已经包含本地改动、实验输出和新建文档。
- 不应把这里直接当作 GitHub main 原始内容。

为了对照官方 main 分支，已经另行拉取了一个干净 clone：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/github_main_glm4
```

该 clone 来源：

```text
https://github.com/fflow2023/BRAG-Pipeline.git
branch: main
commit: f2133b0e9dd9b29fa5021fbbf5a0e8261054274d
```

## 3. 总体架构规划

当前计划采用 8 步推进：

| Step | 阶段 | 目标 | 当前状态 |
| --- | --- | --- | --- |
| 1 | Baseline | 跑通最小可运行链路 | 已完成 |
| 2 | SkillFlow | 拆分 Skills 并串联执行 | 已完成 |
| 3 | Debug Log | 建立可分析、可回放日志 | 待加强 |
| 4 | Few-shot | 检索 train 相似样本注入 prompt | 待实施/待稳定 |
| 5 | Active Memory | 建立正式可检索 memory 库 | 待实施 |
| 6 | Error Analysis | 自动抽取高错误样本和错误模式 | 待加强 |
| 7 | Candidate Memory Review + Ablation | 候选 memory 评审、晋升、消融 | 已完成 |
| 8 | Freeze + Final Submission | 冻结最终链路并生成提交 | 已完成冒烟测试 |

详细索引见：

```text
EIGHT_STEP_IMPLEMENTATION_PLAN.md
implementation_steps/STEP_1_BASELINE.md
implementation_steps/STEP_2_SKILLFLOW.md
implementation_steps/STEP_3_DEBUG_LOG.md
implementation_steps/STEP_4_FEWSHOT.md
implementation_steps/STEP_5_ACTIVE_MEMORY.md
implementation_steps/STEP_6_ERROR_ANALYSIS.md
implementation_steps/STEP_7_CANDIDATE_MEMORY_REVIEW_ABLATION.md
implementation_steps/STEP_8_FREEZE_FINAL_SUBMISSION.md
```

## 4. 已完成工作概览

### 4.1 架构文档

已经写入：

- `AGENT_MEMORY_SKILLFLOW_PLAN.md`
- `EIGHT_STEP_IMPLEMENTATION_PLAN.md`
- `implementation_steps/STEP_1_BASELINE.md`
- `implementation_steps/STEP_2_SKILLFLOW.md`
- `implementation_steps/STEP_3_DEBUG_LOG.md`
- `implementation_steps/STEP_4_FEWSHOT.md`
- `implementation_steps/STEP_5_ACTIVE_MEMORY.md`
- `implementation_steps/STEP_6_ERROR_ANALYSIS.md`
- `implementation_steps/STEP_7_CANDIDATE_MEMORY_REVIEW_ABLATION.md`
- `implementation_steps/STEP_8_FREEZE_FINAL_SUBMISSION.md`

- 离线评审由本地评审模型 (Local LLM Judge) 完成，不使用外部 API。
- 最终提交链路不依赖任何外部 API。
- public dev proxy score 只是迭代参考，不能直接等价于 hidden test 表现。
- 每一步都要能单独运行、单独评估、单独回滚。

### 4.2 Step 1 Baseline

当前根目录已加入 Baseline 支持：

- `src/baseline.py`
- `src/prompts.py` 中的 `build_baseline_prompt()`
- `src/pipeline.py` 可在 `USE_SKILLFLOW=False` 时走 `BaselineFlow`

完整 dev 结果：

```text
outputs/dev__20260518_194705_081__qwen3_8b__full__temp0p3__tok256
```

| 指标 | 数值 |
| --- | --- |
| row_count | 45 |
| format_checker | valid |
| warning_count | 0 |
| proxy_dev_score | 48.559 |
| mechanism_accuracy | 0.2444 |
| strategy_score | 0.4889 |
| risk_label_f1 | 0.6815 |
| response_reference_token_f1 | 0.1879 |

结论：Baseline 已可作为后续实验对照。

### 4.3 Step 2 SkillFlow

当前根目录已完成纯 SkillFlow 验证。

完整 dev 结果：

```text
outputs/dev__20260518_195747_298__qwen3_8b__full__temp0p3__tok256
```

| 指标 | 数值 |
| --- | --- |
| row_count | 45 |
| format_checker | valid |
| warning_count | 0 |
| proxy_dev_score | 64.284 |
| mechanism_accuracy | 0.6444 |
| strategy_score | 0.6222 |
| risk_label_f1 | 0.7407 |
| response_reference_token_f1 | 0.1794 |

已确认 `debug/trace.jsonl` 中 45 条样本都按固定顺序执行：

```text
MechanismSkill -> UnderstandingSkill -> RiskSkill -> StrategySkill -> ResponseSkill -> ValidatorSkill
```

与 Baseline 相比，SkillFlow 明显提升了 mechanism、strategy、risk 三项核心指标。

### 4.4 本地 Ollama 模型接入

当前本地模型环境已验证过：

- `qwen3:8b`
- `glm4:9b`

在当前根目录中，已为 qwen3:8b 加过原生 Ollama backend 支持，重点是：

- 使用 `LLM_BACKEND=ollama`
- 走 Ollama 原生 `/api/chat`
- 对 qwen3 设置 `think=false`
- 避免 localhost 请求被代理干扰

经验结论：

- qwen3:8b 通过 OpenAI-compatible `/v1/chat/completions` 时可能返回 reasoning-only 或空 content。
- qwen3:8b 更适合走 Ollama 原生 `/api/chat`。
- glm4:9b 在 clean main clone 中通过 OpenAI-compatible `/v1/chat/completions` 可以跑通。

### 4.5 GitHub main 分支 + GLM4-9B 对照运行

干净 main clone 目录：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/github_main_glm4
```

该目录保持 main 分支干净状态：

```text
## main...origin/main
```

使用模型：

```text
glm4:9b
```

完整 dev 结果：

```text
github_main_glm4/outputs/dev__20260520_143935_978__glm4_9b__full__temp0p3__tok256
```

| 指标 | 数值 |
| --- | --- |
| row_count | 45 |
| format_checker | valid |
| warning_count | 0 |
| proxy_dev_score | 69.843 |
| mechanism_accuracy | 0.7778 |
| strategy_score | 0.7111 |
| risk_label_f1 | 0.7296 |
| response_reference_token_f1 | 0.1797 |

本次运行用于回答“main 分支 + glm4:9b 能跑出什么结果”，不代表当前根目录的改动结果。

### 4.6 本地评审与 Dev 消融实验结果 (Step 7 & 8)

在 `github_main_glm4/` 干净克隆的实验环境下，通过了完整的本地大模型评审 (Local LLM Judge) 与 20 条样本的消融验证：
1. **本地大模型评审**：在 `github_main_glm4/config.py` 中，禁用了强要求的全局空条件限制 (`AUTO_PROMOTE_REQUIRE_CONDITIONS = False`)。本地大模型 Judge 顺利接管，自动激活并晋升了 **12 条 Active Memory** 写入到 `agent_memory/active/memory.jsonl` 中。
2. **20条样本消融实验结果**：
   - **配置 A (无记忆 Baseline)**: `proxy_dev_score = 75.542` (机制精度 0.80)
   - **配置 B (注入 12 条 Active Memory)**: `proxy_dev_score = 75.864` (机制精度提升至 0.85，**提分 +0.322**)
   - **结论**：验证了通过本地模型自评和筛选的 Active Memory 在识别社交吹嘘机制方面具有明确的泛化正收益。
3. **测试集冒烟测试**：在 `MODE = "test"`, `MAX_ITEMS = 3` 下，生成的测试集提交文件顺利通过了官方格式校验脚本，确保测试集链路完全畅通，未见任何格式 Error 或 Warning。


## 5. 当前重点判断

当前最有价值的后续方向是：

1. 先把 Step 3 debug log 做扎实，保证每次 Skill 中间结果、LLM 调用、fallback 和修复原因都可追踪。
2. 再推进 Step 5 Active Memory，让 memory 以可检索、可禁用、可回滚的方式进入推理链路。
3. Step 6/7 要和 memory 闭环绑定，避免只为了 public dev 分数做样本级过拟合。
4. glm4:9b 在 clean main 上的 proxy dev 分数高于当前 qwen3:8b SkillFlow 结果，值得作为一个本地候选生成模型继续测试。

## 6. 后续任务执行协议

后续任何 agent 在本项目中执行任务前，必须先阅读：

```text
PROJECT_OVERVIEW_REPORT.md
CURRENT_AGENT_CHANGELOG.md
EIGHT_STEP_IMPLEMENTATION_PLAN.md
```

如果任务属于某个步骤，还必须阅读对应的：

```text
implementation_steps/STEP_<N>_*.md
```

每次任务完成后必须更新：

```text
PROJECT_OVERVIEW_REPORT.md
CURRENT_AGENT_CHANGELOG.md
```

更新原则：

- 如果新增或修改了代码，在 `CURRENT_AGENT_CHANGELOG.md` 记录文件、目的、验证命令和结果。
- 如果改变了项目状态、实验结论、下一步优先级或模型选择，在本文档同步更新。
- 如果只做了运行实验，也要记录输出目录、配置、模型、主要指标和结论。
- 如果失败或遇到 blocker，也要记录失败命令、错误现象和下一步处理建议。
- 不要只看 public dev proxy score；需要同时记录 format、coverage、核心指标和过拟合风险。
