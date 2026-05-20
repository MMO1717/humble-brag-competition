# BRAG-Pipeline：Understander–Responder Social Agent

这是 CCAC 2026 赛道四 BRAG-Agent 的 pipeline demo。它会读取官方 JSONL 输入，调用兼容 OpenAI 格式的 chat completions 接口，然后用 Python dict 组装最终 JSONL 提交文件。

当前 v2 在原有最小 demo 上增加了 Agent Wiki、SkillFlow 和可选 few-shot，但启动流程和依赖仍然保持简单：

```text
复制 .env.example -> 修改 config.py -> python main.py
```

## 1. 安装依赖

进入工程目录：

```bash
cd BRAG-Pipeline
pip install -r requirements.txt
```

## 2. 配置 `.env`

复制环境变量模板：

```bash
copy .env.example .env
```

在 `.env` 中配置 LLM API：

```env
OPENAI_BASE_URL=http://localhost:5001/v1
OPENAI_API_KEY=sk-local
OPENAI_MODEL=your-model-name
```

这是若使用 KoboldCpp 的示例。KoboldCpp 兼容 OpenAI 格式的接口，API_KEY 和 MODEL_NAME 可以任填。

## 3. 修改 `config.py`

建议先跑 3 条冒烟测试：

```python
MODE = "dev"
MAX_ITEMS = 3
```

常用配置项：

- `MODE`：`"dev"` 或 `"test"`。
- `MAX_ITEMS`：调试时设为小整数；完整运行时设为 `None`。
- `TEMPERATURE`：模型采样温度。
- `MAX_TOKENS`：每次模型调用的最大词元数。
- `RETRY_TIMES`：接口调用失败后的重试次数。
- `RUN_LLM_HEALTH_CHECK`：启动时先检查 LLM 接口是否可用，避免 API 配错时生成全兜底结果。
- `RUN_OFFICIAL_FORMAT_CHECK`：运行后自动调用官方格式检查脚本。
- `RUN_DEV_EVAL`：dev 模式下自动调用官方 dev 代理评分脚本。
- `OUTPUT_DIR`：所有运行结果、检查报告、评分报告的保存目录。
- `RUN_NAME_PREFIX`：可选的文件夹名前缀，方便给实验分组。
- `USE_SKILLFLOW`：v2 主流程开关，当前应保持为 `True`。
- `USE_AGENT_WIKI`：是否读取 `agent_wiki/` 下的静态知识。
- `USE_FEWSHOT`：是否从 `train.jsonl` 检索 few-shot 示例。
- `FEWSHOT_K`：每次最多注入的 few-shot 示例数，默认 `2`。
- `SAVE_DEBUG_TRACE`：是否保存每条样本的 Agent 链路调试信息。
- `SAVE_LLM_CALL_LOGS`：是否保存逐次 LLM 调用日志。
- `SAVE_PROMPT_TEXT`：LLM 调用日志里是否保存完整 prompt。
- `SAVE_RAW_LLM_OUTPUT`：LLM 调用日志里是否保存模型原始输出。
- `RUN_DEV_ERROR_ANALYSIS`：dev 评分后是否运行独立错误分析模块。
- `ERROR_ANALYSIS_TOP_K`：错误分析保留的高错误样本数。

## 4. 一键运行

在 `brag_pipeline/` 目录下执行：

```bash
python main.py
```

程序会在终端打印本次 `run_id`、结果文件夹、格式检查结果和 dev 代理分数摘要。

每次运行只会在 `outputs/` 下新增一个结果文件夹，命名格式大致为：

```text
模式 + 时间戳 + 模型名 + 样本数 + 温度 + max_tokens
```

这样同一模式下按文件夹名排序时，基本就是按运行时间排序。

进入某次运行的文件夹后，优先打开里面的 `RES.md`，它会给出本次运行结果的摘要。

如果 `SAVE_DEBUG_TRACE = True`，同一文件夹下还会生成：

```text
debug/trace.jsonl
```

这个文件用于错误分析，可以看到每条样本的机制、风险、策略、回复、skill trace、错误信息、模型原始输出和 few-shot 示例。

