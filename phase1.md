# Phase 1: Minimal LLM Pipeline Integration

## 1. Phase 1 目标

当前项目已经完成了纯规则 baseline，主要作用是跑通底层工程闭环：

```text
input jsonl
-> heuristic baseline generation
-> contract normalization
-> format checker
-> dev evaluator
-> RES.md
```

Phase 1 的目标不是继续深调规则 baseline，而是在已有底层框架可运行的基础上，接入一个最小可用的 LLM pipeline。

目标命令：

```bash
python3 main.py --mode dev --backend llm --max-items 3
python3 main.py --mode dev --backend llm
python3 main.py --mode test --backend llm --max-items 3
```

新的 LLM 运行链路应为：

```text
input jsonl
  -> LLM prompt
  -> raw model output
  -> JSON parse / repair
  -> contract normalization
  -> format checker
  -> dev evaluator
  -> trace / RES.md
```

核心原则：

- 先接入 LLM，让后续优化基于真实模型行为。
- 第一版 prompt 必须简单，不要塞大量 examples。
- 模型输出不能直接提交，必须经过 JSON parse / repair 和 contract normalization。
- 必须保存 trace，方便之后分析每条样本哪里出错。
- 暂时不要接 RAG / memory / few-shot 检索，避免一开始问题来源太复杂。

## 2. 当前 Baseline 的定位

不要删除现有 heuristic baseline。

现有 baseline 继续保留，作为：

- fallback
- 对照组
- 格式验证样例
- LLM 失败时的保底输出

建议 CLI 支持：

```bash
python3 main.py --mode dev --backend heuristic
python3 main.py --mode dev --backend llm
```

如果不传 `--backend`，默认继续使用 `heuristic`，避免破坏已有命令。

## 3. Pipeline 每一步说明

### 3.1 input jsonl

官方输入文件是 JSONL，每一行是一个样本，字段包括：

```text
episode_id
speaker_post
platform
relationship
agent_role
interaction_goal
```

pipeline 第一件事是逐行读取输入样本。

### 3.2 LLM prompt

把单条输入组织成给模型看的提示词。

第一版 prompt 只做最小指导：

- 告诉模型任务是什么。
- 给出合法 label 集合。
- 给出输入字段。
- 要求模型只输出 JSON。
- 禁止输出 Chain-of-Thought 或解释性推理。

不要在 Phase 1 加大量例子。

### 3.3 raw model output

这是模型最原始返回的文本。

理想情况是合法 JSON，但实际可能出现：

- JSON 前后有解释文本。
- Markdown code fence。
- 缺字段。
- label 拼错。
- 输出了推理过程。
- 输出不是合法 JSON。

所以 raw model output 不能直接作为 submission。

### 3.4 JSON parse / repair

这一层负责把模型原始文本尽量转换成 Python dict。

至少需要处理：

- 去掉 Markdown code fence。
- 从解释文本中抽取第一个 JSON object。
- 解析失败时不让整次运行崩掉。
- 解析失败时 fallback 到 heuristic baseline 或默认安全输出。

解析状态和错误原因必须写入 trace。

### 3.5 contract normalization

这是最关键的硬约束层。

最终输出必须符合官方 contract，只能包含 7 个字段：

```text
episode_id
bragging_mechanism
speaker_intention
desired_feedback
risk_assessment
response_strategy
response_text
```

需要强制检查：

- 字段是否完整。
- label 是否合法。
- 字数是否超限。
- 是否存在 `<think>` / `Thinking:` / `Reasoning:` 等推理泄露。
- `response_text` 是否太长。
- `no_response` 策略下是否过度热情。
- 字段缺失时是否能安全补齐。

模型只是候选答案生成器，最终提交文件必须来自 normalization 之后的结果。

### 3.6 format checker

调用官方 `scripts/format_checker.py`。

这一层只检查格式，不判断答案质量：

- JSONL 是否每行合法。
- 字段是否完整。
- 字段名是否正确。
- label 是否合法。
- 字数是否超限。

该步骤必须 100% 通过，否则提交无效。

