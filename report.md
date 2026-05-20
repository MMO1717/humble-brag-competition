# Humble Brag Competition 项目状态报告

更新时间：2026-05-21

## 1. 当前判断

这个仓库应作为新的正式主线使用。旧的 `/Users/mm/Desktop/BRAG-Pipeline-main` 工程已经做过不少实验，但目录边界和 git 状态不够干净，不适合继续作为主战场。

当前策略是：

```text
新仓库搭主框架 -> 旧项目做 reference -> 逐步移植有效模块 -> 每步验证
```

这比继续在旧目录上叠加功能更稳，也更方便提交、回滚和向 GitHub 同步。

## 2. 已完成事项

### 2.1 新仓库已拉取

已从以下远端拉取：

```text
https://github.com/MMO1717/humble-brag-competition.git
```

当前本地路径：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/humble-brag-competition
```

当前分支：

```text
new
```

### 2.2 旧项目已归档为 reference

旧 BRAG-Pipeline 实验工程已经整理到：

```text
reference/
```

归档时排除了：

- `.env`
- `.git`
- `.venv`
- `outputs`
- `__pycache__`
- `.DS_Store`

这样可以保留旧代码、旧文档和官方评测脚本副本，同时避免把本地密钥、虚拟环境和大量实验输出上传到 GitHub。

### 2.3 已推送到 GitHub

`reference/` 已提交并推送到远端 `new` 分支。

最近一次 reference 归档提交：

```text
ef2823b Add reference pipeline archive
```

### 2.4 Phase 0 数据契约审计完成

已对 `data/Bragging_data.json` 和官方评测规范、文件及脚本进行完整审计。产出审计文档 [PROJECT_CONTRACT_AUDIT.md](file:///Users/mm/Desktop/BRAG-Pipeline-main/humble-brag-competition/PROJECT_CONTRACT_AUDIT.md) 并更新至 README.md 相关文档列表。
- 确认了当前数据字段、官方输入/输出 7 字段、合法标签和字数、模式等约束。
- 明确了当前 `Bragging_data.json` 与官方 `dev_input.jsonl` 不匹配的现状与数据读取策略。
- 规划了后续评测脚本提升方案与 Phase 1 baseline 最小实现建议。

### 2.5 Phase 1 最小 Baseline 已跑通

已新增：

```text
main.py
humble_brag/
scripts/format_checker.py
scripts/evaluate_dev.py
```

当前 baseline 是纯本地 heuristic pipeline，不依赖外部 API 或 LLM。

已验证运行：

| 运行 | 输出目录 | 格式检查 | 代理分数 |
| --- | --- | --- | --- |
| dev 3 条 smoke | `outputs/dev__20260521_004330_043__heuristic_baseline__max3` | valid, 0 warning | 49.565 |
| dev full 45 条 | `outputs/dev__20260521_004340_237__heuristic_baseline__full` | valid, 0 warning | 49.223 |
| test 3 条 smoke | `outputs/test__20260521_004154_200__heuristic_baseline__max3` | valid, 0 warning | not run |

full dev 指标：

| 指标 | 数值 |
| --- | --- |
| proxy_dev_score | 49.223 |
| mechanism_accuracy | 0.2667 |
| strategy_score | 0.6333 |
| risk_label_f1 | 0.5785 |
| response_reference_token_f1 | 0.1324 |

结论：Phase 1 的目标是跑通合法闭环，不追求高分。当前 baseline 已满足“可读取、可生成、可检查、可评分、可保存报告”的基础要求。

## 3. 现有代码状态

根目录现有代码主要是早期 Meta-String RAG 原型：

- `schema.py`：定义通用社交平台、关系、角色、互动目标等枚举和 `SocialContext`
- `rag.py`：基于 Meta-String + FAISS 的检索原型
- `data/Bragging_data.json`：当前数据文件

这些代码有参考价值，但还不是最终比赛 pipeline。主要问题：

1. schema 还偏通用社交助手，不完全对齐 BRAG 官方 7 字段输出。
2. RAG 原型没有接入完整生成、校验、评测、输出链路。
3. 当前文档中过去关于高分目标的表述需要降级为工程假设，不能当作已验证结论。
4. 需要先建立官方格式检查和 dev 评分闭环，再做复杂增强。

## 4. reference 中可复用内容

旧项目中较有价值的部分：

| 模块 | 可复用方式 |
| --- | --- |
| `reference/src/skillflow.py` | 后续可参考固定 SkillFlow 调度方式 |
| `reference/src/skills/` | 可参考机制、风险、策略、回复拆分 |
| `reference/src/llm_client.py` | 可参考 Ollama qwen 原生 `/api/chat` 适配 |
| `reference/src/postprocess.py` | 可参考输出清理和标签归一化 |
| `reference/BRAG-Agent-public/scripts/` | 可直接作为官方格式检查和 dev 评分来源 |
| `reference/PROJECT_OVERVIEW_REPORT.md` | 可查看旧实验指标和阶段记录 |

不建议直接搬运的部分：

- 旧目录里的整体工程结构
- 旧实验输出
- 没有完整 ablation 的 memory 规则
- 过度乐观的分数目标和未验证策略

## 5. 下一步重点

Phase 0 和 Phase 1 已完成。下一步工作重心是 Phase 2 Debug Trace 和 Phase 3 SkillFlow：

1. 为每条样本保存 trace，记录机制、策略、风险、回复和后处理动作。
2. 把 heuristic baseline 拆成可替换的 SkillFlow 接口。
3. 用同一套评测命令比较 baseline 与 SkillFlow。
4. 再考虑 few-shot / Meta-String retrieval。

## 6. 风险

- 当前 `data/Bragging_data.json` 与官方 JSONL 输入格式已确认不一致，不能直接作为 submission 输入。
- 如果先上复杂 RAG/memory，容易在 schema 未稳定时返工。
- 3 条 smoke score 或小样本 ablation 只能说明链路可跑，不能证明 hidden test 泛化。
- `reference/` 是归档，不应该被当作主线代码直接执行。
- 当前 baseline 只是低成本工程基线，proxy score 不高是预期结果。

## 7. 当前推荐结论

继续在当前新仓库做，但开发顺序必须是：

```text
official contract first
-> runnable baseline
-> trace and reports
-> SkillFlow
-> retrieval / memory
-> final freeze
```

当前已经完成前两步，下一步应补 trace 和 SkillFlow。
