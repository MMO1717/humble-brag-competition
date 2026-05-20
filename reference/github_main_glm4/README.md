# BRAG-Pipeline：Understander–Responder Social Agent

这是 CCAC 2026 赛道四 BRAG-Agent 的工程版 pipeline。它读取官方 JSONL 输入，调用 OpenAI-compatible chat completions 接口，再由 Python dict 组装官方 7 字段 JSONL 输出。

当前主线是 v2 SkillFlow，并已经吸收 v1 高分分支里的通用优化：机制校准、策略矩阵、风险规范化、回复审查和离线防过拟合检查。v1 分支只作为参考来源，没有直接合并。

```text
复制 .env.example -> 修改 config.py -> python main.py
```

## 1. 安装依赖

```bash
cd brag_pipeline
pip install -r requirements.txt
```

主依赖仍然只有：

```text
openai
python-dotenv
```

DSPy 在 `dspy_optimizer/`，不进入主流程，不影响 `python main.py`。

## 2. 配置模型

在 `.env` 中配置：

```env
OPENAI_BASE_URL=http://localhost:5001/v1
OPENAI_API_KEY=sk-local
OPENAI_MODEL=your-model-name
```

KoboldCpp、SiliconFlow、本地 OpenAI-compatible 服务都按 `/v1/chat/completions` 兼容接口使用。

## 3. 常用配置

主要改 `config.py`：

```python
MODE = "dev"          # dev / test
MAX_ITEMS = 3         # 冒烟测试；完整 dev/test 改成 None

MEMORY_MODE = "no_memory"
AUTO_PROMOTE_CANDIDATE_MEMORY = False

RUN_OFFICIAL_FORMAT_CHECK = True
RUN_DEV_EVAL = True
RUN_DEV_ERROR_ANALYSIS = True
```

远程 API 有 RPM/TPM 限制时，打开本地限速：

```python
ENABLE_API_RATE_LIMIT = True
API_REQUESTS_PER_MINUTE = 500
API_TOKENS_PER_MINUTE = 40000
API_RATE_LIMIT_SAFETY_MARGIN = 0.8
```

本地模型保持 `ENABLE_API_RATE_LIMIT = False`。限速器只会在调用前等待，不会额外发请求；token 用 prompt 字符数和 `MAX_TOKENS` 粗估，所以安全系数不要设得太满。

推荐三种运行方式：

```python
# 冒烟测试
MODE = "dev"
MAX_ITEMS = 3
MEMORY_MODE = "no_memory"
AUTO_PROMOTE_CANDIDATE_MEMORY = False
```

```python
# 完整 dev
MODE = "dev"
MAX_ITEMS = None
MEMORY_MODE = "no_memory"
RUN_DEV_EVAL = True
RUN_DEV_ERROR_ANALYSIS = False
GENERATE_CANDIDATE_MEMORY = False
```

```python
# test 提交
MODE = "test"
MAX_ITEMS = None
RUN_DEV_EVAL = False
RUN_DEV_ERROR_ANALYSIS = False
```

## 4. 一键运行

```bash
python main.py
```

每次运行会在 `outputs/` 下生成一个独立文件夹：

```text
outputs/<mode>__<time>__<model>__<size>__temp...__tok.../
```

优先看：

```text
RES.md
submission.jsonl
format_report.json
dev_eval_report.json
run_manifest.json
debug/trace.jsonl
```

`RES.md` 会显示本次分数、格式检查、配置和文件说明。`debug/trace.jsonl` 用来看每条样本的 mechanism、strategy、risk、response 和 Skill 轨迹。

## 5. Baseline 对比建议

做模型 baseline 时，建议固定代码和除模型外的所有配置：

```python
MODE = "dev"
MAX_ITEMS = None
USE_STATIC_MEMORY = True
MEMORY_MODE = "no_memory"
USE_FEWSHOT = True
FEWSHOT_K = 2
RUN_DEV_EVAL = True
RUN_DEV_ERROR_ANALYSIS = False
GENERATE_CANDIDATE_MEMORY = False
AUTO_PROMOTE_CANDIDATE_MEMORY = False
SAVE_DEBUG_TRACE = True
SAVE_LLM_CALL_LOGS = False
```

然后每次只改 `.env` 里的 `OPENAI_MODEL`。远程 API 打开 `ENABLE_API_RATE_LIMIT`，本地模型关闭。

建议记录表格：

| 模型 | run_id | Proxy Dev | Mechanism | Strategy | Risk F1 | Response F1 | 备注 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| THUDM/GLM-4-9B-0414 |  |  |  |  |  |  |  |
| THUDM/GLM-Z1-9B-0414 |  |  |  |  |  |  |  |
| Qwen/Qwen3-14B |  |  |  |  |  |  |  |

分数从每次输出目录的 `RES.md` 或 `dev_eval_report.json` 里抄。`run_manifest.json` 会保存本次模型名、限速配置和关键参数，方便之后复查。

## 6. 当前架构

固定 SkillFlow：

```text
Input row
-> MechanismSkill
-> UnderstandingSkill
-> StrategySkill
-> RiskSkill
-> ResponseSkill
-> ValidatorSkill
-> RewriterSkill if needed
-> Final output row
```

