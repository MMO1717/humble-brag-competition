# PROJECT_AUDIT.md

## 1. 项目目录结构

| 路径 | 类型 | 作用 | 是否核心 | 后续是否需要修改 |
| -- | -- | -- | ---- | -------- |
| `main.py` | 入口 | 唯一启动入口，加载 .env 并调用 pipeline | ✅ | 不改 |
| `config.py` | 配置 | 运行模式、模型参数、功能开关、路径派生 | ✅ | Phase 1 需增加 run_manifest 配置 |
| `src/pipeline.py` | 核心 | 主流程编排：加载数据、运行 SkillFlow、评估、输出 | ✅ | Phase 1 需增加 trace/manifest 逻辑 |
| `src/skillflow.py` | 核心 | 固定顺序 SkillFlow 控制器 | ✅ | Phase 3 可能需扩展 |
| `src/skills/base.py` | 核心 | Skill 基类 | ✅ | 不改 |
| `src/skills/mechanism_skill.py` | 核心 | 机制分类 + 校准 + 复核 + 缓存 | ✅ | Phase 4 可能需调 prompt |
| `src/skills/understanding_skill.py` | 核心 | 意图和期望反馈推断 | ✅ | Phase 4 可能需调 prompt |
| `src/skills/strategy_skill.py` | 核心 | 策略选择（纯规则矩阵） | ✅ | Phase 4 可能需调规则 |
| `src/skills/risk_skill.py` | 核心 | 风险标签生成（纯规则） | ✅ | Phase 4 可能需调规则 |
| `src/skills/response_skill.py` | 核心 | 回复生成 + 兜底 + social rubric 审查 | ✅ | Phase 4/5 可能需调 prompt |
| `src/skills/response_risk_review_skill.py` | 核心 | 回复后风险复查 + 自动改写 | ✅ | Phase 7 可能需扩展 |
| `src/skills/validator_skill.py` | 核心 | 7 字段校验 | ✅ | Phase 7 可能需扩展 |
| `src/skills/rewriter_skill.py` | 核心 | 校验失败时重写 | ✅ | 不改 |
| `src/prompts.py` | 核心 | 所有 prompt 构建函数 | ✅ | Phase 4 需调 prompt |
| `src/postprocess.py` | 核心 | 解析、校准、清理、兜底模板 | ✅ | Phase 4 可能需调规则 |
| `src/strategy_rules.py` | 核心 | 确定性策略矩阵 | ✅ | Phase 4 可能需调规则 |
| `src/social_rubric.py` | 核心 | 轻量回复审查器 | ✅ | Phase 7 可能需扩展 |
| `src/schemas.py` | 核心 | 枚举、默认值、字数限制 | ✅ | 不改 |
| `src/validators.py` | 核心 | 输入/输出校验 | ✅ | Phase 7 可能需扩展 |
| `src/output_builder.py` | 核心 | 从 state 组装 7 字段输出 | ✅ | 不改 |
| `src/memory.py` | 核心 | Memory 加载、条件匹配、检索 | ✅ | Phase 6 可能需扩展 |
| `src/fewshot.py` | 核心 | Few-shot 检索（Jaccard / embedding / hybrid） | ✅ | Phase 5 可能需调参数 |
| `src/embedding_client.py` | 辅助 | embedding API 客户端 | ❌ | 不改 |
| `src/debug_logger.py` | 辅助 | 调试日志记录 | ✅ | Phase 1 需扩展 |
| `src/error_analyzer.py` | 辅助 | dev 错误分析 | ✅ | Phase 2 需扩展 |
| `src/io_utils.py` | 辅助 | JSONL 读写 | ❌ | 不改 |
| `scripts/format_checker.py` | 评估 | 官方格式检查 | ✅ | 不改 |
| `scripts/evaluate_dev.py` | 评估 | dev 代理评分 | ✅ | 不改 |
| `data/train.jsonl` | 数据 | 500 条训练数据 | ✅ | 不改 |
| `data/dev_input.jsonl` | 数据 | 45 条 dev 输入 | ✅ | 不改 |
| `data/dev_gold.jsonl` | 数据 | 45 条 dev 标注 | ✅ | 不改 |
| `data/test_input.jsonl` | 数据 | 409 条测试输入 | ✅ | 不改 |
| `memory/memory.jsonl` | 数据 | 48 条结构化记忆 | ✅ | Phase 6 可能需扩展 |
| `tests/test_pipeline.py` | 测试 | 28 个单元测试 | ✅ | 需扩展新功能测试 |
| `docs/` | 文档 | 数据集说明、标签定义 | ❌ | 不改 |
| `MEMORY/` | 文档 | 项目记忆（当前只有 `memory.jsonl`） | ❌ | 需创建 `shared_memory.md` |
| `技术报告.md` | 文档 | 系统技术报告 | ❌ | 不改 |
| `BRAG-Agent_内容与提示词.md` | 文档 | 比赛提示词参考 | ❌ | 不改 |
| `requirements.txt` | 配置 | 依赖：openai, python-dotenv | ✅ | 不改 |
| `.env.example` | 配置 | 环境变量模板 | ✅ | 不改 |
| `outputs/` | 输出 | 运行结果（gitignore） | ❌ | 不改 |

