# BRAG-Pipeline

BRAG-Pipeline 是一个面向社交语境理解与回复生成的受控 Agent 流程。系统识别隐含表达机制，推断说话者意图，选择回复策略，评估社交风险，并生成符合场景约束的短回复。

项目包含完整的数据读取、SkillFlow、结构化 Memory、few-shot 检索、格式检查、dev 评分、错误分析和 test 提交生成能力。

## 目录

```text
BRAG-Pipeline_new/
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
OPENAI_BASE_URL=https://your-api.example.com/v1
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=your-model-name
```

模型名只在 `.env` 中设置，不需要修改代码。

## 常用配置

打开 `config.py`，顶部为日常需要修改的选项：

```python
RUN_MODE = "smoke"  # smoke / dev / test

USE_MEMORY = True
USE_FEWSHOT = True
FEWSHOT_RETRIEVAL_MODE = "jaccard"  # jaccard / embedding / hybrid

RUN_ERROR_ANALYSIS = True
SAVE_ERROR_MEMORY = False
USE_GENERATED_MEMORY = False
```

- `RUN_MODE`：选择冒烟测试、完整 dev 或最终 test。
- `USE_MEMORY`：加载 `memory/memory.jsonl`。
- `USE_FEWSHOT`：从 `data/train.jsonl` 检索回复示例。
- `FEWSHOT_RETRIEVAL_MODE`：选择 Jaccard、embedding 或混合检索。
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

先在 `.env` 中设置最终模型：

```env
OPENAI_MODEL=Qwen/Qwen3-14B
```

然后在 `config.py` 中设置：

```python
RUN_MODE = "test"
```

执行：

```bash
python main.py
```

流程读取全部 409 条 test，执行格式检查，不运行 dev 评分和错误分析。可提交文件为：

```text
outputs/<run_id>/submission.jsonl
```

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

详细设计与模型对比见 [技术报告.md](技术报告.md)。

## Memory 与 Few-shot

`memory/memory.jsonl` 内置 48 条结构化记忆，分为：

- `mechanism_rule`
- `confusion_rule`
- `strategy_policy`
- `scenario_policy`
- `risk_pattern`
- `response_style_card`
- `anti_pattern`

每条记忆包含目标 Skill、目标标签、正负条件、置信度和优先级。检索时先执行类型、标签和条件过滤，再计算相关性。

Few-shot 使用 500 条 train 数据。当前默认仅为 `ResponseSkill` 检索 2 个示例；机制和策略不使用近邻投票，避免训练集近邻噪声覆盖分类规则和策略矩阵。

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
