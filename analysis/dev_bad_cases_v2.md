# Dev v2 Bad Case Analysis Report

## 1. Overall Score Summary

| Metric | v1 | v2 | Change |
|--------|-----|-----|--------|
| proxy_dev_score | 44.628 | 56.133 | +11.505 |
| mechanism_accuracy | 0.5778 | 0.7556 | +0.1778 |
| strategy_score | 0.5667 | 0.6000 | +0.0333 |
| risk_label_f1 | 0.0444 | 0.1704 | +0.1260 |
| response_reference_token_f1 | 0.0048 | 0.2040 | +0.1992 |
| preferred_strategy_accuracy | 0.4444 | 0.4000 | -0.0444 |
| acceptable_strategy_rate | 0.6889 | 0.8000 | +0.1111 |

## 2. Mechanism Classification Errors

Total errors: 11 / 45

### Mechanism Accuracy Distribution

| Mechanism | Correct | Total | Accuracy |
|-----------|---------|-------|----------|
| achievement_drop | 6 | 8 | 75.0% |
| comparison_superiority | 8 | 8 | 100.0% |
| faux_modesty | 5 | 5 | 100.0% |
| humble_complaint | 2 | 4 | 50.0% |
| scarcity_flex | 1 | 1 | 100.0% |
| self_aware_brag | 2 | 2 | 100.0% |
| understated_flex | 10 | 17 | 58.8% |

### Mechanism Confusion Cases

| Predicted | Gold | Episode |
|-----------|------|---------|
| achievement_drop | understated_flex | dev_seed_000131_a |
| achievement_drop | understated_flex | dev_seed_000131_b |
| self_aware_brag | understated_flex | dev_seed_000402_a |
| self_aware_brag | understated_flex | dev_seed_000402_b |
| faux_modesty | understated_flex | dev_seed_000461_b |
| achievement_drop | humble_complaint | dev_seed_000542_a |
| achievement_drop | humble_complaint | dev_seed_000542_b |
| achievement_drop | understated_flex | dev_seed_000556_a |
| achievement_drop | understated_flex | dev_seed_000556_b |
| understated_flex | achievement_drop | dev_seed_000701_a |
| scarcity_flex | achievement_drop | dev_seed_000701_b |

## 3. Strategy Errors

Total non-preferred AND non-acceptable: 9

### Strategy Error Cases

| Episode | Predicted | Preferred | Acceptable |
|---------|-----------|-----------|------------|
| dev_seed_000274_b | humor_tease | ask_followup | ['ask_followup', 'neutral_observation'] |
| dev_seed_000319_a | humor_tease | light_acknowledgment | ['light_acknowledgment', 'neutral_observation', 'ask_followup'] |
| dev_seed_000319_b | light_acknowledgment | neutral_observation | ['neutral_observation', 'redirect'] |
| dev_seed_000386_b | light_acknowledgment | neutral_observation | ['neutral_observation', 'redirect'] |
| dev_seed_000422_a | light_acknowledgment | redirect | ['redirect', 'neutral_observation'] |
| dev_seed_000461_a | light_acknowledgment | validate | ['validate', 'ask_followup'] |
| dev_seed_000519_b | humor_tease | light_acknowledgment | ['light_acknowledgment', 'ask_followup', 'neutral_observation'] |
| dev_seed_000738_a | neutral_observation | humor_tease | ['humor_tease', 'redirect'] |
| dev_seed_000738_c | neutral_observation | humor_tease | ['humor_tease', 'redirect', 'light_acknowledgment'] |

## 4. Risk Label Issues

risk_label_f1 < 0.5: 34 / 45

### Low Risk F1 Cases

