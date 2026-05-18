# multi_v1 vs multi_v1.1-lite-a 对比报告

## 1. 本轮改动

修改文件：
- `src/system_prompt_sections.py` — 在 `understated_flex` 定义后新增约 60 词的 DISAMBIGUATION 提示，区分 `understated_flex` vs `achievement_drop`

未修改文件：
- `src/official_validator.py`、`src/MultiAgentBraggingAgent.py`、`src/BraggingResponseAgent.py`、`run_multi_agent_official.py`

## 2. 指标对比

| 指标 | multi_v1 (rerun) | multi_v1.1-lite-a | 变化 |
|------|-------------------|-------------------|------|
| **proxy_dev_score** | 65.309 | **65.478** | **+0.17** |
| mechanism_accuracy | 0.7111 | 0.7333 | **+2.2pp** |
| strategy_score | 0.6556 | 0.6444 | -1.1pp |
| risk_label_f1 | 0.6519 | 0.6259 | **-2.6pp** |
| response_reference_token_f1 | 0.1761 | 0.2047 | +2.9pp |
| format errors | 0 | 0 | 0 |

## 3. 成功标准检查

| 标准 | 要求 | 实际 | 通过? |
|------|------|------|-------|
| format_checker | 0 errors | 0 | YES |
| proxy_dev_score | >= 64.8 (65.309 - 0.5) | 65.478 | YES |
| mechanism_accuracy | 不下降超过 1pp | +2.2pp | YES |
| risk_label_f1 | 不下降超过 1pp | **-2.6pp** | **NO** |
| understated_flex 命中 | 不低于 multi_v1 | 持平 (9/17) | YES |

**risk_label_f1 下降 2.6pp，超出 1pp 容忍阈值。**

## 4. understated_flex 专项分析

Gold 中 understated_flex: **17 条**

| 版本 | 正确 | 误判为 achievement_drop | 误判为其他 |
|------|------|------------------------|-----------|
| multi_v1 | 9 | 3 | 5 (self_aware_brag x2, scarcity_flex x1, faux_modesty x1, ? x1) |
| multi_v1.1-lite-a | 9 | 5 | 3 (self_aware_brag x1, faux_modesty x1, ? x1) |

变化分析：
- 正确数持平（9/17）
- achievement_drop 误判从 3 增至 5（+2）
- 其他误判从 5 降至 3（-2）
- 净效果：将部分 "other" 错误转移到了 "achievement_drop" 错误，正确数不变

具体变化的 4 条：
- `dev_seed_000556_b`: correct->achievement_drop (回归)
- `dev_seed_000691_b`: self_aware_brag->understated_flex (修复)
- `dev_seed_000695_a`: scarcity_flex->understated_flex (修复)
- `dev_seed_000738_c`: understated_flex->achievement_drop (回归)

## 5. Bad Case 分析

### Case 1: risk_label_f1 整体下降
risk_label_f1 从 0.6519 降至 0.6259（-2.6pp），虽然本轮只改了 mechanism 判别，但微小的 prompt 变化可能影响了模型对 risk label 的选择分布。

### Case 2: dev_seed_000556_b 回归
gold=understated_flex，v1 正确，lite 误判为 achievement_drop。说明 DISAMBIGUATION 规则在某些边界案例上反而让模型更倾向于选择 achievement_drop。

### Case 3: dev_seed_000738_c 回归
gold=understated_flex，v1 正确，lite 误判为 achievement_drop。同上，新增规则在部分案例上起了反作用。

### Case 4: strategy_score 下降
strategy_score 从 0.6556 降至 0.6444（-1.1pp），虽在容忍范围内，但说明 mechanism 判断的微调间接影响了策略选择。

## 6. 结论

**建议不保留 multi_v1.1-lite-a。**

理由：
1. risk_label_f1 下降 2.6pp，超出 1pp 容忍阈值
2. understated_flex 正确数持平（9/17），未达到预期提升效果
3. 新增的 DISAMBIGUATION 规则在部分案例上反而导致回归
4. proxy_dev_score 仅提升 0.17，不足以弥补 risk_label 下降

## 7. 下一步建议

1. **回退到 multi_v1** 作为最终提交版本
2. 如果继续优化 understated_flex，应从数据层面分析误判案例的共同特征，而非继续堆 prompt 规则
3. 考虑直接进入 multi_v1.2（candidate reranking），用后处理方式修正 mechanism 误判
