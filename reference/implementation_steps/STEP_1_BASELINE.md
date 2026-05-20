# Step 1：Baseline

## 目标

建立一个最小可运行的 BRAG-Agent 基线，用来确认官方数据读取、JSONL 输出、格式检查和 dev 代理评分链路全部可用。

Baseline 不追求高分，重点是形成可比较的初始分数和错误分布。

## 实现范围

Baseline 应尽量简单：

- 读取 `BRAG-Agent-public/data/dev_input.jsonl` 或 `test_input.jsonl`
- 调用本地合规模型生成字段
- 组装官方要求的 7 个输出字段
- 做基础 enum 归一化和字段清洗
- 输出 `submission.jsonl`
- 自动运行 `format_checker.py`
- dev 模式下自动运行 `evaluate_dev.py`

## 暂不做

- 不使用 memory
- 不使用 few-shot
- 不使用复杂 SkillFlow
- 不使用外部 API
- 不做 candidate memory 生成

## 代码位置

当前工程中主要对应：

- `main.py`
- `config.py`
- `src/pipeline.py`
- `src/llm_client.py`
- `src/output_builder.py`
- `src/postprocess.py`
- `src/validators.py`

Step 1 当前使用 `BaselineFlow`：

- `src/baseline.py`
- `src/prompts.py` 中的 `build_baseline_prompt()`

运行 Step 1 时必须显式设置：

```python
USE_SKILLFLOW = False
USE_FEWSHOT = False
USE_AGENT_WIKI = False
RUN_DEV_ERROR_ANALYSIS = False
```

## 产物

```text
outputs/<run_id>/
  submission.jsonl
  format_report.json
  dev_eval_report.json
  run_manifest.json
  RES.md
```

## 验证命令

冒烟测试：

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=3; config.USE_SKILLFLOW=False; config.USE_FEWSHOT=False; config.USE_AGENT_WIKI=False; config.RUN_DEV_ERROR_ANALYSIS=False; run_pipeline(config)"
```

完整 dev：

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=None; config.USE_SKILLFLOW=False; config.USE_FEWSHOT=False; config.USE_AGENT_WIKI=False; config.RUN_DEV_ERROR_ANALYSIS=False; run_pipeline(config)"
```

## 通过标准

- `format_checker.py` 通过
- `submission.jsonl` 行数和输入样本一致
- 7 个字段完整且没有多余字段
- dev 模式下能产出 `proxy_dev_score`
- 结果目录可复现、可追踪
- `run_manifest.json` 中 `use_skillflow` 为 `false`
- `run_manifest.json` 中 `flow_name` 为 `BaselineFlow`

## 风险点

- 本地模型输出 hidden reasoning
- 模型输出非法 enum
- `episode_id` 没有原样复制
- `risk_assessment` 输出成数组而不是字符串
- 只看 3 条冒烟测试分数，误判模型真实表现

## 完成标志

当 Baseline 能稳定跑通 dev subset 和完整 dev，并且每次运行都能保存 `RES.md`、`format_report.json`、`dev_eval_report.json` 和 `run_manifest.json` 时，进入 Step 2。

## 当前完成记录

Step 1 已完成本地验证。

### 3 条 dev 冒烟测试

运行目录：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/outputs/dev__20260518_194639_754__qwen3_8b__max3__temp0p3__tok256
```

结果：

| 指标 | 数值 |
| --- | --- |
| row_count | 3 |
| format_checker | valid |
| warning_count | 0 |
| proxy_dev_score | 53.295 |
| mechanism_accuracy | 0.3333 |
| strategy_score | 0.3333 |
| risk_label_f1 | 0.8889 |
| response_reference_token_f1 | 0.2567 |

### 完整 dev 运行

运行目录：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/outputs/dev__20260518_194705_081__qwen3_8b__full__temp0p3__tok256
```

结果：

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

`run_manifest.json` 已确认：

```text
flow_name = BaselineFlow
use_skillflow = false
use_agent_wiki = false
use_fewshot = false
run_dev_error_analysis = false
```

结论：Step 1 的目标已经达成。Baseline 分数不高是预期结果，它的作用是提供后续 SkillFlow、few-shot、memory 和 error analysis 的对照基线。
