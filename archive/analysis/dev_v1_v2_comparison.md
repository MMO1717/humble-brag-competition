# Dev v1 vs v2 vs v3 Comparison Report

## Score Summary

| Metric | v1 | v2 | v3.1 | v1→v3.1 Change |
|--------|-----|-----|------|----------------|
| **proxy_dev_score** | **44.628** | **56.133** | **63.82** | **+19.192 (+43.0%)** |
| mechanism_accuracy | 0.5778 | 0.7556 | 0.6889 | +0.1111 (+19.2%) |
| strategy_score | 0.5667 | 0.6000 | 0.6333 | +0.0666 (+11.8%) |
| risk_label_f1 | 0.0444 | 0.1704 | 0.6111 | +0.5667 (+1276%) |
| response_reference_token_f1 | 0.0048 | 0.2040 | 0.2176 | +0.2128 (+4433%) |
| preferred_strategy_accuracy | 0.4444 | 0.4000 | 0.4444 | 0.0 (unchanged) |
| acceptable_strategy_rate | 0.6889 | 0.8000 | 0.8222 | +0.1333 (+19.3%) |
| format_checker errors | 0 | 0 | 0 | 0 |

## Per-Version Changes

### v1 → v2 (English output + mechanism defs)
- Biggest gain: response_reference_token_f1 (+0.1992) from Chinese→English switch
- mechanism_accuracy +0.1778 from better definitions
- risk_label_f1 +0.126 from mandatory keyword requirement

### v2 → v3.1 (Risk label reasoning + shorter responses)
- Biggest gain: risk_label_f1 +0.4407 from risk label reasoning guide
- mechanism_accuracy -0.0667 (regression from risk guide cognitive load)
- response_reference_token_f1 +0.0136 (slightly better)
- strategy_score +0.0333 (slightly better)
- acceptable_strategy_rate +0.0222 (slightly better)

## Key Improvements

### 1. risk_label_f1: 0.0444 → 0.6111 (+1276%)
The single biggest overall improvement across all versions.
- v1: Almost no risk keywords → F1 near 0
- v2: Model defaulted to "sycophancy" for everything → F1 0.17
- v3.1: Risk label reasoning guide with misrecognition as default → F1 0.61

### 2. response_reference_token_f1: 0.0048 → 0.2176 (+4433%)
English output enabled token overlap with English references.

### 3. mechanism_accuracy: 0.5778 → 0.6889 (+19.2%)
Improved from v1 but regressed from v2 (0.7556) due to risk label guide interaction.

### 4. acceptable_strategy_rate: 0.6889 → 0.8222 (+19.3%)
More strategies fall within acceptable sets.

## Remaining Issues

### 1. mechanism_accuracy regression (v2: 0.7556 → v3.1: 0.6889)
The risk label reasoning guide appears to distract the model from mechanism classification. Some understated_flex cases are now misclassified.

### 2. response_reference_token_f1 still moderate (0.2176)
The model's phrasing style differs from the reference. Further response template guidance could help.

### 3. preferred_strategy_accuracy unchanged (0.4444)
The model still doesn't hit the exact preferred strategy in ~55% of cases.

## Recommendations for Next Round

1. **Mechanism recovery**: Try removing the RISK_LABEL_GUIDE section and instead embedding risk label rules directly into the few-shot examples' risk_assessment field comments.
2. **Response style**: Add explicit instruction to match the reference style — short, conversational, no filler phrases like "That sounds like" or "I can see that".
3. **Strategy precision**: Add more context-specific examples showing when neutral_observation is preferred over light_acknowledgment.
