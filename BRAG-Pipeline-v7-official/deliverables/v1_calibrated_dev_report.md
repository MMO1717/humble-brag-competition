# BRAG-Pipeline v1 calibrated dev 结果报告

## 摘要

本次在 `v1_generalized` 基础上加入通用 mechanism 校准和规则化 risk 渲染，形成 `v1_calibrated`。规则只使用通用语言 cue，不按具体 dev episode、实体或 reference response 硬修。

## 改动

| 模块 | 改动 |
|---|---|
| `src/postprocess.py` | 新增 `calibrate_mechanism()`，在模型 mechanism 输出后做通用 cue 校准 |
| `src/postprocess.py` | 将 `normalize_risk_assessment()` 改为规则渲染为主，减少 qwen3 过度预测 sycophancy |
| `src/pipeline.py` | 在 `classify_mechanism()` 后、`choose_strategy()` 前接入 mechanism 校准 |

## Dev 结果

| 版本 | Proxy Dev | Mechanism | Strategy | Risk F1 | Response F1 | Format |
|---|---:|---:|---:|---:|---:|---:|
| baseline pipeline | 52.489 | 0.3333 | 0.6222 | 0.6074 | 0.1931 | 1.0000 |
| v1 generalized | 60.764 | 0.6000 | 0.6444 | 0.6074 | 0.1818 | 1.0000 |
| v1 calibrated | 72.440 | 0.8667 | 0.7222 | 0.7296 | 0.1602 | 1.0000 |

## 变化

| 对比 | Proxy Dev | Mechanism | Strategy | Risk F1 | Response F1 |
|---|---:|---:|---:|---:|---:|
| v1 calibrated - v1 generalized | +11.676 | +0.2667 | +0.0778 | +0.1222 | -0.0216 |
| v1 calibrated - baseline | +19.951 | +0.5334 | +0.1000 | +0.1222 | -0.0329 |

## 结论

`v1_calibrated` 明显提升了机制分类、策略和风险标签，代价是 `response_reference_token_f1` 略降。这个 tradeoff 符合 generalized 路线：优先提升可泛化的标签与社会语用稳定性，不追 public dev reference 文本贴合。
