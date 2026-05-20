# Humble Brag Competition

本仓库是 BRAG / humble-brag response 任务的新主线仓库。当前目标不是继续在旧实验目录上堆功能，而是先建立一个干净、可验证、可回滚的 pipeline 骨架，再把已经验证过的旧成果逐步移植进来。

## 当前状态

更新时间：2026-05-21

- 当前远端：`https://github.com/MMO1717/humble-brag-competition.git`
- 当前分支：`new`
- 旧 BRAG-Pipeline 实验工程已整理到 `reference/`
- `reference/` 只作为参考归档，不作为后续主线开发目录
- 根目录现有 `schema.py`、`rag.py` 是早期 Meta-String RAG 原型，需要按比赛真实输入/输出协议重构
- Phase 0 数据契约审计已完成，详见 `PROJECT_CONTRACT_AUDIT.md`
- Phase 1 最小 heuristic baseline 已跑通，可通过 `python3 main.py --mode dev` 生成并评测

## 目录说明

```text
.
├── data/
│   └── Bragging_data.json
├── reference/
│   └── old BRAG-Pipeline archive
├── humble_brag/
│   └── baseline pipeline package
├── scripts/
│   ├── format_checker.py
│   └── evaluate_dev.py
├── outputs/
│   └── ignored run artifacts
├── main.py
├── rag.py
├── schema.py
├── requirements.txt
├── README.md
├── report.md
└── task.md
```

`reference/` 已排除 `.env`、`.git`、`.venv`、`outputs`、`__pycache__` 等本地运行产物。它保留旧项目源码、阶段文档和官方脚本副本，用于查阅旧实验结论。

## 开发原则

1. 先搭稳大框架，再逐步增强。
2. 每一步必须有明确输入、输出、验证命令和回滚边界。
3. 不把 public dev proxy score 当成 hidden test 结论。
4. 不直接搬旧项目整套实现，只移植经过验证且边界清晰的模块。
5. 最终提交链路优先保证格式、标签、字段和评测脚本兼容。

## 推荐主线

第一阶段先实现一个扎实的最小 pipeline：

```text
load data
-> normalize input
-> generate required fields
-> validate schema and labels
-> write jsonl
-> run official format/eval checks
-> save run report
```

当前最小 baseline 已实现，运行方式：

```bash
python3 main.py --mode dev --max-items 3
python3 main.py --mode dev
python3 main.py --mode test --max-items 3
```

每次运行会在 `outputs/` 下生成唯一目录，包含 `submission.jsonl`、`input_subset.jsonl`、`run_manifest.json`、`format_report.json`、`RES.md`，dev 模式还会包含 `dev_eval_report.json`。

之后再加入：

- SkillFlow 拆分
- debug trace
- few-shot / Meta-String retrieval
- active memory
- error analysis
- local judge review and ablation

## 相关文档

- [PROJECT_CONTRACT_AUDIT.md](file:///Users/mm/Desktop/BRAG-Pipeline-main/humble-brag-competition/PROJECT_CONTRACT_AUDIT.md)：Phase 0 项目输入/输出契约与数据审计报告
- [report.md](file:///Users/mm/Desktop/BRAG-Pipeline-main/humble-brag-competition/report.md)：当前项目状态、旧实验归档说明、下一步判断
- [task.md](file:///Users/mm/Desktop/BRAG-Pipeline-main/humble-brag-competition/task.md)：分阶段任务清单和验收标准
- [PROJECT_OVERVIEW_REPORT.md](file:///Users/mm/Desktop/BRAG-Pipeline-main/humble-brag-competition/reference/PROJECT_OVERVIEW_REPORT.md)：旧 BRAG-Pipeline 实验纵览
- [CURRENT_AGENT_CHANGELOG.md](file:///Users/mm/Desktop/BRAG-Pipeline-main/humble-brag-competition/reference/CURRENT_AGENT_CHANGELOG.md)：旧实验变更记录
