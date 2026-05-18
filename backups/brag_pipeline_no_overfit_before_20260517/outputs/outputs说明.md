# outputs 目录说明

`python main.py` 每运行一次，会在本目录下新增一个结果文件夹。

文件夹命名格式大致为：

```text
模式 + 时间戳 + 模型名 + 样本数 + 温度 + max_tokens
```

这样同一模式下按文件夹名排序时，基本就是按运行时间排序。

## 每个运行文件夹里有什么

- `RES.md`：本次运行的摘要，建议优先打开这个文件。
- `submission.jsonl`：生成的最终提交结果文件，每行一个样本输出。
- `input_subset.jsonl`：只在 `MAX_ITEMS` 非空时生成，用于检查 subset 的 episode_id。
- `format_report.json`：官方 `format_checker.py` 的完整结果。
- `dev_eval_report.json`：官方 `evaluate_dev.py` 的完整结果，仅 dev 模式有意义。
- `run_manifest.json`：本次运行的配置索引，记录模型、参数、路径和脚本退出码。

- 格式是否通过：看 `format_report.json` 里的 `parsed_stdout_json.valid`，`true` 表示通过。
- dev 分数：看 `dev_eval_report.json` 里的 `parsed_stdout_json.proxy_metrics.proxy_dev_score`。
- test 没有公开 gold，所以本地没有分数，只能看格式是否通过。

- 如果是 `MAX_ITEMS = 3` 这类冒烟测试，分数只用于确认链路，不代表完整 dev 表现。