核心模块：

- `src/skills/`：各阶段 Skill。
- `src/postprocess.py`：机制校准、风险规范化、回复清洗、fallback 回复。
- `src/strategy_rules.py`：v1 移植来的通用策略矩阵。
- `src/social_rubric.py`：回复审查器，拦截过夸、说教、策略不一致等硬伤。
- `agent_memory/static/`：静态知识目录。
- `agent_memory/candidate/`：错误分析生成的候选动态记忆。
- `agent_memory/active/`：人工确认后启用的动态记忆。

最终输出仍然只能包含官方 7 字段：

```text
episode_id
bragging_mechanism
speaker_intention
desired_feedback
risk_assessment
response_strategy
response_text
```

`episode_id` 始终从输入复制。最终 JSONL 始终由 Python dict + `json.dumps(..., ensure_ascii=False)` 写出。

## 7. v1 高分优化如何生效

本工程没有合并 v1 pipeline，而是把有效规则移植到 v2：

- `MechanismSkill`：LLM 先分类，再用 `calibrate_mechanism()` 做通用 cue 校准。
- `StrategySkill`：使用 `platform + relationship + interaction_goal + mechanism` 策略矩阵。
- `RiskSkill`：使用 `normalize_risk_assessment()` 规则渲染风险文本，保证风险关键词稳定可抽取。
- `ResponseSkill`：先保留模型回复；若 `judge_row()` 发现 hard issue，再使用 generalized fallback。

这几个规则不引用 dev episode id、实体名或 reference response，目标是可泛化，而不是硬背 dev。

## 8. Memory 用法

默认：

```python
MEMORY_MODE = "no_memory"
AUTO_PROMOTE_CANDIDATE_MEMORY = False
```

这表示动态记忆不参与主线分数，先保住稳定 baseline。

跑完完整 dev 后，错误分析会生成候选记忆：

```text
agent_memory/candidate/memory_candidates.jsonl
agent_memory/candidate/candidate_review.md
```

要实验动态记忆：

```python
MEMORY_MODE = "active"
AUTO_PROMOTE_CANDIDATE_MEMORY = False
```

然后手动把确认过的候选整理到：

```text
agent_memory/active/memory.jsonl
```

不建议默认打开自动晋级。若必须打开，当前规则要求：

- `schema_ok=True`
- `confidence >= AUTO_PROMOTE_MIN_CONFIDENCE`
- 没有 review warning
- `conditions` 非空
- 类型在 `AUTO_PROMOTE_ALLOWED_MEMORY_TYPES` 白名单内

具体记忆内容已被 `.gitignore` 忽略，仓库只提交框架，不提交本地经验。

## 9. 官方检查与评分

冒烟测试时会生成 `input_subset.jsonl`，可手动检查：

```bash
cd BRAG-Agent-public
python scripts/format_checker.py ../outputs/<run_id>/submission.jsonl ../outputs/<run_id>/input_subset.jsonl
```

完整 dev 手动评分：

```bash
cd BRAG-Agent-public
python scripts/evaluate_dev.py data/dev_input.jsonl data/dev_gold.jsonl ../outputs/<run_id>/submission.jsonl
```

test 只有格式检查，没有公开 gold：

```bash
cd BRAG-Agent-public
python scripts/format_checker.py ../outputs/<run_id>/submission.jsonl data/test_input.jsonl
```

dev 代理评分不等于隐藏 test 标准，只用于本地迭代。

## 10. 离线防过拟合检查

这个检查不调用 API：

```bash
python scripts/run_no_overfit_offline_checks.py
```

它会检查：

- 机制 cue 校准是否正常。
- 策略矩阵样例是否符合预期。
- 风险文本是否包含可抽取关键词。
- 回复审查器是否能拦截硬伤。
- 代码里是否混入高风险 dev-specific keyword。
- fallback 回复是否有基本多样性。

输出在：

```text
outputs/no_overfit_offline/
```

该目录不进 git。

## 11. Prompt 位置

主要 prompt 在：

```text
src/prompts.py
```

优先改对应 builder：

- `build_mechanism_prompt()`
- `build_understanding_prompt()`
- `build_response_prompt()`
- `format_fewshot_examples()`

策略和风险现在主要由规则层控制，不建议只靠 prompt 修。

## 12. dev 代理评分公式

官方公开 `evaluate_dev.py` 的 proxy 分数：

```text
100 * (
  0.30 * mechanism_accuracy
  + 0.20 * strategy_score
  + 0.20 * risk_label_f1
  + 0.15 * response_reference_token_f1
  + 0.15 * format_score
)
```

各项含义：

- `mechanism_accuracy`：`bragging_mechanism` 完全匹配 gold。
- `strategy_score`：命中 preferred 得 1.0，命中 acceptable 得 0.5。
- `risk_label_f1`：从 `risk_assessment` 字符串抽取风险关键词后和 gold 算 F1。
- `response_reference_token_f1`：回复和参考回复的 token overlap F1。
- `format_score`：格式通过为 1.0，不通过则提交无效。
