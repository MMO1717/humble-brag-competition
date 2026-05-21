# Humble Brag Competition 项目状态报告

更新时间：2026-05-21

## 1. 当前判断

这个仓库应作为新的正式主线使用。旧的 `/Users/mm/Desktop/BRAG-Pipeline-main` 工程已经做过不少实验，但目录边界和 git 状态不够干净，不适合继续作为主战场。

当前策略是：

```text
新仓库搭主框架 -> 旧项目做 reference -> 逐步移植有效模块 -> 每步验证
```

这比继续在旧目录上叠加功能更稳，也更方便提交、回滚和向 GitHub 同步。

## 2. 已完成事项

### 2.1 新仓库已拉取

已从以下远端拉取：

```text
https://github.com/MMO1717/humble-brag-competition.git
```

当前本地路径：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/humble-brag-competition
```

当前分支：

```text
new
```

### 2.2 旧项目已归档为 reference

旧 BRAG-Pipeline 实验工程已经整理到：

```text
reference/
```

归档时排除了：

- `.env`
- `.git`
- `.venv`
- `outputs`
- `__pycache__`
- `.DS_Store`

这样可以保留旧代码、旧文档和官方评测脚本副本，同时避免把本地密钥、虚拟环境和大量实验输出上传到 GitHub。

### 2.3 已推送到 GitHub

`reference/` 已提交并推送到远端 `new` 分支。

最近一次 reference 归档提交：

```text
ef2823b Add reference pipeline archive
```

### 2.4 Phase 0 数据契约审计完成

已对 `data/Bragging_data.json` 和官方评测规范、文件及脚本进行完整审计。产出审计文档 [PROJECT_CONTRACT_AUDIT.md](file:///Users/mm/Desktop/BRAG-Pipeline-main/humble-brag-competition/PROJECT_CONTRACT_AUDIT.md) 并更新至 README.md 相关文档列表。
- 确认了当前数据字段、官方输入/输出 7 字段、合法标签和字数、模式等约束。
- 明确了当前 `Bragging_data.json` 与官方 `dev_input.jsonl` 不匹配的现状与数据读取策略。
- 规划了后续评测脚本提升方案与 Phase 1 baseline 最小实现建议。

### 2.5 Phase 1 & 2 最小 Pipeline 与调试日志已跑通

已新增/重构：

```text
main.py (支持 --backend heuristic|llm 选择)
humble_brag/llm_client.py (集成 OpenAI SDK 与 urllib 兼容降级，支持本地 Ollama 自动探测)
humble_brag/prompts.py (极简 zero-shot Prompt 'llm_a_minimal_v1')
humble_brag/json_repair.py (JSON 提取与格式修复容错)
humble_brag/runner.py (新增 LLM 运行支路、异常保底 fallback 逻辑与 trace 日志生成)
scripts/format_checker.py
scripts/evaluate_dev.py
```

已验证运行：

| 运行后端 | 运行模式 | 输出目录 | 格式检查 | 代理分数 | Fallback 率 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| Heuristic | dev 3 条 | `outputs/dev__20260521_085839_388__heuristic_baseline__max3` | valid, 0 error | 49.565 | 0.0% (0/3) | 启发式纯规则基准 |
| LLM (glm4:9b) | dev 3 条 | `outputs/dev__20260521_085904_879__llm_glm4_9b__max3` | valid, 0 error | 17.033 | 0.0% (0/3) | 0 故障，首次连通 LLM |
| LLM (glm4:9b) | dev 10 条 | `outputs/dev__20260521_090014_396__llm_glm4_9b__max10` | valid, 0 error | 29.116 | 0.0% (0/10) | 0 故障，逻辑与字段完全正常 |
| LLM (glm4:9b) | test 3 条 | `outputs/test__20260521_090039_047__llm_glm4_9b__max3` | valid, 0 error | not run | 0.0% (0/3) | 测试模式输出格式正确 |
| LLM (glm4:9b) | dev full 45 条 | `outputs/dev__20260521_090526_358__llm_glm4_9b__full` | valid, 0 error | 35.983 | 0.0% (0/45) | 核心闭环全量通过，无一例 fallback |

full dev (LLM) 指标：

| 指标 | 数值 |
| --- | --- |
| proxy_dev_score | 35.983 |
| mechanism_accuracy | 0.2667 |
| strategy_score | 0.4444 |
| risk_label_f1 | 0.0481 |
| response_reference_token_f1 | 0.2087 |

结论：Phase 1 & 2 的目标是在不破坏 heuristic baseline 且不引入复杂检索的前提下，打通最小的 LLM 运行链路并提供 per-sample debug trace。目前已达成，0 fallback 数据体现出解析器与后处理契约极佳的鲁棒性。接下来先验证 Phase 2.1 的 prompt 校准效果，再决定是否进入 Phase 3 多步骤 SkillFlow。

### 2.6 Phase 2.1 Prompt 校准与后处理增强已实现并完成验证

根据 `outputs/dev__20260521_090526_358__llm_glm4_9b__full/debug/trace.jsonl` 和 full dev 指标，当前 LLM backend 的主要问题不是工程链路，而是模型行为：

- `response_strategy` 过度集中在 `light_acknowledgment`。
- `risk_assessment` 自然但缺少 evaluator 可识别的风险标签短语。
- `response_text` 在 `stay_neutral` / `avoid_sycophancy` 场景中出现过度夸奖。

已完成代码层改动：

```text
humble_brag/prompts.py
- 保留 llm_a_minimal_v1
- 新增 llm_b_label_definition_v1
- 新增 mechanism / strategy 标签定义
- 新增 strategy selection rules
- 新增 risk assessment 风险标签要求

