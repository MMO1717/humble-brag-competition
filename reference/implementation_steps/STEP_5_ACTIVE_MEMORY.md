# Step 5：Active Memory

## 目标

建立受控 memory 系统，让 Skill 能从 active memory 中动态检索泛化经验。

Active Memory 是正式推理链路唯一允许读取的 memory。它必须是经过评审、可回滚、可禁用的静态经验库。

## 实现范围

建议新增：

```text
src/memory/
  schemas.py
  memory_store.py
  memory_retriever.py

agent_memory/
  active_memory.jsonl
  disabled_memory.jsonl
  rejected_memory.jsonl
  memory_update_logs.jsonl
```

Memory schema 建议：

```json
{
  "memory_id": "label_humble_complaint_001",
  "type": "label_definition",
  "skill": "mechanism",
  "trigger": "complaint framing plus positive status signal",
  "content": "When complaint framing highlights an inconvenience that also signals recognition, privilege, or achievement, prefer humble_complaint.",
  "status": "active",
  "version": 1,
  "approved_by": "human_or_external_api_judge",
  "created_from": ["train_or_dev_error_pattern"],
  "notes": "General rule, not tied to one episode."
}
```

Memory 类型：

| Type | 主要服务 Skill |
| --- | --- |
| `label_definition` | MechanismSkill |
| `failure_pattern` | MechanismSkill / StrategySkill |
| `context_strategy` | StrategySkill |
| `risk_avoidance` | RiskSkill / ResponseSkill |
| `response_style` | ResponseSkill |
| `retrieval_policy` | Few-shot Retriever |

## 检索方式

先做简单可控检索，不急着上向量数据库：

- 按 `skill` 过滤
- 按 `type` 过滤
- 对 `speaker_post`、`platform`、`relationship`、`interaction_goal` 做 token overlap
- 每个 Skill 最多注入 `top_k=3`

## 配置项

```python
USE_AGENT_MEMORY = True
MEMORY_TOP_K = 3
ACTIVE_MEMORY_PATH = PIPELINE_DIR / "agent_memory" / "active_memory.jsonl"
```

## 产物

```text
agent_memory/active_memory.jsonl
outputs/<run_id>/debug/trace.jsonl
```

trace 中应记录：

```json
{
  "memory_examples": {
    "mechanism": [],
    "risk": [],
    "strategy": [],
    "response": []
  }
}
```

## 验证命令

无 memory：

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=None; config.USE_AGENT_MEMORY=False; run_pipeline(config)"
```

有 memory：

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=None; config.USE_AGENT_MEMORY=True; config.MEMORY_TOP_K=3; run_pipeline(config)"
```

## 通过标准

- active memory 能被读取和检索
- 每个 Skill 只拿到与自己相关的 memory
- memory 注入不会破坏格式检查
- 完整 dev 上关键指标不下降，尤其是 mechanism、strategy、risk
- memory 内容不包含具体 dev 答案复述

## 风险点

- memory 太多导致 prompt 变长
- memory 与 wiki 或规则冲突
- memory 本身过拟合 dev
- memory 触发条件太宽，导致错误泛化

## 完成标志

当 active memory 能进入 SkillFlow、可记录、可关闭、可对比，并且不会破坏 dev 关键指标时，进入 Step 6。
