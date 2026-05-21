# 实施任务清单

更新时间：2026-05-21

## 总原则

本项目后续按“先框架、再增强”的方式推进。任何新功能都必须满足：

- 能单独开启或关闭
- 有明确验证命令
- 不破坏官方输出格式
- 有可比较的 baseline
- 实验结论写回文档

## Phase 0：仓库和数据盘点 (已完成 - 2026-05-21)

目标：确认当前仓库真实输入、输出和评测契约。

任务：

- [x] 1. 读取 `data/Bragging_data.json`，整理字段列表、样本数量和示例。
- [x] 2. 从 `reference/BRAG-Agent-public/` 中确认官方输入字段、输出 7 字段、合法标签和评测脚本调用方式。
- [x] 3. 写出本仓库专用的输入 schema 和输出 schema 说明（写入 `PROJECT_CONTRACT_AUDIT.md`）。
- [x] 4. 确认是否需要把官方 `format_checker.py`、`evaluate_dev.py` 提升到根目录脚本区。

验收标准：

- [x] 文档中列出输入字段和输出字段。
- [x] 能说明当前数据与官方 JSONL 数据是否一致。
- [x] 后续 pipeline 不再依赖猜测字段。

## Phase 1：最小可运行 Baseline (已完成 - 2026-05-21)

目标：先跑通完整链路，不追求高分。

任务：

- [x] 1. 实现数据加载器。
- [x] 2. 实现最小 baseline 生成器。
- [x] 3. 实现输出 JSONL 写入。
- [x] 4. 实现 schema validator / postprocess。
- [x] 5. 接入 format checker。
- [x] 6. dev 模式下接入 evaluator。

验收标准：

- [x] 可以生成 `submission.jsonl`。
- [x] 格式检查 0 error。
- [x] 每次运行保存：
  - `submission.jsonl`
  - `input_subset.jsonl`
  - `run_manifest.json`
  - `format_report.json`
  - `dev_eval_report.json`，如果有 gold
  - `RES.md`

完成记录：

| 运行 | 输出目录 | 格式检查 | 代理分数 |
| --- | --- | --- | --- |
| dev 3 条 smoke | `outputs/dev__20260521_004330_043__heuristic_baseline__max3` | valid, 0 warning | 49.565 |
| dev full 45 条 | `outputs/dev__20260521_004340_237__heuristic_baseline__full` | valid, 0 warning | 49.223 |
| test 3 条 smoke | `outputs/test__20260521_004154_200__heuristic_baseline__max3` | valid, 0 warning | not run |

## Phase 2：可调试日志 & Minimal LLM Pipeline (已完成 - 2026-05-21)

目标：接入 Minimal LLM backend，并让每条样本为什么这样输出可以追踪。

任务：

- [x] 1. 接入 LLM backend，并支持 `--backend heuristic|llm` 选择。
- [x] 2. 每条样本保存 trace。
- [x] 3. trace 至少包含输入、模型输出、解析结果、fallback 原因和最终输出。
- [x] 4. 实现 JSON extract & repair 容错，并支持 API 失败 / 解析失败时 fallback 到 Heuristic Baseline。
- [x] 5. 每次运行生成 `RES.md` 指标报告和 `debug/trace.jsonl` 调试文件。

验收标准：

- [x] 任意一条输出都能回查中间过程。
- [x] 失败、fallback、修复动作都有记录。
- [x] 格式检查 0 error，且能正常输出 dev evaluator 分数。

完成记录：

