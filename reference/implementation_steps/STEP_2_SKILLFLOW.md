# Step 2：SkillFlow

## 目标

把一次性生成拆成多个可控 Skill，由固定 SkillFlow 串起来，降低模型同时处理多个目标时的混乱。

推荐流程：

```text
Input Row
  ↓
Context / Understanding
  ↓
Mechanism
  ↓
Risk
  ↓
Strategy
  ↓
Response
  ↓
Validator
  ↓
Rewriter if needed
  ↓
Final Output
```

## 实现范围

核心模块：

```text
src/skillflow.py
src/skills/base.py
src/skills/mechanism_skill.py
src/skills/understanding_skill.py
src/skills/risk_skill.py
src/skills/strategy_skill.py
src/skills/response_skill.py
src/skills/validator_skill.py
src/skills/rewriter_skill.py
```

每个 Skill 只负责一个子任务：

| Skill | 职责 |
| --- | --- |
| MechanismSkill | 机制分类 |
| UnderstandingSkill | 说话人意图和期望反馈 |
| RiskSkill | 风险标签和风险说明 |
| StrategySkill | 回复策略选择 |
| ResponseSkill | 生成最终英文回复 |
| ValidatorSkill | 检查字段、enum、长度、hidden reasoning |
| RewriterSkill | 只修复不合法字段 |

## 设计原则

- 使用固定顺序，不使用自由规划 Agent。
- 模型不直接生成最终整行 JSONL。
- 最终 JSONL 由 Python dict 组装。
- 每个 Skill 失败时只记录错误并提供兜底值，不中断整批运行。
- Validator 和 Rewriter 是最终稳定性的底线。

## 暂不做

- 不让 response prompt 同时决定所有字段
- 不做动态 Skill 编排
- 不在 SkillFlow 中引入外部 API
- 不在 test 阶段生成或更新 memory

## 产物

```text
src/skillflow.py
src/skills/*.py
outputs/<run_id>/submission.jsonl
outputs/<run_id>/RES.md
```

## 验证命令

Step 2 验证的是纯 SkillFlow 效果，因此需要关闭 few-shot、agent wiki 和 error analysis：

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -m py_compile main.py src/*.py src/skills/*.py
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=3; config.USE_SKILLFLOW=True; config.USE_FEWSHOT=False; config.USE_AGENT_WIKI=False; config.RUN_DEV_ERROR_ANALYSIS=False; run_pipeline(config)"
```

完整 dev：

```bash
cd /Users/mm/Desktop/BRAG-Pipeline-main
python3 -c "from pathlib import Path; from src.llm_client import load_env; from src.pipeline import run_pipeline; import config; load_env(Path('.env')); config.MODE='dev'; config.INPUT_PATH=config.INPUT_PATH_BY_MODE['dev']; config.MAX_ITEMS=None; config.USE_SKILLFLOW=True; config.USE_FEWSHOT=False; config.USE_AGENT_WIKI=False; config.RUN_DEV_ERROR_ANALYSIS=False; run_pipeline(config)"
```

## 通过标准

- 每条样本按固定 Skill 顺序执行
- Skill 出错时不会中断整批运行
- Validator 能拦住非法字段和 hidden reasoning
- Rewriter 或 fallback 能保证最终 submission 格式合法
- 3 条冒烟测试和完整 dev 都能跑通

## 风险点

- Skill 拆得过细导致调用次数过多、推理过慢
- 前置 Skill 错误传导到后续 Skill
- StrategySkill 过度依赖规则，灵活性不足
- ResponseSkill 忽略前面 Skill 的中间结果

## 完成标志

当 SkillFlow 能稳定跑通 dev，并且错误定位能明确归因到具体 Skill 时，进入 Step 3。

## 当前完成记录

Step 2 已完成本地验证。

### 3 条 dev 冒烟测试

运行目录：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/outputs/dev__20260518_195714_715__qwen3_8b__max3__temp0p3__tok256
```

结果：

| 指标 | 数值 |
| --- | --- |
| row_count | 3 |
| format_checker | valid |
| warning_count | 0 |
| proxy_dev_score | 87.738 |
| mechanism_accuracy | 1.0 |
| strategy_score | 1.0 |
| risk_label_f1 | 1.0 |
| response_reference_token_f1 | 0.1825 |

### 完整 dev 运行

运行目录：

```text
/Users/mm/Desktop/BRAG-Pipeline-main/outputs/dev__20260518_195747_298__qwen3_8b__full__temp0p3__tok256
```

结果：

| 指标 | 数值 |
| --- | --- |
| row_count | 45 |
| format_checker | valid |
| warning_count | 0 |
| proxy_dev_score | 64.284 |
| mechanism_accuracy | 0.6444 |
| strategy_score | 0.6222 |
| risk_label_f1 | 0.7407 |
| response_reference_token_f1 | 0.1794 |

`run_manifest.json` 已确认：

```text
flow_name = SkillFlow
use_skillflow = true
use_agent_wiki = false
use_fewshot = false
run_dev_error_analysis = false
```

`debug/trace.jsonl` 已确认 45 条样本都按固定 Skill 顺序执行：

```text
MechanismSkill -> UnderstandingSkill -> RiskSkill -> StrategySkill -> ResponseSkill -> ValidatorSkill
```

与 Step 1 Baseline 对比：

| 阶段 | proxy_dev_score | mechanism | strategy | risk | response |
| --- | --- | --- | --- | --- | --- |
| Step 1 Baseline | 48.559 | 0.2444 | 0.4889 | 0.6815 | 0.1879 |
| Step 2 SkillFlow | 64.284 | 0.6444 | 0.6222 | 0.7407 | 0.1794 |

结论：Step 2 的目标已经达成。SkillFlow 在不使用 few-shot 和 wiki 的情况下，显著提升了 mechanism、strategy 和 risk 三个核心指标，同时保持格式检查 0 error / 0 warning。
