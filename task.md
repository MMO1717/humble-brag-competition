# 实施任务清单

更新时间：2026-05-21

## 总原则

本项目后续按“先框架、再增强”的方式推进。任何新功能都必须满足：

- 能单独开启或关闭
- 有明确验证命令
- 不破坏官方输出格式
- 有可比较的 baseline
- 实验结论写回文档

## Phase 0：仓库和数据盘点

目标：确认当前仓库真实输入、输出和评测契约。

任务：

1. 读取 `data/Bragging_data.json`，整理字段列表、样本数量和示例。
2. 从 `reference/BRAG-Agent-public/` 中确认官方输入字段、输出 7 字段、合法标签和评测脚本调用方式。
3. 写出本仓库专用的输入 schema 和输出 schema 说明。
4. 确认是否需要把官方 `format_checker.py`、`evaluate_dev.py` 提升到根目录脚本区。

验收标准：

- 文档中列出输入字段和输出字段。
- 能说明当前数据与官方 JSONL 数据是否一致。
- 后续 pipeline 不再依赖猜测字段。

## Phase 1：最小可运行 Baseline

目标：先跑通完整链路，不追求高分。

任务：

1. 实现数据加载器。
2. 实现最小 baseline 生成器。
3. 实现输出 JSONL 写入。
4. 实现 schema validator。
5. 接入 format checker。
6. dev 模式下接入 evaluator。

验收标准：

- 可以生成 `submission.jsonl`。
- 格式检查 0 error。
- 每次运行保存：
  - `submission.jsonl`
  - `run_manifest.json`
  - `format_report.json`
  - `dev_eval_report.json`，如果有 gold
  - `RES.md`

## Phase 2：可调试日志

目标：让每条样本为什么这样输出可以追踪。

任务：

1. 每条样本保存 trace。
2. trace 至少包含输入、模型输出、解析结果、fallback 原因和最终输出。
3. 保存 LLM 调用日志，但默认不保存敏感配置。
4. 生成失败样本摘要。

验收标准：

- 任意一条输出都能回查中间过程。
- 失败、fallback、修复动作都有记录。

## Phase 3：SkillFlow

目标：把任务拆成稳定模块，而不是一次性大 prompt。

建议顺序：

```text
mechanism
-> intent / desired feedback
-> risk
-> strategy
-> response
-> validator / rewriter
```

验收标准：

- SkillFlow 能与 baseline 用同一套数据和评测命令对比。
- 至少完整跑一次 dev。
- 对比表必须包含 proxy score、mechanism、strategy、risk、response。

## Phase 4：Few-shot / Meta-String Retrieval

目标：在框架稳定后，再启用检索增强。

任务：

1. 保留 Meta-String 思路，但先验证字段对齐。
2. 检索不能只看 post 文本，要包含 platform、relationship、agent role、interaction goal。
3. 只把 few-shot 注入最需要的模块，避免 prompt 过长。
4. 做开关消融：`no_fewshot` vs `fewshot`。

验收标准：

- 完整 dev 不明显伤害核心指标。
- 有消融表。
- 有失败样本分析。

## Phase 5：Memory 和 Local Judge

目标：只有在 baseline、SkillFlow、few-shot 都可比较后，再加入 memory。

任务：

1. 建立 active / candidate / deprecated 三类 memory。
2. candidate memory 必须经过人工或 local judge 评审。
3. active memory 必须能禁用。
4. 做 ablation，避免把 public dev 样本硬记成规则。

验收标准：

- 有 memory 使用记录。
- 有 no-memory vs active-memory 对比。
- 有过拟合风险说明。

## 当前下一步

现在最应该做的是 Phase 0 和 Phase 1：

```text
先盘点数据和官方契约
再做最小 baseline
```

暂时不要直接实现复杂 RAG、memory 或自反思回滚。那些模块应该在基础链路可跑、可评、可回滚之后再加。
