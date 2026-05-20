# Step 3：Debug Log

## 目标

建立可分析、可回放的调试日志。后续 prompt 调整、memory 生成、错误分析和 ablation 都必须依赖 Debug Log。

## 实现范围

记录两类日志：

```text
debug/trace.jsonl
debug/llm_calls.jsonl
```

`trace.jsonl` 每条样本记录：

- `episode_id`
- `bragging_mechanism`
- `speaker_intention`
- `desired_feedback`
- `risk_labels`
- `risk_assessment`
- `response_strategy`
- `response_text`
- `skill_trace`
- `skill_errors`
- `validation_errors`
- `raw_outputs`
- `fewshot_examples`
- `memory_examples`

`llm_calls.jsonl` 每次模型调用记录：

- `episode_id`
- `skill`
- `model`
- `temperature`
- `max_tokens`
- `prompt_char_count`
- `response_char_count`
- `elapsed_ms`
- `success`
- `error`
- 可选保存 prompt 和 raw output

## 配置项

```python
SAVE_DEBUG_TRACE = True
SAVE_LLM_CALL_LOGS = True
SAVE_PROMPT_TEXT = True
SAVE_RAW_LLM_OUTPUT = True
```

正式大规模运行时，如果日志太大，可以关闭完整 prompt：

```python
SAVE_PROMPT_TEXT = False
```

## 代码位置

主要对应：

- `src/debug_logger.py`
- `src/pipeline.py`
- `src/skillflow.py`
- `src/skills/*.py`

## 产物

```text
outputs/<run_id>/debug/trace.jsonl
outputs/<run_id>/debug/llm_calls.jsonl
```

## 验证命令

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=3; config.SAVE_DEBUG_TRACE=True; config.SAVE_LLM_CALL_LOGS=True; config.RUN_DEV_ERROR_ANALYSIS=False; run_pipeline(config)"
```

## 通过标准

- 每个输出样本都能在 `trace.jsonl` 找到对应记录
- 每次 LLM 调用都能在 `llm_calls.jsonl` 找到记录
- 日志包含足够信息定位机制、风险、策略、回复错误
- 日志不会影响最终 submission schema

## 风险点

- prompt 日志过大
- raw output 里包含 hidden reasoning，需要避免进入最终 response
- 日志字段变化后，Error Analysis 或 Candidate Memory Generator 读取失败
- 日志过多导致团队只看局部错例，忽视整体指标

## 完成标志

当每次 run 都能稳定保存可读、可追踪、可用于错误分析的日志时，进入 Step 4。