| 运行模式与后端 | 输出目录 | 格式检查 | 代理分数 | 备注 |
| --- | --- | --- | --- | --- |
| dev 3 条 (heuristic) | `outputs/dev__20260521_085839_388__heuristic_baseline__max3` | valid, 0 error | 49.565 | Heuristic 基线保持完好 |
| dev 3 条 (LLM) | `outputs/dev__20260521_085904_879__llm_glm4_9b__max3` | valid, 0 error | 17.033 | 0 fallback, 首次联通 LLM 管道 |
| dev 10 条 (LLM) | `outputs/dev__20260521_090014_396__llm_glm4_9b__max10` | valid, 0 error | 29.116 | 0 fallback, 逻辑和解析均正常 |
| test 3 条 (LLM) | `outputs/test__20260521_090039_047__llm_glm4_9b__max3` | valid, 0 error | not run | 测试模式正常生成 |
| dev full 45 条 (LLM) | `outputs/dev__20260521_090526_358__llm_glm4_9b__full` | valid, 0 error | 35.983 | 0 fallback, 核心闭环全量通过 |

## Phase 2.1：LLM Prompt Calibration & Contract Postprocess (已完成 - 2026-05-21)

目标：在不引入 RAG / memory / few-shot 的前提下，对 Phase 2 的 LLM backend 做小范围校准，重点修复 strategy 塌缩、risk 标签未命中和过度夸奖问题。

任务：

- [x] 1. 保留 `heuristic` backend 和 `llm_a_minimal_v1`。
- [x] 2. 新增 prompt version：`llm_b_label_definition_v1`。
- [x] 3. 新增 CLI 参数 `--prompt-version`，默认 `llm_a_minimal_v1`。
- [x] 4. 在 prompt v2 中加入 mechanism / strategy 标签定义。
- [x] 5. 在 prompt v2 中加入基于 `interaction_goal`、`relationship`、`platform` 的策略选择规则。
- [x] 6. 要求 `risk_assessment` 显式包含风险标签式短语。
- [x] 7. 增强 `contract.py` 的 overpraise 过滤，覆盖 `impressive`、`impressed`、`great`、`awesome`、`congrats`、`well done` 等表达。
- [x] 8. 当 `risk_assessment` 未包含可识别风险短语时，按策略做通用风险补强。
- [x] 9. 运行 smoke / full dev 验证，并记录输出目录与核心指标。

待运行验收命令：

```bash
python3 main.py --mode dev --backend heuristic --max-items 3
python3 main.py --mode dev --backend llm --prompt-version llm_a_minimal_v1 --max-items 3
python3 main.py --mode dev --backend llm --prompt-version llm_b_label_definition_v1 --max-items 10
python3 main.py --mode dev --backend llm --prompt-version llm_b_label_definition_v1
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py
```

验收标准：

- [x] `heuristic` backend 仍可运行。
- [x] `llm_a_minimal_v1` 仍可运行。
- [x] `llm_b_label_definition_v1` 可通过 CLI 选择。
- [x] format checker 通过。
- [x] trace 正确记录 `prompt_version`、raw output、parsed output 和 normalized output。
- [x] strategy 分布不再极端集中在 `light_acknowledgment`。
- [x] `risk_label_f1` 明显高于 0.0481。
- [x] `strategy_score` 不低于 0.4444。
- [x] proxy dev score 高于 35.983。

完成记录：

| 运行模式与后端 | 输出目录 | 格式检查 | 代理分数 | 备注 |
| --- | --- | --- | --- | --- |
| dev 3 条 (heuristic) | `outputs/dev__20260521_093306_421__heuristic_baseline__max3` | valid, 0 error | 49.565 | Heuristic smoke 正常 |
| dev 3 条 (LLM v1) | `outputs/dev__20260521_093726_803__llm_glm4_9b__max3` | valid, 0 error | 42.255 | 真实 LLM 调用，1 fallback |
| dev 10 条 (LLM v2) | `outputs/dev__20260521_093848_197__llm_glm4_9b__max10` | valid, 0 error | 47.003 | 0 fallback，v2 可运行 |
| dev full 45 条 (LLM v2) | `outputs/dev__20260521_094338_443__llm_glm4_9b__full` | valid, 0 error | 45.971 | 1 fallback，strategy 塌缩缓解 |

full dev (LLM v2) 指标：

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

## Phase 2.2：Static Memory Prompt Integration (已完成 - 2026-05-21)

目标：在不引入 dynamic retrieval / RAG / few-shot 的前提下，新增固定任务知识块，测试 static memory 是否能继续提升 LLM 稳定性。