humble_brag/runner.py
- 新增 --prompt-version 参数
- LLM backend 根据 prompt_version 选择 prompt
- trace 和 RES.md 继续记录实际 prompt_version

humble_brag/contract.py
- 扩展 overpraise 过滤词
- 对 neutral_observation / stay_neutral / avoid_sycophancy 做更强反夸奖处理
- 当 risk_assessment 缺少风险标签式短语时，按策略做通用风险补强
```

已运行验证命令：

```bash
python3 main.py --mode dev --backend heuristic --max-items 3
python3 main.py --mode dev --backend llm --prompt-version llm_a_minimal_v1 --max-items 3
python3 main.py --mode dev --backend llm --prompt-version llm_b_label_definition_v1 --max-items 10
python3 main.py --mode dev --backend llm --prompt-version llm_b_label_definition_v1
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py
```

实际运行结果：

| 运行后端 | 运行模式 | 输出目录 | 格式检查 | 代理分数 | Fallback |
| --- | --- | --- | --- | --- | --- |
| Heuristic | dev 3 条 | `outputs/dev__20260521_093306_421__heuristic_baseline__max3` | valid, 0 error | 49.565 | 0 |
| LLM v1 | dev 3 条 | `outputs/dev__20260521_093726_803__llm_glm4_9b__max3` | valid, 0 error | 42.255 | 1 |
| LLM v2 | dev 10 条 | `outputs/dev__20260521_093848_197__llm_glm4_9b__max10` | valid, 0 error | 47.003 | 0 |
| LLM v2 | dev full 45 条 | `outputs/dev__20260521_094338_443__llm_glm4_9b__full` | valid, 0 error | 45.971 | 1 |

full dev 对比：

| 指标 | Phase 2 LLM v1 | Phase 2.1 LLM v2 | 变化 |
| --- | ---: | ---: | ---: |
| proxy_dev_score | 35.983 | 45.971 | +9.988 |
| mechanism_accuracy | 0.2667 | 0.3778 | +0.1111 |
| strategy_score | 0.4444 | 0.5889 | +0.1445 |
| risk_label_f1 | 0.0481 | 0.2667 | +0.2186 |
| response_reference_token_f1 | 0.2087 | 0.1684 | -0.0403 |

LLM v2 full dev 策略分布：

```text
neutral_observation: 19
light_acknowledgment: 20
humor_tease: 5
redirect: 1
```

补充观察：

- 首次未升级权限运行时，LLM 调用被 sandbox 本地网络限制拦截，出现 100% fallback；升级权限后真实调用本地 `glm4:9b` 成功。
- v2 已明显缓解 `light_acknowledgment` 塌缩问题，策略分布更健康。
- v2 full dev 的 `risk_label_f1` 明显高于 v1，但仍低于 heuristic baseline。
- v2 full dev 分数高于 Phase 2 LLM v1，但仍低于 heuristic baseline 的 49.223。

### 2.7 Phase 2.2 Static Memory Prompt Integration 已实现并完成验证

已新增固定任务知识模块：

```text
humble_brag/static_memory.py
- STATIC_MEMORY_VERSION = "STATIC_MEMORY_V1"
- STATIC_MEMORY_V1 包含固定任务知识：
  - strategy selection principles
  - risk label guidance
  - anti-sycophancy rules
  - mechanism 判断原则
  - platform / relationship style rules
```

已完成代码层改动：

```text
humble_brag/prompts.py
- 新增 llm_c_static_memory_v1
- 新增 build_static_memory_prompt_v1
- build_prompt 支持 static memory prompt
- 保留 llm_a_minimal_v1 和 llm_b_label_definition_v1

