# BRAG-Pipeline v1 generalized 实施报告

## 摘要

本次在 BRAG-Pipeline 工程中实现了 `v1 generalized` 方向，并同步到对应 GitHub feature branch。

Ollama 当前未启动，`127.0.0.1:11434` 不可访问，因此 qwen14b/qwen3 baseline 未能执行。本次完成的是不依赖模型的 generalized 模块移植、策略矩阵改造和离线验证。

## 已完成改动

| 模块 | 改动 | 目的 |
|---|---|---|
| `src/strategy_rules.py` | 将 `choose_strategy()` 改成基于 `platform + relationship + interaction_goal + mechanism` 的通用矩阵 | 提升 `response_strategy` 稳定性，避免按 dev case 硬修 |
| `src/postprocess.py` | 将 fallback response 改成 generalized template pool | 提高回复多样性，减少固定模板重复 |
| `src/prompts.py` | 替换偏 public-dev 场景的 mechanism examples | 避免 prompt 学到具体 dev 文本模式 |
| `src/pipeline.py` / `src/social_rubric.py` | 接入 verify-first social judge，只有 hard issue 才回退重写 | 保持模型回复自然度，同时降低过夸、说教和策略不匹配风险 |
| `scripts/run_no_overfit_offline_checks.py` | 增加 dev-specific keyword scan，并同步写入 `deliverables` 报告 | 防止高风险规则重新混入 |

## 验证结果

| 检查项 | 结果 |
|---|---:|
| `python3 -m py_compile config.py main.py src/*.py scripts/*.py` | 通过 |
| no-overfit stress rows | 80 |
| stress unique responses | 30 |
| stress most frequent response count | 8 |
| stress hard failures | 0 |
| stress format checker | 0 errors / 0 warnings（在含官方 checker 的本地数据副本中验证） |
| dev-specific keyword scan | 0 high-risk matches |

## Strategy 独立检查

在无法调用 Ollama 的情况下，用 `dev_gold` 的 `gold_bragging_mechanism` 作为输入，单独检查新的 `choose_strategy()`：

| 指标 | 结果 |
|---|---:|
| strategy score with gold mechanism | 0.7667 |
| preferred exact match | 24 / 45 |
| preferred or acceptable | 45 / 45 |

这个检查不等于最终 dev proxy score，但说明策略矩阵本身没有明显偏离官方 acceptable strategy 范围。

## 当前阻塞

| 阻塞 | 状态 | 后续动作 |
|---|---|---|
| GitHub | 已推送对应 feature branch | 可直接打开 PR |
| Ollama | `127.0.0.1:11434` 连接失败 | 启动 Ollama 后先跑 `curl /api/tags` 和 `curl /v1/models` |
| qwen14b | 当前无法确认模型名 | 以 `/api/tags` 返回的实际模型名配置 `.env` |

## 下一步

1. 打开对应 GitHub PR 页面。
2. Ollama 恢复后先跑 `MAX_ITEMS=3` smoke test。
3. 再跑完整 dev 45 条，生成 `RES.md`、`format_report.json`、`dev_eval_report.json`。
4. 如果 qwen14b 可用，用 qwen14b 重跑同样流程；否则先保留 qwen3 baseline。
