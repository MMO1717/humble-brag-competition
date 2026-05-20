# Humble Brag Competition

本仓库是 BRAG / humble-brag response 任务的新主线仓库。当前目标不是继续在旧实验目录上堆功能，而是先建立一个干净、可验证、可回滚的 pipeline 骨架，再把已经验证过的旧成果逐步移植进来。

## 当前状态

更新时间：2026-05-21

- 当前远端：`https://github.com/MMO1717/humble-brag-competition.git`
- 当前分支：`new`
- 旧 BRAG-Pipeline 实验工程已整理到 `reference/`
- `reference/` 只作为参考归档，不作为后续主线开发目录
- 根目录现有 `schema.py`、`rag.py` 是早期 Meta-String RAG 原型，需要按比赛真实输入/输出协议重构

## 目录说明

```text
.
├── data/
│   └── Bragging_data.json
├── reference/
│   └── old BRAG-Pipeline archive
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

之后再加入：

- SkillFlow 拆分
- debug trace
- few-shot / Meta-String retrieval
- active memory
- error analysis
- local judge review and ablation

## 相关文档

- `report.md`：当前项目状态、旧实验归档说明、下一步判断
- `task.md`：分阶段任务清单和验收标准
- `reference/PROJECT_OVERVIEW_REPORT.md`：旧 BRAG-Pipeline 实验纵览
- `reference/CURRENT_AGENT_CHANGELOG.md`：旧实验变更记录