### 3.7 dev evaluator

在 dev 模式下，调用官方 `scripts/evaluate_dev.py`。

它会输出当前 dev proxy 指标，例如：

- `mechanism_accuracy`
- `strategy_score`
- `risk_label_f1`
- `response_reference_token_f1`
- overall proxy score

这一层用于判断 LLM 版本是否比 heuristic baseline 更好。

### 3.8 trace / RES.md

`RES.md` 是整体运行报告，适合快速查看：

- backend
- prompt version
- input path
- output path
- trace path
- format checker status
- dev score
- fallback count
- parse failure count
- invalid label count

`trace` 是逐样本调试记录，不是提交文件。它的作用是记录每条样本从输入到最终输出的完整过程。

## 4. Trace 是什么

Trace 可以理解成每条样本的调试案卷。

建议输出路径：

```text
outputs/<run_id>/debug/trace.jsonl
```

每一行对应一个输入样本。

建议 trace 字段：

```json
{
  "episode_id": "dev_seed_000131_a",
  "backend": "llm",
  "prompt_version": "llm_a_minimal_v1",
  "input": {
    "speaker_post": "...",
    "platform": "...",
    "relationship": "...",
    "agent_role": "...",
    "interaction_goal": "..."
  },
  "prompt": "...",
  "raw_model_output": "...",
  "parse_status": "ok",
  "parse_error": null,
  "parsed_output": {
    "bragging_mechanism": "...",
    "speaker_intention": "...",
    "desired_feedback": "...",
    "risk_assessment": "...",
    "response_strategy": "...",
    "response_text": "..."
  },
  "normalized_output": {
    "episode_id": "...",
    "bragging_mechanism": "...",
    "speaker_intention": "...",
    "desired_feedback": "...",
    "risk_assessment": "...",
    "response_strategy": "...",
    "response_text": "..."
  },
  "fallback_used": false,
  "fallback_reason": null,
  "normalization_notes": []
}
```

Trace 的目的：

- 看模型原始输出是否稳定。
- 看 JSON 是否经常坏。
- 看 label 是否经常非法。
- 看 normalization 是否改坏模型答案。
- 看 prompt 是否让模型过度解释。
- 看 response 是否有 CoT 泄露。
- 看低分到底来自 prompt、模型、解析、后处理还是 evaluator 偏好。

没有 trace，只能看到最终分数；有 trace，才能逐条复盘问题发生在哪一步。

## 5. 需要新增或修改的模块

### 5.1 新增 `humble_brag/llm_client.py`

职责：

- 从环境变量读取 LLM 配置。
- 调用 OpenAI-compatible chat completion API。
- 返回模型原始文本。
- 处理超时、重试和基础异常。

建议支持环境变量：

```bash
LLM_BASE_URL
LLM_API_KEY
LLM_MODEL
LLM_TIMEOUT_SECONDS
LLM_MAX_RETRIES
```

第一版不要过度设计多 provider，只需要 OpenAI-compatible 接口。

### 5.2 新增 `humble_brag/prompts.py`

第一版 prompt 命名：

```text
llm_a_minimal_v1
```

Prompt 原则：

- zero-shot 或 near zero-shot。
- 不放大量 examples。
- 不要求模型解释推理。
- 明确要求只输出 JSON。
- 明确字段名。
- 明确合法 label 集合。
- 明确字数限制。
- 明确禁止 Chain-of-Thought。

### 5.3 新增 `humble_brag/json_repair.py`

职责：

- 从模型输出中提取 JSON object。
- 移除 Markdown code fence。
- 移除 JSON 前后的解释性文本。
- 尽量解析为 dict。
- 解析失败时返回 fallback dict，并在 trace 中记录失败原因。

### 5.4 修改 `humble_brag/runner.py`

增加 backend 分支：

```python
if backend == "heuristic":
    use existing baseline
elif backend == "llm":
    use llm pipeline
```

LLM pipeline 每条样本流程：

```text
row
-> build prompt
-> call llm
-> parse raw output
-> normalize output
-> append submission row
-> append trace row
```

### 5.5 修改 `main.py`

