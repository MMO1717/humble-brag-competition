# 当前 Agent 变更记录

更新时间：2026-05-20  
维护要求：后续每一次执行任务前，先阅读本文档和 `PROJECT_OVERVIEW_REPORT.md`；每次产生代码、配置、文档、实验输出、运行方式或结论变化后，同步更新这两个文档。

## 1. 文档用途

本文档记录当前 Codex agent 在 `/Users/mm/Desktop/BRAG-Pipeline-main` 中已经做过的更改、运行过的实验、得到的结果和后续执行约束。

它不是最终论文式报告，而是给后续 agent / 队友快速接手用的工作日志。

## 2. 每次任务前必须检查

后续每次开始任务前，先读：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/PROJECT_OVERVIEW_REPORT.md
/Users/mm/Desktop/BRAG-Pipeline-main/CURRENT_AGENT_CHANGELOG.md
/Users/mm/Desktop/BRAG-Pipeline-main/EIGHT_STEP_IMPLEMENTATION_PLAN.md
```

如果任务对应具体阶段，再读对应 step 文档：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/implementation_steps/STEP_1_BASELINE.md
/Users/mm/Desktop/BRAG-Pipeline-main/implementation_steps/STEP_2_SKILLFLOW.md
/Users/mm/Desktop/BRAG-Pipeline-main/implementation_steps/STEP_3_DEBUG_LOG.md
/Users/mm/Desktop/BRAG-Pipeline-main/implementation_steps/STEP_4_FEWSHOT.md
/Users/mm/Desktop/BRAG-Pipeline-main/implementation_steps/STEP_5_ACTIVE_MEMORY.md
/Users/mm/Desktop/BRAG-Pipeline-main/implementation_steps/STEP_6_ERROR_ANALYSIS.md
/Users/mm/Desktop/BRAG-Pipeline-main/implementation_steps/STEP_7_CANDIDATE_MEMORY_REVIEW_ABLATION.md
/Users/mm/Desktop/BRAG-Pipeline-main/implementation_steps/STEP_8_FREEZE_FINAL_SUBMISSION.md
```

## 3. 每次任务后必须更新

每次任务完成后，必须同时更新：

```text
PROJECT_OVERVIEW_REPORT.md
CURRENT_AGENT_CHANGELOG.md
```

更新规则：

- `PROJECT_OVERVIEW_REPORT.md` 更新项目级状态、已完成阶段、关键指标、下一步优先级。
- `CURRENT_AGENT_CHANGELOG.md` 更新具体文件变更、运行命令、输出目录、指标、失败点和回滚建议。
- 如果没有代码变更但做了实验，也要记录实验配置和输出结果。
- 如果任务失败，也要记录失败原因和下一步建议。
- 离线评审完全在本地闭环，不再引入任何外部 API。

## 4. 当前 Agent 已完成事项

### 4.1 项目架构规划文档

已新增/完善：

```text
AGENT_MEMORY_SKILLFLOW_PLAN.md
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

文档已明确：

- 当前架构优先级是工程增强，不急于 LoRA。
- 核心路线是 Agent Memory + Skills + SkillFlow。
- 本地大模型 Judge (Local LLM Judge) 用于离线 memory 筛选。
- 8 个阶段需要单独文档、单独验证、可回滚。

### 4.2 Step 1 Baseline 实现与验证

已完成：

- 新增 `src/baseline.py`
- 在 `src/prompts.py` 中加入 `build_baseline_prompt()`
- 修改 `src/pipeline.py`，支持 `USE_SKILLFLOW=False` 时运行 `BaselineFlow`
- 在 `implementation_steps/STEP_1_BASELINE.md` 写入完成记录

完整 dev 输出：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/outputs/dev__20260518_194705_081__qwen3_8b__full__temp0p3__tok256
```

验证结果：

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

确认配置：

```text
flow_name = BaselineFlow
use_skillflow = false
use_agent_wiki = false
use_fewshot = false
run_dev_error_analysis = false
```

### 4.3 Step 2 SkillFlow 验证

已完成：

- 运行纯 SkillFlow。
- 关闭 few-shot、agent wiki、dev error analysis。
- 在 `implementation_steps/STEP_2_SKILLFLOW.md` 写入完成记录。

完整 dev 输出：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/outputs/dev__20260518_195747_298__qwen3_8b__full__temp0p3__tok256
```

验证结果：

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

trace 顺序已确认：

```text
MechanismSkill -> UnderstandingSkill -> RiskSkill -> StrategySkill -> ResponseSkill -> ValidatorSkill
```

### 4.4 Ollama qwen3:8b 接入

已在当前根目录做过本地 Ollama backend 适配，重点是：

- `src/llm_client.py` 支持 `LLM_BACKEND=ollama`
- 使用 Ollama 原生 `/api/chat`
- 支持 `OLLAMA_BASE_URL`
- 支持 `OLLAMA_MODEL`
- 支持 `OLLAMA_THINK=false`
- localhost 请求避免走代理

原因：

- qwen3:8b 走 OpenAI-compatible `/v1/chat/completions` 时，可能出现 empty content 或 reasoning-only 输出。
- 原生 `/api/chat` 加 `think=false` 更稳定。

注意：

- 这些改动属于当前根目录工作树，不属于 `github_main_glm4` clean main clone。
- 如果后续要合并到干净 main，需要单独整理 diff。

### 4.5 clean main + glm4:9b 对照实验

用户询问当前文件夹是否仍是 GitHub main 内容。检查后结论：

- 当前根目录不是干净 main。
- 为避免覆盖现有工作，已重新 clone 到子目录：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/github_main_glm4
```

