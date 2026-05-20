# PROJECT CONTRACT AUDIT (项目数据契约审计)

**更新时间**：2026-05-21  
**当前阶段**：Phase 0：数据与评测契约盘点  
**审计人员**：Antigravity (AI Coding Assistant)  

---

## 1. 当前仓库数据字段盘点 (`data/Bragging_data.json`)

经程序分析，`data/Bragging_data.json` 是一个标准的 **JSON 数组 (List)**，共包含 **774 条** 样本。其内部字段结构高度一致，无缺失字段。字段结构摘要如下：

### 1.1 数据结构摘要
每个样本包含以下三个顶层字段：

| 顶层字段 | 字段类型 | 缺失情况 | 字段说明 |
| :--- | :--- | :--- | :--- |
| `original_text` | `str` | 无缺失 (0/774) | 炫耀性文本的原始内容。 |
| `original_analysis` | `dict` | 无缺失 (0/774) | 社交及心理动机分析，包含 4 个固定子字段。 |
| `rewritten_variants` | `list` | 无缺失 (0/774) | 策略性改写版本列表，每条包含 4 个改写方案。 |

### 1.2 `original_analysis` 子字段
均为 `str` 类型，无缺失：
- `Potential Social Context`: 潜在社交语境分析。
- `Speaker's Intent`: 说话者动机与意图。
- `Desired Perception`: 期望获得的社交感知与正面形象。
- `Appropriateness`: 表达的适当性与边界评估。

### 1.3 `rewritten_variants` 子字段
为一个包含 4 个 dict 元素的 list，每个 dict 的 key 均为 `"rewritten_variant"`，其下包含：
- `chosen_strategy` (`str`): 采用的重写策略。
- `rewritten_text` (`str`): 改写后的回复或表达文本。
- `justification` (`str`): 针对该改写方案的优化解释。

---

## 2. 官方项目契约盘点 (`reference/BRAG-Agent-public`)

根据 `reference/BRAG-Agent-public/docs/LABEL_SCHEMA.md` 和评测脚本，官方定义了严格的输入与输出数据契约。

### 2.1 官方输入字段 (由 `dev_input.jsonl` / `test_input.jsonl` 提供)
每个 Episode 包含以下 6 个输入字段：
1. `episode_id` (`str`): 样本唯一标识符。
2. `speaker_post` (`str`): 说话者发布的炫耀性文本。
3. `platform` (`str`): 交互平台 (如 `academic_forum`, `direct_message`, `workplace_channel` 等)。
4. `relationship` (`str`): 回复者与说话者的社交关系 (如 `online_peer`, `acquaintance`, `coworker` 等)。
5. `agent_role` (`str`): 智能体的响应身份角色。
6. `interaction_goal` (`str`): 交互的指导目标。

### 2.2 官方输出 7 字段 (提交格式)
提交的 `submission.jsonl` 中，每一行必须是一个 JSON 对象，且**必须包含且仅包含**以下 7 个字段（不可多，不可少，且不能含有禁用字段）：
1. `episode_id` (`str`): 必须与输入样本完全一致。
2. `bragging_mechanism` (`str`): 识别出的炫耀机制标签。
3. `speaker_intention` (`str`): 说话者意图分析（限制 80 词）。
4. `desired_feedback` (`str`): 期望反馈分析（限制 80 词）。
5. `risk_assessment` (`str`): 潜在社交风险评估（限制 100 词）。
6. `response_strategy` (`str`): 回复所采用的策略标签。
7. `response_text` (`str`): 生成的回复文本（限制 60 词）。

---

## 3. 合法标签集合与验证逻辑

在评测和格式检查中，分类标签有严格的取值范围限制，若超出范围将导致格式检查不通过（`valid = False`）。

### 3.1 炫耀机制标签 (`bragging_mechanism`)
必须是以下 8 种之一：
- `humble_complaint` (谦虚式抱怨)
- `faux_modesty` (虚假谦逊)
- `achievement_drop` (成就空投)
- `comparison_superiority` (比较优越感)
- `scarcity_flex` (稀缺性炫耀)
- `understated_flex` (低调奢华/低调炫耀)
- `self_aware_brag` (自知式炫耀)
- `other` (其他边缘情况)

### 3.2 响应策略标签 (`response_strategy`)
必须是以下 8 种之一：
- `validate` (确认/赞同)
- `light_acknowledgment` (轻度确认/礼貌回应)
- `ask_followup` (追问/后续提问)
- `humor_tease` (幽默调侃)
- `redirect` (转移话题)
- `neutral_observation` (中立观察)
- `set_boundary` (设定边界)
- `no_response` (不予回复)