humble_brag/runner.py
- 根据 prompt_version 设置 memory_version
- trace.jsonl 每条记录 memory_version
- run_manifest.json 记录 memory_version
- RES.md Summary 记录 memory_version
```

本阶段没有引入 dynamic retrieval、RAG、few-shot、`data/Bragging_data.json` 检索或 dev gold 推理规则。

已运行验证命令：

```bash
python3 main.py --mode dev --backend heuristic --max-items 3
python3 main.py --mode dev --backend llm --prompt-version llm_b_label_definition_v1 --max-items 3
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1 --max-items 10
python3 main.py --mode dev --backend llm --prompt-version llm_c_static_memory_v1
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py
```

实际运行结果：

| 运行后端 | 运行模式 | 输出目录 | 格式检查 | 代理分数 | Fallback |
| --- | --- | --- | --- | --- | --- |
| Heuristic | dev 3 条 | `outputs/dev__20260521_102959_688__heuristic_baseline__max3` | valid, 0 error | 49.565 | 0 |
| LLM v2 | dev 3 条 | `outputs/dev__20260521_103200_974__llm_glm4_9b__max3` | valid, 0 error | 36.031 | 0 |
| LLM v3 static memory | dev 10 条 | `outputs/dev__20260521_103344_882__llm_glm4_9b__max10` | valid, 0 error | 58.004 | 0 |
| LLM v3 static memory | dev full 45 条 | `outputs/dev__20260521_103942_363__llm_glm4_9b__full` | valid, 0 error | 50.881 | 0 |

full dev 对比：

| 指标 | Heuristic | LLM v2 | LLM v3 Static Memory |
| --- | ---: | ---: | ---: |
| proxy_dev_score | 49.223 | 45.971 | 50.881 |
| mechanism_accuracy | 0.2667 | 0.3778 | 0.4222 |
| strategy_score | 0.6333 | 0.5889 | 0.5889 |
| risk_label_f1 | 0.5785 | 0.2667 | 0.4600 |
| response_reference_token_f1 | 0.1324 | 0.1684 | 0.1491 |

LLM v3 full dev 策略分布：

```text
neutral_observation: 31
light_acknowledgment: 9
humor_tease: 5
```

补充观察：

- `llm_c_static_memory_v1` full dev 0 fallback、0 parse failure、0 invalid label。
- `debug/trace.jsonl` 45 条均记录 `memory_version = STATIC_MEMORY_V1`。
- `RES.md` Summary 正确记录 `memory_version`。
- 过度夸奖词命中数为 0。
- static memory 已超过 heuristic full dev，但这仍是 public dev proxy，需要继续做 hidden-test 泛化风险控制。

## 3. 现有代码状态

根目录现有代码主要是早期 Meta-String RAG 原型：

- `schema.py`：定义通用社交平台、关系、角色、互动目标等枚举和 `SocialContext`
- `rag.py`：基于 Meta-String + FAISS 的检索原型
- `data/Bragging_data.json`：当前数据文件

这些代码有参考价值，但还不是最终比赛 pipeline。主要问题：

1. schema 还偏通用社交助手，不完全对齐 BRAG 官方 7 字段输出。
2. RAG 原型没有接入完整生成、校验、评测、输出链路。
3. 当前文档中过去关于高分目标的表述需要降级为工程假设，不能当作已验证结论。
4. 需要先建立官方格式检查和 dev 评分闭环，再做复杂增强。

## 4. reference 中可复用内容

旧项目中较有价值的部分：

| 模块 | 可复用方式 |
| --- | --- |
| `reference/src/skillflow.py` | 后续可参考固定 SkillFlow 调度方式 |
| `reference/src/skills/` | 可参考机制、风险、策略、回复拆分 |
| `reference/src/llm_client.py` | 可参考 Ollama qwen 原生 `/api/chat` 适配 |
| `reference/src/postprocess.py` | 可参考输出清理和标签归一化 |
| `reference/BRAG-Agent-public/scripts/` | 可直接作为官方格式检查和 dev 评分来源 |
| `reference/PROJECT_OVERVIEW_REPORT.md` | 可查看旧实验指标和阶段记录 |

不建议直接搬运的部分：

- 旧目录里的整体工程结构
- 旧实验输出
- 没有完整 ablation 的 memory 规则
- 过度乐观的分数目标和未验证策略

## 5. 下一步重点

Phase 0、Phase 1、Phase 2、Phase 2.1、Phase 2.2 已完成。

下一步工作重心：

1. 基于 `outputs/dev__20260521_103942_363__llm_glm4_9b__full/debug/trace.jsonl` 做错误分析。
2. 重点分析 strategy_score 仍低于 heuristic 的原因。
3. 不直接上 dynamic RAG / few-shot；static memory 已有效，下一步若继续增强，应进入 Phase 3 SkillFlow。
4. 保留 heuristic 作为 fallback，`llm_c_static_memory_v1` 可作为当前最佳 LLM 分支。
5. 在继续调高 public dev 前，需要做过拟合风险检查和 stress cases。

## 6. 风险

- 当前 `data/Bragging_data.json` 与官方 JSONL 输入格式已确认不一致，不能直接作为 submission 输入。
- 如果先上复杂 RAG/memory，容易在 schema 未稳定时返工。
- 3 条 smoke score 或小样本 ablation 只能说明链路可跑，不能证明 hidden test 泛化。
- `reference/` 是归档，不应该被当作主线代码直接执行。
- 当前 baseline 只是低成本工程基线，proxy score 不高是预期结果。

## 7. 当前推荐结论

继续在当前新仓库做，但开发顺序必须是：

```text
official contract first
-> runnable baseline
-> trace and reports
-> prompt calibration / contract postprocess
-> SkillFlow
-> retrieval / memory
-> final freeze
```

当前 trace 已补齐，Phase 2.2 static memory 已验证且超过 heuristic public dev proxy。下一步应基于 trace 做错误分析和过拟合风险检查，再决定是否进入 SkillFlow。
