# Agent Memory 说明

这里存放 BRAG-Agent 的受控记忆。Memory 不是自由 Agent 的长期记忆，而是为固定 JSONL 预测任务服务的可审计经验库。

## 目录

- `static/`：静态规则，是当前唯一的静态知识目录。
- `active/memory.jsonl`：人工确认后启用的经验记忆。
- `candidate/memory_candidates.jsonl`：由错误分析生成的候选记忆，默认不进入主流程。
- `deprecated/memory_deprecated.jsonl`：效果不好或过拟合后废弃的记忆。
- `eval/`：memory 策略评估和 ablation 记录。

## 使用原则

- 不把 dev 单条答案写成 memory。
- memory 必须总结抽象规律，并保留来源。
- candidate memory 默认不启用。
- evaluator preference memory 只能作为谨慎参考，不能自动晋级。
- 最终输出仍由 Python dict 组装官方 7 字段。

## 运行模式

- `no_memory`：不向任何 Skill 注入 memory，用作对照。
- `static_only`：只把 `static/` 规则作为 memory 注入，用作实验。
- `active`：只注入 `active/memory.jsonl` 中人工确认的 memory，默认推荐。
- `active_plus_candidate`：同时注入 active 和 candidate，只建议临时实验。

静态规则由 `src/memory_loader.py` 读取。主流程会把 `static/` 中的英文提示段作为基础知识传给 prompt；动态 memory 是否额外注入，由 `config.py` 里的 `MEMORY_MODE` 控制。
