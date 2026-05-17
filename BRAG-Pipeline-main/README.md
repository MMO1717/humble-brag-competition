# BRAG-Pipeline：Understander–Responder Social Agent

这是 CCAC 2026 赛道四 BRAG-Agent 的第一版最小可行演示demo。它会读取官方 JSONL 输入，调用兼容 OpenAI 格式的 chat completions 接口，然后用 Python dict 组装最终 JSONL 提交文件。

第一版保持简单的启动流程和极简环境依赖：

```text
复制 .env.example -> 修改 config.py -> python main.py
```

## 1. 安装依赖

进入工程目录：

```bash
cd brag_pipeline
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
- `RUN_OFFICIAL_FORMAT_CHECK`：运行后自动调用官方格式检查脚本。
- `RUN_DEV_EVAL`：dev 模式下自动调用官方 dev 代理评分脚本。
- `OUTPUT_DIR`：所有运行结果、检查报告、评分报告的保存目录。
- `RUN_NAME_PREFIX`：可选的文件夹名前缀，方便给实验分组。

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

## 9. 关于prompts

主要 prompt 都集中在：

```text
src/prompts.py
```

里面现在有三类 prompt：

- `mechanism_classifier_messages()`：负责让模型判断 `bragging_mechanism`，也就是炫耀机制分类。
- `understanding_messages()`：负责让模型生成 `speaker_intention`、`desired_feedback`、`risk_assessment` 三个理解字段。
- `response_messages()`：负责让模型根据输入、理解字段和规则选出的 `response_strategy` 生成最终英文回复。

注意：`response_strategy` 不是主要交给 prompt 决定，而是由：`src/strategy_rules.py`里的规则函数 `choose_strategy()` 决定。这样做是为了让策略更稳定，避免模型随意输出非法或不一致的策略，缺点是策略灵活性弱，后续再优化改进。

## 10. 关于 dev 代理评分

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

## 11. no-overfit 离线增强

当前版本加入了不依赖模型接口的 no-overfit 工程检查，主要用于验证通用社会语用规则、risk 关键词渲染、策略规则和安全回复 fallback。

运行：

```bash
python3 scripts/run_no_overfit_offline_checks.py
python3 BRAG-Agent-public/scripts/format_checker.py \
  outputs/no_overfit_offline/stress_submission.jsonl \
  outputs/no_overfit_offline/stress_input.jsonl
```

生成文件：

```text
outputs/no_overfit_offline/stress_input.jsonl
outputs/no_overfit_offline/stress_submission.jsonl
outputs/no_overfit_offline/offline_check_report.md
```

这个检查不使用公开答案或参考回复，也不按具体样本文本写规则。它只能证明工程链路和离线约束通过，不能替代完整 dev 运行分数。
