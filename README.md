# BRAG-Pipeline

BRAG-Pipeline 是一个面向社交语境理解与回复生成的受控 Agent 流程。系统识别隐含表达机制，推断说话者意图，选择回复策略，评估社交风险，并生成符合场景约束的短回复。

项目包含完整的数据读取、SkillFlow、结构化 Memory、few-shot 检索、格式检查、dev 评分、错误分析和 test 提交生成能力。

## 目录

```text
BRAG-Pipeline/
├── data/                 # train、dev 和 test 数据
├── docs/                 # 数据集与标签说明
├── memory/
│   └── memory.jsonl      # 内置结构化记忆
├── scripts/              # 格式检查和 dev 评分脚本
├── src/                  # Pipeline、Skills、检索和后处理
├── tests/                # 离线单元测试
├── outputs/              # 运行结果，不提交到 Git
├── config.py             # 运行模式和功能配置
├── main.py               # 唯一启动入口
├── 技术报告.md
└── requirements.txt
```

## 安装

建议使用 Python 3.10 或更高版本。

```bash
pip install -r requirements.txt
```

复制 `.env.example` 为 `.env`，填写兼容 OpenAI 接口的服务信息：

```env
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=gemma3:12b
```

模型名只在 `.env` 中设置，不需要修改代码。

## 常用配置

打开 `config.py`，顶部为日常需要修改的选项：

```python
RUN_MODE = "smoke"  # smoke / dev / test

USE_MEMORY = True
USE_FEWSHOT = True
FEWSHOT_RETRIEVAL_MODE = "jaccard"  # jaccard / embedding / hybrid
MEMORY_ROUTER_MODE = "llm_rerank"   # baseline / function / llm_rerank
USE_RESPONSE_CANDIDATE_RERANK = False
USE_UNDERSTANDING_TEMPLATE_REPAIR = True

RUN_ERROR_ANALYSIS = True
SAVE_ERROR_MEMORY = False
USE_GENERATED_MEMORY = False
```

- `RUN_MODE`：选择冒烟测试、完整 dev 或最终 test。
- `USE_MEMORY`：加载 `memory/memory.jsonl`。
- `USE_FEWSHOT`：从 `data/train.jsonl` 检索回复示例。
- `FEWSHOT_RETRIEVAL_MODE`：选择 Jaccard、embedding 或混合检索。
- `MEMORY_ROUTER_MODE`：选择 Memory 注入方式。当前默认使用 `llm_rerank`，先用函数式路由收窄候选，再让 LLM 只从候选 memory ID 中重排选择。
- `USE_RESPONSE_CANDIDATE_RERANK`：实验性 Response 多候选重排。离线对照未超过当前最佳 dev 分数，因此默认关闭。
- `USE_UNDERSTANDING_TEMPLATE_REPAIR`：对开放文本理解字段做轻量模板修复。当前默认只修 `desired_feedback`，保留 LLM 的 `speaker_intention`。
- `RUN_ERROR_ANALYSIS`：完整 dev 后生成错误分析。
- `SAVE_ERROR_MEMORY`：把错误分析候选写入 `memory/generated.jsonl`。
- `USE_GENERATED_MEMORY`：推理时加载人工确认后的生成记忆。

默认使用 Jaccard。该模式无需额外服务，且在当前完整 dev 对照中表现稳定。

需要测试 embedding 时，可在 `.env` 增加：

```env
FEWSHOT_EMBEDDING_BASE_URL=
FEWSHOT_EMBEDDING_API_KEY=
FEWSHOT_EMBEDDING_MODEL=
```

地址和 Key 留空时复用主 API 配置。embedding 模型留空时会尝试复用 `OPENAI_MODEL`；若服务不支持 embeddings，系统会输出警告并自动切换到 Jaccard。

## 三种运行方式

三种模式都使用同一个命令：

```bash
python main.py
```

### 冒烟测试

在 `config.py` 中设置：

```python
RUN_MODE = "smoke"
```

读取 dev 前 3 条，执行完整 SkillFlow、格式检查和代理评分，不执行错误分析。建议首次配置 API 或更换模型后先运行此模式。

### 完整 Dev

在 `config.py` 中设置：

```python
RUN_MODE = "dev"
```

读取全部 45 条 dev，执行格式检查、代理评分和结果记录。启用 `RUN_ERROR_ANALYSIS` 后还会生成错误分析。

### 最终 Test

先在 `.env` 中设置最终模型。当前本地验证使用：

```env
OPENAI_MODEL=gemma3:12b
```

推荐使用最终 test 专用入口，脚本会临时应用当前推荐配置，不需要手动改 `config.py`：

```bash
python scripts/run_final_test.py --dry-run
```

执行：

```bash
python scripts/run_final_test.py
```

流程读取全部 409 条 test，执行格式检查，不运行 dev 评分和错误分析。可提交文件为：

```text
outputs/<run_id>/submission.jsonl
```

### Nvidia 机器运行完整 Test

给外部机器或同学跑完整 409 条 test 时，直接使用最终 test 入口：

```bash
python scripts/run_final_test.py --dry-run
python scripts/run_final_test.py
```

