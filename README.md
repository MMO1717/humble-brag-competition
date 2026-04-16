# Emotional Agent Project (Phase 2.5 -> 3.0)

本项目旨在构建一个具备情绪感知与状态转换的多智能体辩论框架（Multi-Agent Debate, MAD）。通过融合语义分析与生理信号（EEG），优化智能体之间的协作效率与真理纠偏能力。

## 目录结构

- **`agent_test.py`**: 项目早期的单智能体原型脚本。使用 Gemini SDK 测试 COSTAR-E 提示词模块及其“防盲从”判定。
- **`phase2_5/`**: 当前核心开发目录，包含完整的多智能体协作、判决与评估体系。
- **`phase2/`**: 历史实验版本。

## 核心架构 (Phase 2.5+)

项目主要位于 `phase2_5/` 目录下，采用模块化设计：

- **`agents.py` (Stateful Agents)**: 实现带有情绪状态机的智能体（Alpha & Beta）。包含四种核心状态：`Neutral`, `Skeptical`, `Aggressive`, `Encouraging`。代码遵循 **S²-MAD** (Self-Summarizing MAD) 压缩原则，强制缩减 Token 消耗。
- **`curator.py` (iMAD Curator)**: 判决层。使用 **iMAD** (Intelligent MAD) 半自适应动态阈值判定“懒惰共识”。结合了语义相似度、输出长度及轮次退火策略。
- **`evaluator.py` (FORGE Evaluator)**: 评估层。基于 **FORGE** 进化框架理论实现奖励函数（R-score）。具备“难度感知”能力：难题答对奖励更高，Token 惩罚更轻。
- **`mas_controller.py` (Controller)**: 核心控制器。管理多轮对话逻辑、状态跃迁及 **Node Dropout** (共识达成后的节点剔除)。
- **`eeg_sensor.py` (Physio-Data Bus)**: 生理信号总线。对接 TGAM-Glas 硬件或 Mock 生成人类专注度数据。

## 当前工程状态：Phase 3.1 (Prompt 专注模式)

> [!IMPORTANT]
> **当前 EEG 屏蔽状态**：由于当前阶段专攻 Prompt 调优且无 EEG 硬件，所有与“电波/生理信号”相关的逻辑已执行**软屏蔽**（隐藏而非删除）。
> 
> - **屏蔽手段**：`eeg_sensor.py` 线程静默，`curator.py` 强制跳过生理判定，`evaluator.py` 的 `GAMMA` 权重归零。
> - **后续建议**：恢复 EEG 逻辑只需解开相应注释并恢复 `GAMMA` 权重（详见 `walkthrough.md` 或各文件内部 `[PROMPT-ONLY MODE]` 标签）。

## 运行与测试

- **`test_small_batch.py`**: 当前主要压测脚本。运行 10 题 KKS 逻辑题，验证 S²-MAD、iMAD 和 FORGE 的修改效果。
- **`run_kks_full_benchmark.py`**: KKS 全量数据集自动化跑批工具。
- **`run_benchmarks.py`**: 基础功能回归测试。

## 开发者提示

- **Token 降本**：修改 Agent 系统提示词时，务必遵循 `BASE_SYS_PROMPT` 中的 120 字 `<Rationale>` 限制。
- **Bug 修复记录**：`mas_controller.py` 曾出现过第一轮 `d_sem` 未定义的 `UnboundLocalError`，现已通过调整 `d_sem_history.append` 顺序修复。
- **配置信息**：API KEY 及 Model ID (qwen3.5-27b) 已在运行脚本中硬编码配置。

---
*本项目持续迭代中，修改涉及核心逻辑后请同步更新此 README。*
