# Step 6：Error Analysis

## 目标

把 dev 输出和 gold 对齐，自动找出高错误样本和重复错误模式，为后续 candidate memory 生成提供依据。

## 实现范围

核心模块：

```text
src/error_analyzer.py
```

分析维度：

- mechanism 是否命中
- strategy 是否 preferred 或 acceptable
- risk label F1
- response token F1
- speaker_intention token F1
- desired_feedback token F1
- validation errors
- skill errors
- few-shot 是否误导
- memory 是否误导

输出高错误样本：

```text
error_analysis/error_cases.jsonl
error_analysis/error_report.md
error_analysis/llm_error_review.jsonl
```

## 配置项

```python
RUN_DEV_ERROR_ANALYSIS = True
ERROR_ANALYSIS_TOP_K = 10
ERROR_ANALYSIS_USE_LLM = True
ERROR_ANALYSIS_MAX_CASES_PER_CALL = 5
```

注意：`ERROR_ANALYSIS_USE_LLM=True` 可以用于 dev 错误分析，但不能用于最终 test 生成链路。

## 产物

```text
outputs/<run_id>/error_analysis/error_cases.jsonl
outputs/<run_id>/error_analysis/error_report.md
outputs/<run_id>/error_analysis/llm_error_review.jsonl
```

## 验证命令

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=None; config.RUN_DEV_ERROR_ANALYSIS=True; config.ERROR_ANALYSIS_TOP_K=10; run_pipeline(config)"
```

## 通过标准

- 能列出 top error cases
- 每个 case 有分项分数
- 报告能指出主要错误类型
- 报告能区分 mechanism、risk、strategy、response 错误
- 输出能被 Candidate Memory Generator 读取

## 风险点

- LLM 错误总结把单个 dev 样本规律泛化成错误规则
- response token F1 低不一定代表社交回复差
- dev gold 只有 45 条，错误模式统计可能不稳定
- 不能把 error report 直接当 active memory 使用

## 完成标志

当 Error Analysis 能稳定产出结构化错例和可读报告，并能被下一步 candidate generator 使用时，进入 Step 7。
