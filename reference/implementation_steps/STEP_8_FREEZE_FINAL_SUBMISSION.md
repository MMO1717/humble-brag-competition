# Step 8：Freeze + Final Submission

## 目标

在正式生成 test submission 前冻结所有会影响输出的组件，确保最终提交链路合规、可复现、可回滚。

## 冻结内容

正式 test 前需要冻结：

- 模型名称和版本
- decoding 参数
- prompt
- SkillFlow 顺序
- strategy rules
- active memory
- few-shot retriever 逻辑
- train data 版本
- postprocess / validators / checker
- config

建议写入：

```text
outputs/<final_run_id>/run_manifest.json
FINAL_SUBMISSION_NOTES.md
```

## 最终提交链路

最终 submission 只能走：

```text
test_input.jsonl
  ↓
本地合规模型
  ↓
SkillFlow
  ↓
active memory 检索
  ↓
few-shot 检索
  ↓
规则策略选择
  ↓
Checker & Repair
  ↓
submission.jsonl
  ↓
format_checker.py
```

最终提交链路中不包含：

- 外部 API 模型
- 外部 API reranker
- 外部 API checker
- 外部 API repair
- 外部 API 对 test 样本的任何实时判断
- test 阶段 candidate memory 生成
- test 阶段 memory 更新

## 运行配置

```python
MODE = "test"
MAX_ITEMS = None
RUN_OFFICIAL_FORMAT_CHECK = True
RUN_DEV_EVAL = False
RUN_DEV_ERROR_ANALYSIS = False
ERROR_ANALYSIS_USE_LLM = False
USE_AGENT_MEMORY = True
USE_FEWSHOT = True
```

## 最终运行命令

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
open -a Ollama
python3 main.py
```

手动格式检查：

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main/BRAG-Agent-public
python3 scripts/format_checker.py ../outputs/<final_run_id>/submission.jsonl data/test_input.jsonl
```

## 最终产物

```text
outputs/<final_run_id>/
  submission.jsonl
  format_report.json
  run_manifest.json
  RES.md
  debug/trace.jsonl
  debug/llm_calls.jsonl
```

建议额外复制一份固定命名的提交文件：

```text
outputs/final_submission_qwen3_8b.jsonl
```

## 通过标准

- test submission 通过 `format_checker.py`
- 行数等于 `test_input.jsonl`
- 没有 missing / unexpected / duplicated episode ids
- 没有 hidden reasoning
- 没有非法 enum
- 没有额外字段
- run manifest 能说明模型、参数、memory、few-shot 和代码配置
- 最终链路没有外部 API 调用

## 风险点

- 最终运行忘记切换 `MODE="test"`
- test 阶段误开 RUN_DEV_ERROR_ANALYSIS
- 本地大模型 Judge 评审逻辑被误接入最终推理链路
- active memory 在最终运行后又被修改
- 只保存 submission，没有保存 run manifest 和 format report

## 完成标志

当最终 test submission 通过官方格式检查，并且能证明生成链路没有外部 API 参与时，可以进入正式提交。