如果开启 LLM 调用日志，同一文件夹下还会生成：

```text
debug/llm_calls.jsonl
```

- `debug/llm_calls.jsonl`：逐次 LLM 调用日志，包含 `episode_id`、`skill`、模型名、prompt、原始输出、耗时、错误信息。

如果开启 dev 错误分析，同一文件夹下还会生成：

```text
error_analysis/error_cases.jsonl
error_analysis/error_report.md
error_analysis/llm_error_review.jsonl
```

错误分析默认关闭，打开方式：

```python
RUN_DEV_ERROR_ANALYSIS = True
```

## 5. 冒烟测试检查

当 `MODE = "dev"` 且 `MAX_ITEMS = 3` 时，程序会额外保存本次匹配的输入子集文件。官方格式检查应使用这对文件：

```bash
cd BRAG-Agent-public
python scripts/format_checker.py ../outputs/<本次run_id>/submission.jsonl ../outputs/<本次run_id>/input_subset.jsonl
```

如果没有使用参考输入文件，也可以只做字段格式检查：

```bash
python scripts/format_checker.py ../outputs/<本次run_id>/submission.jsonl
```

正常情况下，如果 `RUN_OFFICIAL_FORMAT_CHECK = True`，上述检查会在 `python main.py` 结束后自动运行，并保存到：

```text
outputs/<本次run_id>/format_report.json
```

## 6. dev 运行与评分

完整 dev 运行建议配置：

```python
MODE = "dev"
MAX_ITEMS = None
RUN_OFFICIAL_FORMAT_CHECK = True
RUN_DEV_EVAL = True
```

运行：

```bash
python main.py
```

程序会自动生成 `dev_eval_report.json`，并在终端打印 `proxy_dev_score`。

如果想手动评分完整 dev：

```bash
cd BRAG-Agent-public
python scripts/evaluate_dev.py data/dev_input.jsonl data/dev_gold.jsonl ../outputs/<本次run_id>/submission.jsonl
```

如果 `MAX_ITEMS` 是小整数，也可以对子集结果评分：

```bash
python scripts/evaluate_dev.py ../outputs/<本次run_id>/input_subset.jsonl data/dev_gold.jsonl ../outputs/<本次run_id>/submission.jsonl
```

注意：dev 评分只是官方公开代理分数，不等于最终隐藏榜单成绩。冒烟测试分数只用于确认链路和初步观察。

## 7. 生成 test 提交

切换到测试集：

```python
MODE = "test"
MAX_ITEMS = None
RUN_OFFICIAL_FORMAT_CHECK = True
RUN_DEV_EVAL = False
```

运行：

```bash
python main.py
```

检查测试集提交格式：

```bash
cd BRAG-Agent-public
python scripts/format_checker.py ../outputs/<本次run_id>/submission.jsonl data/test_input.jsonl
```

test 没有公开 gold，所以本地只能做格式检查，不能计算 dev 代理分数。

## 8. 输出设计说明

- `episode_id` 始终由程序从输入原样复制。
- 最终 JSONL 始终由 Python dict 和 `json.dumps(..., ensure_ascii=False)` 生成。
- 模型不会直接写最终提交 JSONL。
- `bragging_mechanism` 和 `response_strategy` 都会做合法标签归一化。
- `risk_assessment` 始终是非空字符串，不会输出数组。
- `response_text` 会清理 JSON、markdown code fence、`analysis:`、`assistant:`、`<think>`、`chain of thought`、`step by step` 等可疑内容。
- `light_acknowledgment` 和 `neutral_observation` 会禁止明显过度夸赞词。

## 9. v2 架构和调试

v2 主线是固定顺序的 SkillFlow，不是自由规划 Agent：

```text
Input row
-> MechanismSkill
-> UnderstandingSkill
-> RiskSkill
-> StrategySkill
-> ResponseSkill
-> ValidatorSkill
-> RewriterSkill if needed
-> Final output row
```

相关代码位置：

