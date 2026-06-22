# Shared Memory

## Project Status

- 当前阶段：Phase 0 完成，baseline 已冻结
- 当前目标：等待用户确认是否进入 Phase 1 日志改造
- 当前原则：先审计、再运行、再最小改造
- 禁止事项：不要直接大规模重构，不要直接启用 active memory，不要跳过评估

## 2026-06-09 - Phase 0 项目审计与 Baseline 冻结

### 当前状态
- 项目结构审计完成 ✅
- Git 状态审计完成 ✅
- 单元测试 28/28 全部通过 ✅
- 三个模型 dev baseline 全部完成 ✅
- 代码修改：`src/llm_client.py` 兼容 qwen3 reasoning 字段

### 已完成
- ✅ 读取所有项目文档和代码
- ✅ Git 状态检查：当前分支 `merged-branch-sanitized` 与远程同步
- ✅ 远程更新审计：`origin/main` 是不相关项目，不建议合并
- ✅ 项目结构审计：完整 SkillFlow 架构，7 个 skill，48 条 memory，500 条 train
- ✅ 代码审计：所有核心模块已阅读和理解
- ✅ 单元测试：28 个测试全部通过
- ✅ 依赖检查：openai 2.30.0 和 python-dotenv 已安装
- ✅ 创建 `.env` 文件（ollama 本地服务）
- ✅ 修改 `src/llm_client.py` 兼容 qwen3 reasoning 字段
- ✅ 运行 qwen3:8b dev baseline → proxy_dev_score=55.685
- ✅ 运行 glm4:9b dev baseline → proxy_dev_score=69.29
- ✅ 运行 gemma3:12b dev baseline → proxy_dev_score=72.021
- ✅ 输出 GIT_UPDATE_AUDIT.md
- ✅ 输出 PROJECT_AUDIT.md
- ✅ 输出 BASELINE_RUN_REPORT.md（已更新为三模型对比）

### 关键文件
- `main.py`: 唯一入口
- `config.py`: 运行配置（已恢复 RUN_MODE="smoke"）
- `src/llm_client.py`: 已修改，兼容 qwen3 reasoning
- `src/pipeline.py`: 主流程编排
- `src/skillflow.py`: SkillFlow 控制器
- `outputs/dev_20260610_001538_qwen3_8b/`: qwen3:8b 结果
- `outputs/dev_20260610_012742_glm4_9b/`: glm4:9b 结果
- `outputs/dev_20260610_024534_gemma3_12b/`: gemma3:12b 结果（最佳）

### 运行结果

| 模型 | proxy_dev_score | mechanism_accuracy | strategy_score | risk_label_f1 | response_f1 |
| -- | -- | -- | -- | -- | -- |
| **gemma3:12b** | **72.021** | **0.8222** | **0.7556** | 0.7296 | 0.1767 |
| glm4:9b | 69.29 | 0.7556 | 0.7111 | 0.7296 | 0.1872 |
| qwen3:8b | 55.685 | 0.3556 | 0.6667 | 0.7296 | 0.1395 |

### 当前阻塞
- 无 P0 阻塞
- gemma3:12b 推理速度较慢（~1 小时/45 条），test 409 条可能需要更长时间

### 下一步
1. 用户确认是否进入 Phase 1（日志改造）
2. 如需继续，首选 gemma3:12b 作为主力模型
3. Phase 1：增强 run_manifest 和 trace
4. Phase 2：错误分析，找出 mechanism 分类偏差
5. Phase 4：针对 mechanism_accuracy 调 prompt