Nvidia/Ollama 环境说明见 [docs/RUN_FULL_TEST_NVIDIA.md](docs/RUN_FULL_TEST_NVIDIA.md)。

## 运行流程

```text
输入校验
  ↓
MechanismSkill：模型分类、规则校准、条件复核和结果缓存
  ↓
UnderstandingSkill：推断意图与期望反馈
  ↓
StrategySkill：使用场景策略矩阵确定回复策略
  ↓
RiskSkill：生成精简风险标签与评估
  ↓
ResponseSkill：结合 Memory 和 response few-shot 生成回复
  ↓
ResponseRiskReviewSkill：检查过誉、说教、语气和策略一致性
  ↓
ValidatorSkill：校验七字段输出
  ↓
RewriterSkill：仅在首次校验失败时修复
```

机制分类只读取 `speaker_post`，避免场景字段改变原文语义。策略和风险采用确定性规则，语言理解与回复表达由模型完成。每个样本都会保存可追踪的 Skill 执行记录。

详细设计与当前结果见 [技术报告.md](技术报告.md)。

## Memory 与 Few-shot

`memory/memory.jsonl` 内置 48 条结构化记忆，分为：

- `mechanism_rule`
- `confusion_rule`
- `strategy_policy`
- `scenario_policy`
- `risk_pattern`
- `response_style_card`
- `anti_pattern`

每条记忆包含目标 Skill、目标标签、正负条件、置信度、优先级和状态。检索时先跳过非 active/approved 的候选，再执行类型、标签和条件过滤。

当前默认的函数式动态路由只影响 `ResponseSkill`：

- `scenario_policy`、`strategy_policy`、`response_style_card` 必须兼容当前 `response_strategy`。
- `anti_pattern` 只在条件命中当前策略、机制、关系或风险语境时注入。
- `MechanismSkill` 保守使用机制知识卡，不按预测机制做硬过滤，避免自我确认错误。

Few-shot 使用 500 条 train 数据。当前默认仅为 `ResponseSkill` 检索 2 个示例；机制和策略不使用近邻投票，避免训练集近邻噪声覆盖分类规则和策略矩阵。

`RiskSkill` 会额外生成内部 `risk_control_plan`，供 `ResponseSkill` 控制语气和 Bloom 风险。该字段不会写入最终 `submission.jsonl`，最终提交仍只有七个规定字段。

`UnderstandingSkill` 使用 LLM 生成意图与期望反馈后，会在策略确定后用动态主题模板修复 `desired_feedback`。当前最佳完整 dev 中，`desired_feedback` token F1 达到 `0.2372`，同时避免早期固定模板过度重复。

## 当前结果

当前有效完整 dev 结果来自 Gemma3 12B、45 条公开 dev：

| 运行 | Memory 路由 | 代理总分 | 机制准确率 | 策略得分 | 风险 F1 | 回复 F1 |
|---|---|---:|---:|---:|---:|---:|
| `dev_20260622_001031_gemma3_12b` | function | 79.733 | 0.9778 | 0.8889 | 0.7237 | 0.2098 |
| `dev_20260622_040201_gemma3_12b` | llm_rerank | 79.465 | 0.9778 | 0.8889 | 0.7237 | 0.1920 |
| `dev_20260622_153413_gemma3_12b` | llm_rerank | 81.402 | 0.9778 | 0.9556 | 0.7548 | 0.1907 |
| `dev_20260622_220425_gemma3_12b` | llm_rerank | 81.775 | 0.9778 | 0.9556 | 0.7548 | 0.2156 |

结论：在加入最新 StrategySkill/RiskSkill 规则修正后，`llm_rerank` 的完整 dev 分数超过此前 function-router 最优结果，因此当前默认保留 `MEMORY_ROUTER_MODE = "llm_rerank"`。

最新本地规则改动进一步优化了 `StrategySkill` 首选策略选择和 `RiskSkill` false positive 控制；完整 45 条 LLM dev 已验证。

规划执行完成度记录在 `reports/md_plan_completion.md`，运行对比记录在 `reports/run_comparison.md`。

## 输出

每次运行生成独立目录：

```text
outputs/<run_id>/
├── submission.jsonl
├── RES.md
├── run_manifest.json
├── format_report.json
├── dev_eval_report.json      # smoke/dev
├── error_analysis/           # 完整 dev 且启用时
└── debug/
    ├── trace.jsonl
    ├── fewshot.jsonl
    └── input_subset.jsonl    # smoke
```

- `RES.md`：本次运行的主要指标和流程统计。
- `run_manifest.json`：模型、配置、检索模式、调用量和异常统计。
- `debug/trace.jsonl`：逐样本机制校准、Memory、策略和回复轨迹。
- `format_report.json`：提交格式检查结果。

数据字段和标签定义见：

- [中文数据集说明](docs/DATASET_CARD_CN.md)
- [中文标签说明](docs/LABEL_SCHEMA_CN.md)
- [English Dataset Card](docs/DATASET_CARD.md)
- [English Label Schema](docs/LABEL_SCHEMA.md)
