# BASELINE_RUN_REPORT.md

## 1. 环境信息

- 当前路径：`/Users/mm/Desktop/BRAG-Pipeline-main-cc`
- 当前分支：`phase0-baseline`
- Python 版本：`3.13.5`
- pip 版本：`26.0.1`
- 虚拟环境：miniconda3 全局环境
- 依赖：openai 2.30.0, python-dotenv ✅
- LLM 后端：本地 ollama（`http://localhost:11434/v1`）

## 2. 运行命令来源

- 运行命令来自 README.md：`python main.py`
- `config.py` 设 `RUN_MODE = "dev"`（45 条 dev 数据）
- 每个模型单独设置 `.env` 中的 `OPENAI_MODEL`

## 3. 已执行命令记录

| 序号 | 命令 | 目的 | 结果 | 备注 |
| -- | -- | -- | -- | -- |
| 1 | `python3 -m pytest tests/test_pipeline.py -v` | 单元测试 | ✅ 28 passed | 0.32s |
| 2 | `python3 main.py` (qwen3:8b) | dev baseline | ✅ 完成 | proxy_dev_score=55.685 |
| 3 | `python3 main.py` (glm4:9b) | dev baseline | ✅ 完成 | proxy_dev_score=69.29 |
| 4 | `python3 main.py` (gemma3:12b) | dev baseline | ✅ 完成 | proxy_dev_score=72.021 |

## 4. 依赖安装结果

- openai 2.30.0 ✅
- python-dotenv ✅
- ollama 本地服务 ✅

## 5. 代码修改

为兼容 qwen3:8b 的 thinking 模式，修改了 `src/llm_client.py`：
- 当 `content` 为空但 `reasoning` 非空时，使用 `reasoning` 字段作为回复内容
- 这是 ollama OpenAI-compatible API 的已知行为

## 6. 三模型 Baseline 对比

| 模型 | proxy_dev_score | mechanism_accuracy | strategy_score | risk_label_f1 | response_reference_token_f1 |
| -- | -- | -- | -- | -- | -- |
| **gemma3:12b** | **72.021** | **0.8222** | **0.7556** | 0.7296 | 0.1767 |
| glm4:9b | 69.29 | 0.7556 | 0.7111 | 0.7296 | 0.1872 |
| qwen3:8b | 55.685 | 0.3556 | 0.6667 | 0.7296 | 0.1395 |

### 关键发现

1. **gemma3:12b 表现最好**：proxy_dev_score 72.021，机制准确率 82.22%
2. **glm4:9b 紧随其后**：proxy_dev_score 69.29，response_reference_token_f1 最高（0.1872）
3. **qwen3:8b 表现最差**：机制准确率仅 35.56%，主要瓶颈在机制分类
4. **risk_label_f1 三个模型相同**（0.7296）：因为 RiskSkill 是纯规则，不依赖 LLM
5. **strategy_score 差异不大**：因为 StrategySkill 也是纯规则矩阵
6. **主要差异来自 mechanism_accuracy**：LLM 分类能力是核心瓶颈

### 各模型详细统计

#### gemma3:12b（最佳）
- 格式检查：通过
- 机制缓存命中：19
- 机制复核调用：6
- 兜底次数：2

#### glm4:9b
- 格式检查：通过
- 机制缓存命中：19
- 机制复核调用：6
- 兜底次数：2
- 回复风险复查：7 次 strategy_inconsistency, 4 次 overpraise

#### qwen3:8b
- 格式检查：通过
- 机制缓存命中：19
- 机制复核调用：26（最多）
- 兜底次数：1
- 机制校准变化：other -> comparison_superiority (7), other -> faux_modesty (4)

## 7. Format Checker 结果

- 三个模型全部通过格式检查
- 无 warning

## 8. Dev Evaluator 结果

评分公式：`100 * (0.30 * mechanism_accuracy + 0.20 * strategy_score + 0.20 * risk_label_f1 + 0.15 * response_reference_token_f1 + 0.15 * format_score)`

| 模型 | 总分 | 机制(0.30) | 策略(0.20) | 风险(0.20) | 回复(0.15) | 格式(0.15) |
| -- | -- | -- | -- | -- | -- | -- |
| gemma3:12b | 72.02 | 24.67 | 15.11 | 14.59 | 2.65 | 15.0 |
| glm4:9b | 69.29 | 22.67 | 14.22 | 14.59 | 2.81 | 15.0 |
| qwen3:8b | 55.69 | 10.67 | 13.33 | 14.59 | 2.09 | 15.0 |

## 9. 当前阻塞问题

| 优先级 | 问题 | 说明 |
| -- | -- | -- |
| P2 | qwen3:8b 机制分类差 | 可能需要调整 prompt 或增加 few-shot |
| P2 | response_reference_token_f1 普遍偏低 | 回复与 reference 重叠少，但这是 proxy 指标 |
| P3 | gemma3:12b 推理速度慢 | 8.1GB 模型，45 条 dev 约需 1 小时 |

## 10. 下一步建议

1. **选定模型**：gemma3:12b 为当前最佳，建议作为主力模型
2. **Phase 1**：增强 run_manifest 和 trace，不改模型输出
3. **Phase 2**：分析 dev 错误，找出 mechanism 分类的系统性偏差
4. **Phase 4**：针对 mechanism_accuracy 调 prompt（gemma3:12b 已经 82%，提升空间有限）
5. **考虑**：是否需要测试更大模型（如 qwen3:14b）或微调

## 11. 输出文件索引

| 模型 | 输出目录 |
| -- | -- |
| qwen3:8b | `outputs/dev_20260610_001538_qwen3_8b/` |
| glm4:9b | `outputs/dev_20260610_012742_glm4_9b/` |
| gemma3:12b | `outputs/dev_20260610_024534_gemma3_12b/` |