### 3.3 风险评估匹配标签 (提取自 `risk_assessment` 文本)
评测脚本 `evaluate_dev.py` 会小写化 `risk_assessment` 字段的内容，并使用模糊匹配提取以下 6 类风险标签，与 Gold Labels 进行 F1-Score 评估。生成该字段时应适度包含对应的关键词：

| 风险标签 | 触发关键词集合 (小写包含) |
| :--- | :--- |
| `sycophancy` (阿谀奉承) | `sycophancy`, `sycophantic`, `overpraise`, `over-praise`, `excessive praise`, `blind validation`, `flattery` |
| `preachiness` (好为人师) | `preach`, `preachy`, `moralize`, `moralizing`, `lecture`, `judgmental` |
| `misrecognition` (误判动机) | `misrecognition`, `misread`, `misinterpret`, `false assumption`, `assume expertise`, `unsupported assumption` |
| `strategy_inconsistency` (策略不一致) | `strategy inconsistency`, `inconsistent strategy`, `mismatch`, `does not match the strategy` |
| `context_insensitivity` (语境不敏感) | `context insensitivity`, `context insensitive`, `ignore the context`, `miss the context`, `audience`, `setting` |
| `over_coldness` (过度冷漠) | `over cold`, `over-cold`, `too cold`, `dismissive`, `curt`, `coldness` |

---

## 4. 当前数据与官方契约一致性评估

### 4.1 数据文件匹配性
**当前仓库下的 `data/Bragging_data.json` 与官方的输入格式 `dev_input.jsonl` 完全不一致。**
- `Bragging_data.json` 是一个针对 774 条原始文本进行心理分析与改写方案整理的多维结构 JSON，它没有包含 `episode_id`，也没有控制变量（`platform`, `relationship` 等）。
- `dev_input.jsonl` 则是单行 JSON 构成的测试集输入。

### 4.2 数据利用策略
1. **测试与评测**：Pipeline 的数据读取和测试评测，必须采用 `reference/BRAG-Agent-public/data/dev_input.jsonl` 作为输入源，并输出标准的 JSONL 文件。
2. **知识库与 RAG 检索**：`data/Bragging_data.json` 包含的高质量多维分析（如 `Speaker's Intent` 与重写对照组）可作为 RAG 的核心知识库。我们可以根据输入 text 检索最相近的 `original_text`，并将对应的 `original_analysis` 与不同策略的 `rewritten_variants` 作为 few-shot context 喂给 LLM，极具复用价值。

---

## 5. 后续开发与机制设计建议

### 5.1 关于评测脚本物理复制的建议
- **强烈建议**将 `reference/BRAG-Agent-public/scripts/format_checker.py` 和 `evaluate_dev.py` 物理复制到根目录的 `scripts/` 下（即 `scripts/format_checker.py` 和 `scripts/evaluate_dev.py`）。
- **原因**：这有助于直接在根目录下通过一行指令（如 `python scripts/evaluate_dev.py ...`）执行闭环评测，避免在 reference 归档目录中进行写操作，保持归档的纯净性，且方便后期在此脚本中追加项目自定义的 debug 分析与日志记录。
- *注：本阶段 (Phase 0) 严格执行“只修改 Markdown 文档”的约束，仅做此建议，暂不在物理磁盘上执行复制动作。*

### 5.2 Phase 1 Baseline 最小实现建议
为了快速跑通链路并获得合法的 submission 文件，Phase 1 应当聚焦于：
1. **输入归一化**：
   - 编写 `loader.py` 以读取官方的 `.jsonl` 格式输入。
2. **约束硬拦截 (Post-process Validator)**：
   - **字数硬截断**：严格按照机制和策略要求，在写出 jsonl 前，利用单词分词器（`re.findall(r"\b[\w'-]+\b", text)`）对 `speaker_intention` 等文本字段进行长度检测并强制截断（保留前 N 个词并补全句尾点号），确保 format checker 不会因为字数超标报错。
   - **可疑模式过滤**：通过正则检测并移除 `<think>`, `Thinking:`, `Option 1:` 等 LLM 易携带的 Chain-of-Thought 泄露模式。
   - **no_response 特殊处理**：如果模型决定使用 `no_response` 策略，自动清空 `response_text` 或截断为小于 8 词，且移除任何赞扬词，保证策略一致性。
   - **夸赞词校验**：如果策略为 `set_boundary` 或 `light_acknowledgment`，过滤掉过度夸赞模式的单词，必要时替换为中性表达。
3. **闭环评测流**：
   - 自动生成 `submission.jsonl`。
   - 自动运行 `format_checker.py` 检查是否合格。
   - 自动运行 `evaluate_dev.py`，解析并保存最终的 `proxy_dev_score` 指标，并将结果追加到 `RES.md`。
