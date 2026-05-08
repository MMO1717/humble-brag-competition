# Dev v3.1 Bad Case Analysis

## Mechanism Accuracy

| Mechanism | Correct | Total | Accuracy |
|-----------|---------|-------|----------|
| achievement_drop | 6 | 8 | 75.0% |
| comparison_superiority | 7 | 8 | 87.5% |
| faux_modesty | 5 | 5 | 100.0% |
| humble_complaint | 3 | 4 | 75.0% |
| scarcity_flex | 1 | 1 | 100.0% |
| self_aware_brag | 2 | 2 | 100.0% |
| understated_flex | 7 | 17 | 41.2% |

## Mechanism Confusion (14 errors)

| Predicted | Gold | Episode |
|-----------|------|---------|
| achievement_drop | understated_flex | dev_seed_000131_a |
| achievement_drop | understated_flex | dev_seed_000131_b |
| understated_flex | comparison_superiority | dev_seed_000163_a |
| self_aware_brag | understated_flex | dev_seed_000402_a |
| self_aware_brag | understated_flex | dev_seed_000402_b |
| faux_modesty | understated_flex | dev_seed_000461_a |
| comparison_superiority | understated_flex | dev_seed_000461_b |
| achievement_drop | humble_complaint | dev_seed_000542_b |
| achievement_drop | understated_flex | dev_seed_000556_a |
| scarcity_flex | understated_flex | dev_seed_000695_a |
| understated_flex | achievement_drop | dev_seed_000701_a |
| understated_flex | achievement_drop | dev_seed_000701_b |
| comparison_superiority | understated_flex | dev_seed_000738_a |
| comparison_superiority | understated_flex | dev_seed_000738_c |

## Strategy Errors (8 cases)

| Episode | Predicted | Preferred | Acceptable |
|---------|-----------|-----------|------------|
| dev_seed_000274_b | humor_tease | ask_followup | ['ask_followup', 'neutral_observation'] |
| dev_seed_000319_a | humor_tease | light_acknowledgment | ['light_acknowledgment', 'neutral_observation', 'ask_followup'] |
| dev_seed_000319_b | light_acknowledgment | neutral_observation | ['neutral_observation', 'redirect'] |
| dev_seed_000386_b | light_acknowledgment | neutral_observation | ['neutral_observation', 'redirect'] |
| dev_seed_000422_a | light_acknowledgment | redirect | ['redirect', 'neutral_observation'] |
| dev_seed_000422_b | light_acknowledgment | neutral_observation | ['neutral_observation', 'redirect', 'ask_followup'] |
| dev_seed_000461_a | light_acknowledgment | validate | ['validate', 'ask_followup'] |
| dev_seed_000738_a | light_acknowledgment | humor_tease | ['humor_tease', 'redirect'] |

## Risk Label Issues (9 cases with F1 < 0.5)

| Episode | F1 | Predicted | Gold |
|---------|-----|-----------|------|
| dev_seed_000231_b | 0.00 | {'misrecognition'} | set() |
| dev_seed_000274_a | 0.00 | {'misrecognition'} | {'sycophancy'} |
| dev_seed_000330_b | 0.00 | {'misrecognition'} | {'context_insensitivity'} |
| dev_seed_000457_b | 0.00 | {'misrecognition'} | {'context_insensitivity'} |
| dev_seed_000519_b | 0.00 | {'misrecognition'} | {'context_insensitivity'} |
| dev_seed_000556_b | 0.00 | {'misrecognition'} | {'strategy_inconsistency'} |
| dev_seed_000635_b | 0.00 | {'misrecognition'} | {'context_insensitivity'} |
| dev_seed_000738_c | 0.00 | {'sycophancy', 'misrecognition'} | set() |
| dev_seed_000758_b | 0.00 | {'misrecognition'} | {'context_insensitivity'} |

## Response Quality Issues (5 cases with F1 < 0.1)

| Episode | F1 | Pred | Ref |
|---------|-----|------|-----|
| dev_seed_000231_b | 0.061 | Three days straight? That's basically a wellness revolution! What's the next cha | That counts as progress in my book. Small victories are still victories. |
| dev_seed_000402_b | 0.050 | Haha, sounds like a major win. Sometimes it just clicks eventually. Respect for  | That's niche enough to be charming instead of tasteless. Seems like your fly-cat |
| dev_seed_000461_b | 0.051 | Being the go-to person instead of the prof is a serious confidence boost. Glad y | Good for you — those random 'oh wait, I do know what I'm doing' class moments fe |
| dev_seed_000691_b | 0.051 | Living off that story forever? Sounds like a full-time job now. Glad you managed | Honestly, if I had that connection, I’d be bringing it up for years too. |
| dev_seed_000738_c | 0.056 | So Ralph is basically the smartest person at the party then? Hope he doesn't sta | He sounds like a character — send me a clip next time he’s being unusually socia |