- `src/skillflow.py`：固定流程控制器。
- `src/skills/`：每个步骤一个 skill。
- `agent_wiki/`：静态知识文档，可中英双语。
- `src/wiki_loader.py`：只抽取 Wiki 里的英文 prompt notes 注入 prompt。
- `src/fewshot.py`：从 `train.jsonl` 做轻量 token overlap 检索。

few-shot 默认只注入两个地方：

- `MechanismSkill`：帮助机制分类。
- `ResponseSkill`：帮助学习回复风格。

默认不把 few-shot 注入 Understanding / Risk / Strategy，避免 prompt 变长和逻辑漂移。few-shot 示例不会展示 `episode_id`，避免模型模仿训练集 ID。

关闭 few-shot：

```python
USE_FEWSHOT = False
```

调整 few-shot 数量：

```python
FEWSHOT_K = 2
```

修改 Wiki：

```text
agent_wiki/
```

每个 Wiki 文件中 `## English Prompt Notes` 下面的英文内容才会注入 prompt。中文说明只给队友阅读，不会大段塞进英文 prompt。

查看中间状态：

```text
outputs/<本次run_id>/debug/trace.jsonl
```

重点看 `mechanism`、`risk_labels`、`strategy`、`response_text`、`raw_outputs`、`fewshot_examples`、`skill_errors`、`validation_errors`。

查看逐次模型调用：

```text
outputs/<本次run_id>/debug/llm_calls.jsonl
```

重点看 `skill`、`messages`、`response_text`、`elapsed_ms`、`error`。这个文件只记录已有调用，不会增加 API 请求或 token 消耗。

查看 dev 错误分析：

```text
outputs/<本次run_id>/error_analysis/error_report.md
```

重点看高错误样本的 mechanism、strategy、risk、response 差异，以及 LLM 总结的改进建议。

## 10. 关于prompts

主要 prompt 都集中在：

```text
src/prompts.py
```

里面现在按 Skill 拆成几类 builder：

- `build_mechanism_prompt()`：机制分类 prompt，可注入 Wiki 和 few-shot。
- `build_understanding_prompt()`：生成 `speaker_intention` 和 `desired_feedback`。
- `build_risk_prompt()`：生成内部风险标签和最终 `risk_assessment` 字符串。
- `build_response_prompt()`：根据 state、Wiki、few-shot 和策略生成最终英文回复。
- `format_fewshot_examples()`：集中控制 few-shot 示例格式，默认不展示 `episode_id`。

旧的 `mechanism_classifier_messages()`、`understanding_messages()`、`response_messages()` 仍保留为兼容 wrapper。

注意：`response_strategy` 不是主要交给 prompt 决定，而是由：`src/strategy_rules.py`里的规则函数 `choose_strategy()` 决定。这样做是为了让策略更稳定，避免模型随意输出非法或不一致的策略，缺点是策略灵活性弱，后续再优化改进。

如果只想改某一步的 prompt，优先改 `src/prompts.py` 对应 builder；如果想改某一步的执行逻辑，再改 `src/skills/` 下对应的 skill。

## 11. 关于 dev 代理评分

官方公开的 `evaluate_dev.py` 是 dev 代理评分脚本，只用于本地迭代参考。它和真实 test 集隐藏评测标准不完全一样，最终排名要以官方隐藏测试集评测为准。

dev 代理总分公式是：

```text
100 * (
  0.30 * mechanism_accuracy
  + 0.20 * strategy_score
  + 0.20 * risk_label_f1
  + 0.15 * response_reference_token_f1
  + 0.15 * format_score
)
```

各项都是 `0~1` 分，满分是 `1.0`：

- `mechanism_accuracy`：`bragging_mechanism` 分类准确率，标签和 dev_gold 完全一致才算对。
- `strategy_score`：`response_strategy` 策略得分；命中首选策略得 `1.0`，命中可接受策略得 `0.5`，否则得 `0`。
- `risk_label_f1`：从 `risk_assessment` 字符串里抽取风险关键词，再和 gold 风险标签算 F1。
- `response_reference_token_f1`：`response_text` 和参考回复的 token overlap F1，措辞不同也会影响这个分数。
- `format_score`：格式分；通过 `format_checker.py` 就是 `1.0`，不通过则提交无效。
