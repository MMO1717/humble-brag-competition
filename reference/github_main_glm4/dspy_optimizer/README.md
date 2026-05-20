# DSPy 优化器

这是可选实验层，不影响主 pipeline。

主工程仍然使用：

```bash
python main.py
```

DSPy 相关脚本只用于离线优化 prompt、few-shot 或模块配置。优化结果会写入 `exports/`，不会自动覆盖 `src/prompts.py` 或 `agent_memory/active/memory.jsonl`。

## 第一阶段目标

- 优先优化 `MechanismSkill`。
- 使用 `train.jsonl` 切分 internal train/validation。
- dev 只作为最终参考，避免围绕 dev 过拟合。

## 安装

```bash
pip install -r dspy_optimizer/requirements-dspy.txt
```

未安装 DSPy 不影响主 pipeline。