任务：

- [x] 1. 保留 `heuristic` backend。
- [x] 2. 保留 `llm_a_minimal_v1`。
- [x] 3. 保留 `llm_b_label_definition_v1`。
- [x] 4. 新增 prompt version：`llm_c_static_memory_v1`。
- [x] 5. 新增 `humble_brag/static_memory.py`，包含 `STATIC_MEMORY_VERSION` 和 `STATIC_MEMORY_V1`。
- [x] 6. static memory 只包含固定任务知识，不包含 few-shot、动态检索或 dev gold。
- [x] 7. `trace.jsonl` 每条记录 `memory_version`。
- [x] 8. `run_manifest.json` 记录 `memory_version`。
- [x] 9. `RES.md` Summary 记录 `memory_version`。
- [x] 10. 运行 smoke / full dev 验证，并记录输出目录与核心指标。

完成记录：

| 运行模式与后端 | 输出目录 | 格式检查 | 代理分数 | 备注 |
| --- | --- | --- | --- | --- |
| dev 3 条 (heuristic) | `outputs/dev__20260521_102959_688__heuristic_baseline__max3` | valid, 0 error | 49.565 | Heuristic smoke 正常 |
| dev 3 条 (LLM v2) | `outputs/dev__20260521_103200_974__llm_glm4_9b__max3` | valid, 0 error | 36.031 | 0 fallback，memory_version 为 n/a |
| dev 10 条 (LLM v3 static memory) | `outputs/dev__20260521_103344_882__llm_glm4_9b__max10` | valid, 0 error | 58.004 | 0 fallback，`STATIC_MEMORY_V1` |
| dev full 45 条 (LLM v3 static memory) | `outputs/dev__20260521_103942_363__llm_glm4_9b__full` | valid, 0 error | 50.881 | 0 fallback，超过 heuristic full dev |

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

观察：

- `llm_c_static_memory_v1` full dev 0 fallback、0 parse failure、0 invalid label。
- `trace.jsonl` 45 条均记录 `memory_version = STATIC_MEMORY_V1`。
- 过度夸奖词命中数为 0。
- static memory 明显提升 mechanism 和 risk，但 strategy_score 仍低于 heuristic。

## Phase 3：SkillFlow

目标：把任务拆成稳定模块，而不是一次性大 prompt。

建议顺序：

```text
mechanism
-> intent / desired feedback
-> risk
-> strategy
-> response
-> validator / rewriter
```

验收标准：

- SkillFlow 能与 baseline 用同一套数据和评测命令对比。
- 至少完整跑一次 dev。
- 对比表必须包含 proxy score、mechanism、strategy、risk、response。

## Phase 4：Few-shot / Meta-String Retrieval

目标：在框架稳定后，再启用检索增强。

任务：

1. 保留 Meta-String 思路，但先验证字段对齐。
2. 检索不能只看 post 文本，要包含 platform、relationship、agent role、interaction goal。
3. 只把 few-shot 注入最需要的模块，避免 prompt 过长。
4. 做开关消融：`no_fewshot` vs `fewshot`。

验收标准：

- 完整 dev 不明显伤害核心指标。
- 有消融表。
- 有失败样本分析。

## Phase 5：Memory 和 Local Judge

目标：只有在 baseline、SkillFlow、few-shot 都可比较后，再加入 memory。

任务：

1. 建立 active / candidate / deprecated 三类 memory。
2. candidate memory 必须经过人工或 local judge 评审。
3. active memory 必须能禁用。
4. 做 ablation，避免把 public dev 样本硬记成规则。

验收标准：

- 有 memory 使用记录。
- 有 no-memory vs active-memory 对比。
- 有过拟合风险说明。

## Phase 6：Candidate Freeze and Submission Readiness (已完成 - 2026-05-21)

目标：停止继续堆复杂功能，把当前最强候选整理成可复现、可解释、可提交前审计的稳定版本。

任务：