新增参数：

```bash
--backend heuristic|llm
```

默认值：

```bash
--backend heuristic
```

后续可以再加：

```bash
--prompt-version llm_a_minimal_v1
```

如果时间紧，prompt version 可以先写死，但 trace 里必须记录。

## 6. Prompt 第一版要求

第一版不要做复杂 prompt。

不要加入：

- 大量 examples。
- 774 条数据检索。
- RAG。
- memory。
- 长篇评分规则。
- 复杂 Chain-of-Thought 指令。

建议 prompt 结构：

```text
You are generating a valid JSON response for a humble-brag response task.

Given one social interaction, classify the bragging mechanism and choose a response strategy.

Do not reveal reasoning.
Do not include chain-of-thought.
Return only one JSON object.

Allowed bragging_mechanism labels:
...

Allowed response_strategy labels:
...

Input:
episode_id: ...
speaker_post: ...
platform: ...
relationship: ...
agent_role: ...
interaction_goal: ...

Return JSON with exactly these fields:
{
  "bragging_mechanism": "...",
  "speaker_intention": "...",
  "desired_feedback": "...",
  "risk_assessment": "...",
  "response_strategy": "...",
  "response_text": "..."
}
```

## 7. Fallback 策略

LLM pipeline 不能因为单条失败中断整次运行。

出现以下情况时，应 fallback：

- API 调用失败。
- 模型输出为空。
- JSON 解析失败。
- 输出字段严重缺失。
- label 完全非法。

Fallback 可以使用现有 heuristic baseline。

Trace 中必须记录：

```json
{
  "fallback_used": true,
  "fallback_reason": "json_parse_failed"
}
```

## 8. 验收命令

实现后必须运行：

```bash
python3 main.py --mode dev --backend heuristic --max-items 3
python3 main.py --mode dev --backend llm --max-items 3
python3 main.py --mode dev --backend llm --max-items 10
python3 main.py --mode test --backend llm --max-items 3
```

如果 LLM 配置可用，再运行 full dev：

```bash
python3 main.py --mode dev --backend llm
```

还需要运行：

```bash
python3 -m compileall -q humble_brag main.py scripts/format_checker.py scripts/evaluate_dev.py
```

## 9. Phase 1 完成标准

- `--backend heuristic` 仍然可运行。
- `--backend llm` 可以跑通至少 3 条 dev 样本。
- LLM 输出经过 parse / repair。
- 最终 submission JSONL 通过 format checker。
- dev 模式能调用 evaluator。
- 每次运行生成 `trace.jsonl`。
- `RES.md` 记录 backend、prompt version、trace path、fallback count、parse failure count。
- 单条 LLM 失败不会中断整个 pipeline。
- 不引入 RAG / memory / few-shot 检索。
- 不删除现有 heuristic baseline。

## 10. 代码实现边界

这次只做 Phase 1 LLM minimal pipeline。

不要做：

- 不要深调 prompt。
- 不要加入大量 examples。
- 不要引入 RAG。
- 不要把 `data/Bragging_data.json` 塞进 prompt。
- 不要改官方 `format_checker.py` / `evaluate_dev.py` 的评分逻辑。
- 不要为了 dev 分数写样本级规则。
- 不要删除 heuristic baseline。

## 11. 推荐提交信息

```bash
git add main.py humble_brag README.md report.md task.md phase1.md
git commit -m "Add minimal LLM backend pipeline"
```

如果新增了文件，也一并加入：

```bash
git add humble_brag/llm_client.py humble_brag/prompts.py humble_brag/json_repair.py
```

## 12. 后续 Phase 2 方向

Phase 1 完成后，再根据 trace 做 prompt ablation：

1. `llm_a_minimal_v1`: 极简 prompt，无例子。
2. `llm_b_label_definition_v1`: 加每个 label 的一句话定义。
3. `llm_c_tiny_fewshot_v1`: 每类只加极少抽象例子。
4. `llm_d_retrieval_v1`: 最后再考虑 RAG / memory。

不要在 Phase 1 直接跳到 Phase 2。
