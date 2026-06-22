# BRAG-Agent 项目内容与提示词

## 内容

### 项目说明

可以。现在不需要强制拆成 3 个 agent。更适合改成：**一个代码 agent 统一阅读项目、同步 GitHub 更新、跑 baseline、写审计报告、再按阶段做最小可回滚修改**。

另外，`https://github.com/fflow2023/BRAG-Pipeline.git` 这个仓库目前在公开 Web 访问里返回 404/Not Found，所以如果用户本地已经能拉取，说明它可能是私有仓库、权限仓库，或者只在本地 Git 凭据下可访问。后续应以**本地仓库实际代码**为准，不要让 agent 依据网页内容猜测。

下面这份可以直接复制给代码 agent。

---

---

### 当前项目后续整体计划

#### 0. 先处理 GitHub 更新

因为同学仓库有更新，下一步不是直接改代码，而是先做 **fetch -> diff -> audit -> merge**。

推荐顺序：

```bash
git status
git remote -v
git fetch --all --prune
git branch -vv
git remote show origin
````

然后根据默认分支比较：

```bash
git log --oneline HEAD..origin/main
git diff --stat HEAD..origin/main
git diff --name-status HEAD..origin/main
```

如果默认分支是 `master`，把 `origin/main` 换成 `origin/master`。

只有在确认没有未提交改动、远程更新内容清楚之后，再新建分支合并：

```bash
git checkout -b sync-brag-pipeline-update
git merge origin/main
```

如果本地有未提交改动，先保存：

```bash
git status > LOCAL_STATUS_BEFORE_UPDATE.txt
git diff > LOCAL_DIFF_BEFORE_UPDATE.patch
```

不要直接 `git pull`，否则很容易把本地实验文件和同学更新混在一起。

---

#### 1. 第一阶段：只读审计

产出：

```text
GIT_UPDATE_AUDIT.md
PROJECT_AUDIT.md
BASELINE_RUN_REPORT.md
```

目标是确认：

```text
1. 当前项目怎么运行
2. 当前入口在哪里
3. 当前数据怎么读
4. 当前模型怎么调
5. 当前 prompt / skill / memory 在哪里
6. 当前怎么生成 submission.jsonl
7. 当前怎么跑 format checker
8. 当前怎么跑 dev evaluator
9. 同学更新了哪些文件
10. 哪些模块可以直接复用
```

官方公开包本身提供 `format_checker.py` 和 `evaluate_dev.py`，公开数据规模是 train 500、dev 45、test 409；正式提交文件是 `test_submission.jsonl` 和 `submission_metadata.md`。([GitHub][1])

---

#### 2. 第二阶段：跑通 baseline

目标不是优化分数，而是把当前架构原样跑通。

需要保存：

```text
outputs/baseline/submission.jsonl
outputs/baseline/format_check.txt
outputs/baseline/dev_eval_report.json
outputs/baseline/run_notes.md
```

dev proxy 分数只能用于本地调试和模型选择，官方 leaderboard 由 hidden private evaluation 决定；公开 dev proxy 公式包含 mechanism、strategy、risk、response token F1 和 format 五部分。([GitHub][2])

---

#### 3. 第三阶段：加入 run_id / manifest / trace

这是第一个真正应该改代码的阶段。

只加日志，不改 prompt，不改模型，不改输出策略。

目标目录：

```text
outputs/runs/<run_id>/
  submission.jsonl
  trace.jsonl
  run_manifest.json
  dev_eval_report.json
  format_check.txt
  error_report.md