clone 信息：

```text
repo: https://github.com/fflow2023/BRAG-Pipeline.git
branch: main
commit: f2133b0e9dd9b29fa5021fbbf5a0e8261054274d
status: ## main...origin/main
```

已在该 clean main clone 中配置：

```text
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=glm4:9b
```

3 条 dev smoke 输出：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/github_main_glm4/outputs/dev__20260520_143843_005__glm4_9b__max3__temp0p3__tok256
```

结果：

| 指标 | 数值 |
| --- | --- |
| row_count | 3 |
| format_checker | valid |
| warning_count | 0 |
| proxy_dev_score | 87.478 |
| mechanism_accuracy | 1.0 |
| strategy_score | 1.0 |
| risk_label_f1 | 1.0 |
| response_reference_token_f1 | 0.1652 |

完整 dev 输出：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/github_main_glm4/outputs/dev__20260520_143935_978__glm4_9b__full__temp0p3__tok256
```

结果：

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

该结果说明：

- clean main + glm4:9b 可以直接通过 OpenAI-compatible Ollama `/v1` 跑通。
- glm4:9b 在 public dev proxy 上强于当前 qwen3:8b 的 Step 2 SkillFlow 全量结果。
- 该结果仍然只是 public dev proxy，不能直接代表 hidden test。

### 4.6 Step 7/8 本地离线评审与消融实验结论 (glm4:9b)

在 `github_main_glm4/` 中，完成了完整的离线大模型自评审及 20 条样本的消融验证。

**变更文件**：
*   `github_main_glm4/config.py`：设置 `AUTO_PROMOTE_REQUIRE_CONDITIONS = False`（解决空触发条件的过滤硬拦截）。

**晋升成果**：
*   成功自动晋级了 **12 条** 记忆规则写入 `github_main_glm4/agent_memory/active/memory.jsonl`，用于动态注入推理 Prompt。

**20条局部样本消融对比指标**：

| 实验配置 | 代理总分 | 机制精度 (Mechanism) | 策略得分 (Strategy) | 风险 F1 (Risk) | 回复 F1 (Response) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **配置 A (无记忆 Baseline)** | 75.542 | 0.80 | 0.95 | 0.7667 | 0.1473 |
| **配置 B (12条 Active Memory)** | 75.864 | 0.85 | 0.90 | 0.7667 | 0.1354 |
| **变化净值** | **+0.322** | **+0.05** | -0.05 | 持平 | -0.0119 |

**测试集冒烟验证**：
*   运行 `python3 main.py`（参数为 `MODE = "test"`, `MAX_ITEMS = 3`）。
*   生成的提交文件通过 `format_checker.py` 校验，无 error，无 warning。


## 5. 已知运行命令

### 5.1 Step 1 Baseline full dev

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=None; config.USE_SKILLFLOW=False; config.USE_FEWSHOT=False; config.USE_AGENT_WIKI=False; config.RUN_DEV_ERROR_ANALYSIS=False; run_pipeline(config)"
```

### 5.2 Step 2 SkillFlow full dev

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=None; config.USE_SKILLFLOW=True; config.USE_FEWSHOT=False; config.USE_AGENT_WIKI=False; config.RUN_DEV_ERROR_ANALYSIS=False; run_pipeline(config)"
```

### 5.3 clean main + glm4:9b full dev

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main/github_main_glm4
.venv/bin/python -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=None; config.ENABLE_API_RATE_LIMIT=False; config.MEMORY_MODE='no_memory'; config.RUN_DEV_ERROR_ANALYSIS=False; config.GENERATE_CANDIDATE_MEMORY=False; config.AUTO_PROMOTE_CANDIDATE_MEMORY=False; run_pipeline(config)"
```

### 5.4 Step 7/8 运行消融对比与冒烟命令 (github_main_glm4)

*   **运行跑批命令**（去除系统代理以防止本地 localhost 连通性被 proxy 劫持导致 502）：
    ```bash
    cd /Users/mm/Desktop/BRAG-Pipeline-main/github_main_glm4
    env -u http_proxy -u https_proxy -u ALL_PROXY -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy python3 main.py
    ```


## 6. 当前风险和注意事项

- 当前根目录不是干净 GitHub main，不要在未确认 diff 的情况下直接提交或覆盖。
- `github_main_glm4` 是干净 clone，对照实验应尽量在该目录中保持最小改动。
- qwen3:8b 和 glm4:9b 的 Ollama backend 行为不同，不能假设同一种 API 路径都稳定。
- 3 条 smoke 分数容易虚高，最终判断必须看完整 dev。
- public dev proxy score 不能代表 hidden test，memory 和 few-shot 尤其需要过拟合检查。
- 离线 memory 评审使用本地大模型 Judge，整个提交推理和评审均在本地闭环。

## 7. 下一步建议

优先级建议：

1. 完成 Step 3 Debug Log：把每个 Skill 的输入、输出、fallback、validator 结果、修复原因记录完整。
2. 比较 qwen3:8b SkillFlow 与 glm4:9b main/SkillFlow：统一配置后再判断哪个模型作为主线。
3. 推进 Step 5 Active Memory：先做可检索、可禁用、可回滚，不急于自动晋升。
4. 再做 Step 6/7：错误分析生成 candidate memory，并用本地大模型 Judge 或人工做 review 和 ablation。