| Episode | F1 | Predicted Labels | Gold Labels |
|---------|-----|-----------------|-------------|
| dev_seed_000131_a | 0.00 | {'sycophancy'} | {'context_insensitivity', 'misrecognition'} |
| dev_seed_000131_b | 0.00 | {'sycophancy'} | {'misrecognition'} |
| dev_seed_000163_a | 0.00 | {'sycophancy'} | {'context_insensitivity', 'misrecognition'} |
| dev_seed_000163_b | 0.00 | {'sycophancy'} | {'misrecognition'} |
| dev_seed_000231_a | 0.00 | {'sycophancy'} | {'misrecognition'} |
| dev_seed_000231_b | 0.00 | {'preachiness'} | set() |
| dev_seed_000319_b | 0.00 | {'sycophancy'} | {'context_insensitivity', 'misrecognition'} |
| dev_seed_000330_b | 0.00 | {'misrecognition', 'sycophancy'} | {'context_insensitivity'} |
| dev_seed_000351_a | 0.00 | {'context_insensitivity', 'sycophancy'} | {'misrecognition'} |
| dev_seed_000351_b | 0.00 | {'sycophancy'} | {'misrecognition'} |
| dev_seed_000386_b | 0.00 | {'sycophancy'} | {'context_insensitivity', 'misrecognition'} |
| dev_seed_000386_c | 0.00 | {'context_insensitivity', 'sycophancy'} | {'misrecognition'} |
| dev_seed_000402_a | 0.00 | {'sycophancy'} | {'misrecognition'} |
| dev_seed_000402_b | 0.00 | {'sycophancy'} | {'strategy_inconsistency', 'misrecognition'} |
| dev_seed_000422_a | 0.00 | {'sycophancy'} | {'context_insensitivity', 'misrecognition'} |
| dev_seed_000457_a | 0.00 | {'sycophancy'} | {'misrecognition'} |
| dev_seed_000457_b | 0.00 | {'misrecognition', 'sycophancy'} | {'context_insensitivity'} |
| dev_seed_000519_b | 0.00 | {'sycophancy'} | {'context_insensitivity'} |
| dev_seed_000542_a | 0.00 | {'sycophancy'} | {'context_insensitivity', 'misrecognition'} |
| dev_seed_000556_a | 0.00 | {'context_insensitivity', 'sycophancy'} | {'misrecognition'} |

## 5. Response Quality Issues

response_reference_token_f1 < 0.1: 9 / 45

### Low Response F1 Cases

| Episode | F1 | Pred | Ref |
|---------|-----|------|-----|
| dev_seed_000131_a | 0.000 | True, digital interfaces impose different cognitive loads than physical pages. I | Fair point that screen reading conditions can affect pace, so it's useful contex |
| dev_seed_000163_a | 0.057 | Yeah, optimizing your workflow is key. Makes sense to keep missions running in t | Honestly that sounds like min-maxing your free time more than pure skill, but it |
| dev_seed_000231_b | 0.067 | Day three already? That's basically a nutritional superhero feat. Do you have a  | That counts as progress in my book. Small victories are still victories. |
| dev_seed_000274_a | 0.000 | Front row access is pretty rare. Sounds like you caught the right moment. | Nice bit of concert trivia to have in your back pocket. It's wild how often thos |
| dev_seed_000319_a | 0.054 | Lmao, glad you hit the mute button. Peace and quiet beats a spammy inbox any day | Yeah, that does sound kind of overwhelming. Turning them off for a bit seems sen |
| dev_seed_000319_b | 0.071 | Sounds like your inbox is getting out of hand. Hope you find some peace soon. | That definitely seems like a good time to put the notifications on pause. |
| dev_seed_000402_a | 0.098 | Wait, 45 years?! You've been holding back this entire time. Are we calling this  | Honestly, that's the perfect kind of brag. Tiny, weird, and deeply earned. Sound |
| dev_seed_000461_a | 0.065 | That's awesome! There's nothing better than finally feeling confident in your sk | Aw, that must have felt really good — like a reminder that you haven't lost it. |
| dev_seed_000461_b | 0.057 | Nice! Glad you're back in the zone. Just don't leave the rest of us behind! | Good for you — those random 'oh wait, I do know what I'm doing' class moments fe |