## 2. 当前运行入口

- 入口文件：`main.py`
- README 说明了运行方式：`python main.py`
- dev / test / smoke 共用入口，通过 `config.py` 的 `RUN_MODE` 切换
- 无 CLI 参数，所有配置通过 `config.py` 和 `.env`
- 配置文件：`config.py`（运行配置）、`.env`（API 密钥和模型）

## 3. 当前数据流

```text
input jsonl (dev_input.jsonl / test_input.jsonl)
  -> io_utils.load_jsonl()
  -> validators.validate_input_row()
  -> SkillFlow.run_row():
       -> MechanismSkill: LLM 分类 + 规则校准 + 可选复核 + 缓存
       -> UnderstandingSkill: LLM 推断意图和期望反馈
       -> StrategySkill: 确定性策略矩阵（纯规则）
       -> RiskSkill: 纯规则风险标签
       -> ResponseSkill: LLM 生成回复 + social rubric 审查 + 兜底
       -> ResponseRiskReviewSkill: 回复后风险复查 + 自动改写
       -> ValidatorSkill: 7 字段校验
       -> RewriterSkill: 校验失败时重写
  -> output_builder.build_output_row()
  -> io_utils.write_jsonl() -> submission.jsonl
  -> scripts/format_checker.py -> format_report.json
  -> scripts/evaluate_dev.py -> dev_eval_report.json (smoke/dev only)
  -> error_analyzer.run_dev_error_analysis() (dev only)
```

## 4. 当前 7 个字段生成逻辑

| 字段 | 生成方式 | 说明 |
| -- | -- | -- |
| `episode_id` | 直接复制 | 从 input_row 直接复制，output_builder 保证 |
| `bragging_mechanism` | LLM 分类 + 规则校准 + 可选复核 | MechanismSkill 生成，postprocess.calibrate_mechanism_with_evidence() 校准 |
| `speaker_intention` | LLM 一次生成 | UnderstandingSkill 通过 prompt 生成，postprocess.clean_field_text() 清理 |
| `desired_feedback` | LLM 一次生成 | 同上，与 speaker_intention 同一次 LLM 调用 |
| `risk_assessment` | 纯规则生成 | RiskSkill 通过 infer_contextual_risk_labels() + render_risk_assessment() 生成 |
| `response_strategy` | 纯规则生成 | StrategySkill 通过 choose_strategy_with_trace() 的策略矩阵生成 |
| `response_text` | LLM 生成 + 审查 + 兜底 | ResponseSkill 生成，ResponseRiskReviewSkill 复查，social_rubric.judge_row() 审查 |

## 5. 当前 LLM Client

