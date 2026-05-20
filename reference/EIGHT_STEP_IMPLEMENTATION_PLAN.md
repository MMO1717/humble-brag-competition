# BRAG-Agent 架构构建 8 步实施计划索引

本文档是 8 步实施计划的索引页。每一个阶段都有独立 Markdown 文档，便于分工、执行、评审和后续维护。

## 步骤列表

| Step | 文档 | 目标 |
| --- | --- | --- |
| 1 | [STEP_1_BASELINE.md](implementation_steps/STEP_1_BASELINE.md) | 已完成：跑通最小可运行基线，确认 JSONL 输出、格式检查和 dev 评分链路 |
| 2 | [STEP_2_SKILLFLOW.md](implementation_steps/STEP_2_SKILLFLOW.md) | 已完成：把任务拆成固定顺序 Skills，由 SkillFlow 控制执行 |
| 3 | [STEP_3_DEBUG_LOG.md](implementation_steps/STEP_3_DEBUG_LOG.md) | 建立可分析、可回放的 trace 和 LLM 调用日志 |
| 4 | [STEP_4_FEWSHOT.md](implementation_steps/STEP_4_FEWSHOT.md) | 从 train 集检索相似样本，增强机制判断和回复风格 |
| 5 | [STEP_5_ACTIVE_MEMORY.md](implementation_steps/STEP_5_ACTIVE_MEMORY.md) | 建立可检索、可回滚、可禁用的 active memory |
| 6 | [STEP_6_ERROR_ANALYSIS.md](implementation_steps/STEP_6_ERROR_ANALYSIS.md) | 自动抽取高错误样本和重复错误模式 |
| 7 | [STEP_7_CANDIDATE_MEMORY_REVIEW_ABLATION.md](implementation_steps/STEP_7_CANDIDATE_MEMORY_REVIEW_ABLATION.md) | 生成 candidate memory，进行评审、晋升和 ablation |
| 8 | [STEP_8_FREEZE_FINAL_SUBMISSION.md](implementation_steps/STEP_8_FREEZE_FINAL_SUBMISSION.md) | 冻结最终链路并生成合规 test submission |

## 总体边界

- 每一步都必须能单独运行、单独评估、单独回滚。
- 所有实验先在 dev 上验证，test 只用于最终生成提交。
- 离线评审由本地评审模型 (Local LLM Judge) 完成，整个项目不依赖外部大模型 API 从而保持完全闭环。
- 任何外部 API 不参与最终 test submission 且不参与任何离线评审。
- public dev proxy score 只是迭代参考，不能直接等同于 hidden test 表现。
- 每次实验都必须保存 submission、format report、dev eval report、debug trace 和 run manifest。

## 推荐推进节奏

| 阶段 | 重点 | 状态判断 |
| --- | --- | --- |
| Step 1-3 | 跑通链路、拆 Skill、保存日志 | 工程可调试 |
| Step 4 | few-shot 检索 | 低成本增强 |
| Step 5 | active memory 读取 | memory 进入推理链路 |
| Step 6 | error analysis | 找到稳定错误模式 |
| Step 7 | candidate review + ablation | 判断 memory 是否真有用 |
| Step 8 | freeze + submission | 合规提交 |

当前工程已完成 Step 1-2，并基本具备 Step 3-4 和 Step 6 的雏形。下一阶段最值得优先补的是：

```text
Step 5：Active Memory
Step 7：Candidate Memory Review + Ablation
```

这两步完成后，整个系统才真正形成 Agent Memory + SkillFlow 的闭环。
