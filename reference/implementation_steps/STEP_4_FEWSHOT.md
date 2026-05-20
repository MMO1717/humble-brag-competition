# Step 4：Few-shot

## 目标

从 `train.jsonl` 检索相似样本，将少量示例注入对应 Skill 的 prompt，提高机制分类和回复风格稳定性。

Few-shot 是当前阶段比 LoRA 更现实的增强方式，成本低、可回滚、可做 ablation。

## 实现范围

核心模块：

```text
src/fewshot.py
```

默认检索特征：

- `speaker_post` token overlap
- `platform`
- `relationship`
- `agent_role`
- `interaction_goal`

默认注入位置：

| Skill | few-shot 用途 |
| --- | --- |
| MechanismSkill | 机制标签边界判断 |
| ResponseSkill | 学习回复风格和策略匹配 |

暂时不建议给所有 Skill 都注入 few-shot，避免 prompt 太长和逻辑漂移。

## 配置项

```python
USE_FEWSHOT = True
FEWSHOT_K = 2
FEWSHOT_MIN_SCORE = 0.0
FEWSHOT_INCLUDE_FIELDS = True
```

## 产物

```text
outputs/<run_id>/debug/trace.jsonl
```

其中每条 trace 应记录：

```json
{
  "fewshot_examples": {
    "mechanism": [],
    "response": []
  }
}
```

## 验证命令

对比无 few-shot：

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=None; config.USE_FEWSHOT=False; config.RUN_DEV_ERROR_ANALYSIS=False; run_pipeline(config)"
```

对比有 few-shot：

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=None; config.USE_FEWSHOT=True; config.FEWSHOT_K=2; config.RUN_DEV_ERROR_ANALYSIS=False; run_pipeline(config)"
```

## 通过标准

- 有 few-shot 和无 few-shot 都能通过格式检查
- `trace.jsonl` 能看到检索到的示例
- 完整 dev 上至少不明显损害 mechanism、strategy、risk 三个关键指标
- 如果 response token F1 提升但策略或 risk 明显下降，需要谨慎保留

## 风险点

- few-shot 选到相似文本但错误策略，误导模型
- few-shot 太多导致 prompt 噪音过大
- 模型复制训练集回复，降低泛化
- 只优化 dev token overlap，隐藏测试表现不一定提升

## 完成标志

当 few-shot 能稳定被检索、注入、记录，并且 ablation 显示它没有破坏关键指标时，进入 Step 5。