- [x] 1. 创建 `FINAL_CANDIDATE_FREEZE.md`，冻结最终候选配置。
- [x] 2. 创建 `OVERFIT_RISK_AUDIT.md`，检查 dev gold、episode_id 规则、candidate memory、test mode 依赖等风险。
- [x] 3. 创建 `TRACE_SANITY_REPORT.md`，审计最佳 run 的 SkillFlow trace。
- [x] 4. 创建 `FINAL_READINESS_REPORT.md`，汇总 dev ablation、test dry run 和提交建议。
- [x] 5. 运行 compileall 编译检查。
- [x] 6. 运行 dev ablation：heuristic、static memory prompt、SkillFlow no-memory、SkillFlow active-memory。
- [x] 7. 按用户要求只做 45 条 test dry run，不生成完整 409 条 test submission。

完成记录：

| Run | 输出目录 | 关键配置 | 格式 | 代理分数 |
| --- | --- | --- | --- | ---: |
| Heuristic reference | `outputs/dev__20260521_194048_706__heuristic_baseline__full` | heuristic | valid | 49.223 |
| Static memory prompt | `outputs/dev__20260521_200217_548__llm_glm4_9b__full` | `llm_c_static_memory_v1` | valid | 49.573 |
| SkillFlow no memory | `outputs/dev__20260521_201215_813__llm_glm4_9b_skillflow__full` | `--use-skillflow --memory-mode no_memory` | valid | 68.111 |
| SkillFlow active memory | `outputs/dev__20260521_212356_012__llm_glm4_9b_skillflow__full` | `--use-skillflow --use-agent-memory --memory-mode active` | valid | 68.100 |
| Frozen source run | `outputs/dev__20260521_190335_066__llm_glm4_9b_skillflow__full` | `--use-skillflow --use-fewshot --use-agent-memory --memory-mode active` | valid | 68.780 |

Test dry run：

| Run | 输出目录 | 配置 | 格式 | 行数 |
| --- | --- | --- | --- | ---: |
| no-fewshot test dry run | `outputs/test__20260521_213329_881__llm_glm4_9b_skillflow__max45` | active memory, no few-shot | valid | 45 |
| frozen-candidate test dry run | `outputs/test__20260521_214225_439__llm_glm4_9b_skillflow__max45` | active memory + few-shot | valid | 45 |

Phase 6 结论：

- 当前最强候选是 `skillflow_v1_fewshot_active_empty_memory`。
- 最强 run 的 active memory 实际为空，`memory_used_count=0`。
- candidate memory 仍处于 candidate 状态，不允许进入 final chain。
- 因为最强 run 使用 few-shot，而本轮 no-fewshot ablation 分数略低，最终完整 test submission 前建议再做一次 few-shot full dev 复现。

### Phase 6.1：Frozen Candidate Dev/Test 45 Validation (已完成 - 2026-05-21)

本轮只执行最终候选配置的 45 条验证，不修改核心代码，不 promote candidate memory，不跑完整 409 条 test。

执行命令：

```bash
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py

OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode dev --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active

OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=glm4:9b \
python3 main.py --mode test --backend llm --use-skillflow --use-fewshot --use-agent-memory --memory-mode active --max-items 45
```

完成记录：

| Run | 输出目录 | 格式 | Fallback | Memory used | 代理分数 |
| --- | --- | --- | ---: | ---: | ---: |
| frozen dev-45 | `outputs/dev__20260521_221741_731__llm_glm4_9b_skillflow__full` | valid | 0 | 0 | 69.007 |
| frozen test-45 | `outputs/test__20260521_222905_096__llm_glm4_9b_skillflow__max45` | valid | 0 | 0 | not run |

补充说明：

- active memory path 启用，但 active memory 为空，`memory_used_count=0`。
- candidate memory 没有 promote，也没有进入 `memory_mode=active` 推理链。
- 本轮 dev 后离线 error analysis 追加了 candidate memory 条目，但这些条目仍为 candidate 状态。
- 当前电脑资源限制下，完整 409 条 test 留到最终提交前再跑。