```

这一步完成后，每次实验都能回答：

```text
这次用的哪个模型？
用了哪个 prompt？
有没有 few-shot？
有没有 memory？
有没有 repair？
每条样本原始输出是什么？
parser 怎么解析的？
postprocess 改了什么？
最终 JSON 是什么？
```

---

#### 4. 第四阶段：错误分析

基于 dev_gold 做自动报告。

重点分析：

```text
1. mechanism 错误
2. strategy 错误
3. risk false positive / false negative
4. response token F1 极低样本
5. strategy-response mismatch
6. hidden reasoning / 格式错误
7. Bloom 高风险回复
```

官方 Bloom 风险包括 `sycophancy`、`strategy_inconsistency`、`context_insensitivity`、`misrecognition`、`preachiness` 和 `over_coldness`，其中 sycophancy、strategy_inconsistency、context_insensitivity 权重最高。([GitHub][2])

---

#### 5. 第五阶段：SkillFlow v1

从当前架构里抽出可复用部分，改成：

```text
Input
-> Normalizer
-> Mechanism Skill
-> Intent / Desired Feedback Skill
-> Risk Skill
-> Strategy Skill
-> Response Skill
-> Validator
-> Submission
```

第一版不要加 memory，也不要加 retrieval。

原因是：先确认“拆模块”本身是否稳定。如果 SkillFlow 一拆分就掉分，必须先通过 trace 找原因，而不是继续叠功能。

---

#### 6. 第六阶段：Prompt / Rule 校准

优化顺序：

```text
1. mechanism_accuracy
2. strategy_score
3. risk_label_f1
4. response_quality
5. response_reference_token_f1
```

注意：本地 response token F1 不是最终官方回复质量。官方 Core 质量包括 understanding、policy、response、consistency 四项，而 Bloom 还会惩罚过度吹捧、策略不一致、忽视语境、误读、说教、过冷等行为。([GitHub][2])

---

#### 7. 第七阶段：Few-shot Retrieval

使用 train.jsonl 做 few-shot，而不是马上 LoRA。

推荐：

```text
mechanism skill: k=2
risk skill: k=1-2
strategy skill: k=1-2
response skill: k=1
```

每个检索结果必须记录到 trace，便于判断是否污染输出。

---

#### 8. 第八阶段：Conditional Memory

保留 `MEMORY/` 文件夹，但不要把 memory 当成“全局 prompt 规则库”。

推荐结构：

```text
MEMORY/
  shared_memory.md
  candidate_memory.jsonl
  active_memory.jsonl
  deprecated_memory.jsonl
  memory_ablation_report.md
```

只有通过 ablation 的 candidate memory 才能进入 active memory。

active memory 必须满足：

```text
1. 有明确 condition
2. 有 scope，例如 risk_skill / strategy_skill
3. activation_rate 不过高
4. 有 positive_examples
5. 有 counterexamples 或适用边界
6. 可关闭
7. 可回滚
```

---

#### 9. 第九阶段：Validator / Repair

format checker 会拒绝 missing IDs、unexpected IDs、duplicate IDs、missing fields、extra fields、invalid labels、过长字段、hidden reasoning 或 prompt-like text，以及明显的 response_strategy / response_text mismatch。([GitHub][3])

因此 validator 必须优先做：

```text
1. 字段数量检查
2. episode_id 检查
3. label 合法性检查
4. 长度检查
5. hidden reasoning 清理
6. strategy-response 一致性检查
```

Repair 只允许一轮，只修指定字段。

---

#### 10. 第十阶段：Final Freeze

最终前冻结：

```text
model
config
prompt version
few-shot index
active memory
validator
repair
decoding params
postprocess
git commit
```

官方 <=20B 规则要求：ensemble、cascade、generator-reranker、RAG with neural reranker、多 agent 系统中，任何读取输入、生成候选、打分、选择或编辑最终答案的模型都必须 individually <=20B；closed model API 不符合 official <=20B track。([GitHub][3])

最终提交：

```text
test_submission.jsonl
submission_metadata.md
```

并且先跑：

```bash
python scripts/format_checker.py path/to/test_submission.jsonl data/test_input.jsonl
```

---

### 现在最推荐的下一步

直接把上面的 **统一代码 Agent 提示词** 给代码 agent。

第一轮只让它做：

```text
1. GIT_UPDATE_AUDIT.md
2. PROJECT_AUDIT.md
3. BASELINE_RUN_REPORT.md
4. MEMORY/shared_memory.md 更新
```

不要让它第一轮改业务代码。等这 3 个报告出来后，再决定是否进入：

```text
Phase 1：run_id / manifest / trace
```

这样不会因为 GitHub 更新、同学架构变化、memory 设计变化混在一起导致项目不可控。

[1]: https://github.com/jjtail/Bragging_acl2025 "GitHub - jjtail/Bragging_acl2025: \"It’s Not Bragging If You Can Back It Up:  Can LLMs Understand Braggings?\" · GitHub"
[2]: https://github.com/jjtail/Bragging_acl2025/blob/main/EVALUATION.md "Bragging_acl2025/EVALUATION.md at main · jjtail/Bragging_acl2025 · GitHub"
[3]: https://github.com/jjtail/Bragging_acl2025/blob/main/PARTICIPATION_RULES.md "Bragging_acl2025/PARTICIPATION_RULES.md at main · jjtail/Bragging_acl2025 · GitHub"

---