- 文件路径：`src/llm_client.py`
- 模型名：`.env` 中 `OPENAI_MODEL` 配置
- API key / base URL：`.env` 中 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`
- 支持切换模型：✅ 只需改 `.env`
- temperature / max_tokens：每个 skill 调用时独立指定（mechanism=0.0/96, understanding=0.3/256, response=0.3/256）
- 支持本地 <=20B 模型：✅ 只要服务兼容 OpenAI API
- retry：✅ `RETRY_TIMES=3`，指数退避
- timeout：100 秒
- rate limiting：✅ 本地 RPM/TPM 限速器

## 6. 当前 Prompt / SkillFlow 状态

- prompt 文件：`src/prompts.py`
- 已有 SkillFlow：✅ `src/skillflow.py`，固定 7 步 + 可选 Rewriter
- 已有 mechanism skill：✅，含分类 prompt + review prompt + 规则校准
- 已有 risk skill：✅，纯规则，无 LLM 调用
- 已有 strategy skill：✅，纯规则矩阵，无 LLM 调用
- 已有 response skill：✅，含 LLM prompt + few-shot + memory + social rubric 审查
- speaker_intention 和 desired_feedback 由 UnderstandingSkill 一次生成
- 其余字段各自独立 skill 生成

## 7. 当前 Retrieval / Few-shot 状态

- 已有 retriever：✅ `src/fewshot.py`，FewShotRetriever 类
- 使用 train.jsonl 做 few-shot：✅，500 条
- 支持 embedding / hybrid / Jaccard：✅
- 有 meta-string：✅，`_task_text()` 函数构建查询
- 按不同 skill 检索：✅，task_k 配置 mechanism=0, strategy=0, response=2
- 当前只有 response 使用 few-shot（2 条），mechanism 和 strategy 不使用

## 8. 当前 Memory 状态

- 已有 memory 模块：✅ `src/memory.py`，MemoryItem + MemoryRetriever
- 48 条结构化记忆，7 种类型
- memory 不是全局注入：✅，按 skill 条件检索
- memory 有条件：✅，每条有 conditions 和 negative_conditions
- memory 无 activation_rate：❌，当前没有激活率统计
- memory 可关闭：✅，`USE_MEMORY = False`
- memory 可回滚：✅，修改 config.py 即可
- 不会造成 prompt 污染：✅，有条件过滤和字符限制
- 但 memory 没有 `status` 过滤：当前 `status` 字段存在但检索时未过滤

## 9. 当前 Validator / Postprocess 状态

- 字段完整性：✅ `validators.validate_output()` 检查正好 7 个字段
- episode_id 一致性：✅
- label 合法性：✅ mechanism 和 strategy 枚举检查
- response_strategy 合法性：✅
- hidden reasoning 泄露：✅ `has_suspicious_text()` 检查
- response_text 长度：✅ `MAX_WORDS["response_text"] = 60`
- strategy-response 一致性：✅ `ResponseRiskReviewSkill` 检查 ask_followup 有问号等
- Bloom 风险：✅ `social_rubric.judge_row()` 检查过誉、说教等

## 10. 当前 Evaluation 状态

- dev 怎么跑：`config.py` 设 `RUN_MODE = "dev"`，`python main.py`
- format checker：`scripts/format_checker.py`，pipeline 自动调用
- evaluator：`scripts/evaluate_dev.py`，pipeline 自动调用
- 输出分数：`dev_eval_report.json`（JSON）
- 保存 per-sample result：✅ `debug/trace.jsonl`
- 保存 error_report：✅ `error_analysis/error_report.md`（dev 模式且启用时）

## 11. 当前主要问题

| 优先级 | 问题 | 说明 |
| -- | -- | -- |
| P0 | 无 `.env` 文件 | 无法运行 LLM 调用，需用户配置 |
| P1 | 无 `outputs/` 目录 | 首次运行会自动创建 |
| P2 | 无 run_id manifest 增强 | 当前有 run_manifest.json 但缺少 git commit 等信息 |
| P2 | risk_assessment 过于规则化 | RiskSkill 纯规则，可能与 gold 不匹配 |
| P2 | mechanism 策略可能有系统性偏差 | 需要 dev 运行后才能分析 |
| P3 | 无 confusion matrix 输出 | 需要在 error_analyzer 中增加 |
| P3 | memory 无 activation_rate 统计 | Phase 6 需要 |
| P3 | 无 strategy-response mismatch 统计 | 需要在 error_analyzer 中增加 |

## 12. 可复用模块

- `src/skillflow.py`：SkillFlow 控制器，架构清晰，可直接扩展
- `src/skills/base.py`：Skill 基类，统一接口
- `src/memory.py`：Memory 系统，条件匹配+检索，可直接扩展
- `src/fewshot.py`：Few-shot 检索，支持 3 种模式，可直接扩展
- `src/postprocess.py`：解析/校准/清理，规则丰富
- `src/strategy_rules.py`：策略矩阵，规则完整
- `src/social_rubric.py`：回复审查器，可扩展
- `src/debug_logger.py`：调试日志，可扩展
- `src/error_analyzer.py`：错误分析，可扩展
- `scripts/format_checker.py`：官方格式检查，不改
- `scripts/evaluate_dev.py`：官方 dev 评分，不改
- `tests/test_pipeline.py`：28 个测试，全部通过

## 13. 需要新增模块

| 模块 | 用途 | Phase |
| -- | -- | -- |
| `run_manifest` 增强 | 增加 git commit、decoding params、features 开关 | Phase 1 |
| `trace_logger` 增强 | 增加 raw_model_output、parsed_output、final_output 对照 | Phase 1 |
| `error_analysis` 增强 | 增加 confusion matrix、strategy-response mismatch 统计 | Phase 2 |
| `conditional_memory_selector` | memory activation_rate 统计和条件触发 | Phase 6 |
| `semantic_validator` | strategy-response 语义一致性检查 | Phase 7 |
| `repair` 模块 | 一轮修复，记录修复前后对比 | Phase 7 |

## 14. 最小改造路线

1. **Phase 0**：配置 `.env`，运行 smoke 测试，验证 pipeline 可跑通（不改代码）
2. **Phase 1**：增强 run_manifest 和 trace，不改模型输出（只加日志）
3. **Phase 2**：增强 error_analyzer，增加 confusion matrix 和 per-field 统计
4. **Phase 4**：根据 dev 错误分析调 prompt 和规则（每次只改一个模块）
5. **Phase 5**：调整 few-shot 配置（task_k、retrieval_mode）
6. **Phase 6**：增加 memory activation_rate 统计
7. **Phase 7**：增强 validator 和 repair
8. **Phase 8**：模型实验 ablation
9. **Phase 9**：最终冻结提交
