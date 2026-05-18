# qwen3.6-27b Adaptation Analysis

## Summary

`qwen3.6-27b` underperforms the baseline mainly on strategy choice and secondarily on mechanism classification. The output format remains valid, and risk/response degradation is smaller than the mechanism/strategy drop.

The clearest stable pattern is strategy calibration: qwen3.6-27b overuses `light_acknowledgment` and underuses `ask_followup`/`humor_tease`, which directly lowers preferred and acceptable strategy scores. Mechanism errors are more dispersed, with the largest new confusion being `understated_flex -> achievement_drop` but only affecting two baseline-correct samples.

## Data and Files Used

- baseline: `outputs/dev_submission_multi_v1_current.jsonl`
- qwen3.6-27b: `outputs/dev_submission_multi_v1_qwen36_27b.jsonl`
- dev input: `BRAG-Agent-public/data/dev_input.jsonl`
- gold/reference: `BRAG-Agent-public/data/dev_gold.jsonl`

## Overall Metrics

| metric | baseline | qwen3.6-27b | delta |
|---|---:|---:|---:|
| `proxy_dev_score` | 64.18 | 61.213 | -2.967 |
| `mechanism_accuracy` | 0.6667 | 0.6222 | -0.0445 |
| `strategy_score` | 0.6889 | 0.6222 | -0.0667 |
| `risk_label_f1` | 0.6111 | 0.6037 | -0.0074 |
| `response_reference_token_f1` | 0.212 | 0.2019 | -0.0101 |
| `format_errors` | 0 | 0 | 0 |

## Mechanism Comparison

### Per-Gold Mechanism Accuracy

| gold mechanism | baseline | qwen3.6-27b | delta |
|---|---:|---:|---:|
| `achievement_drop` | 7/8 (0.875) | 6/8 (0.750) | -0.125 |
| `comparison_superiority` | 6/8 (0.750) | 6/8 (0.750) | +0.000 |
| `faux_modesty` | 4/5 (0.800) | 3/5 (0.600) | -0.200 |
| `humble_complaint` | 2/4 (0.500) | 2/4 (0.500) | +0.000 |
| `scarcity_flex` | 1/1 (1.000) | 0/1 (0.000) | -1.000 |
| `self_aware_brag` | 2/2 (1.000) | 2/2 (1.000) | +0.000 |
| `understated_flex` | 8/17 (0.471) | 9/17 (0.529) | +0.059 |

### Predicted Mechanism Distribution

| mechanism | baseline count | qwen3.6-27b count | delta |
|---|---:|---:|---:|
| `achievement_drop` | 15 | 11 | -4 |
| `comparison_superiority` | 7 | 6 | -1 |
| `faux_modesty` | 4 | 3 | -1 |
| `humble_complaint` | 2 | 2 | +0 |
| `scarcity_flex` | 3 | 1 | -2 |
| `self_aware_brag` | 4 | 7 | +3 |
| `understated_flex` | 10 | 15 | +5 |

### qwen3.6-27b Confusion Matrix

| gold \ predicted | `achievement_drop` | `comparison_superiority` | `faux_modesty` | `humble_complaint` | `scarcity_flex` | `self_aware_brag` | `understated_flex` |
|---|---:|---:|---:|---:|---:|---:|---:|
| `achievement_drop` | 6 | 0 | 0 | 0 | 0 | 0 | 2 |
| `comparison_superiority` | 0 | 6 | 0 | 0 | 0 | 0 | 2 |
| `faux_modesty` | 0 | 0 | 3 | 0 | 0 | 1 | 1 |
| `humble_complaint` | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| `scarcity_flex` | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `self_aware_brag` | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| `understated_flex` | 3 | 0 | 0 | 0 | 1 | 4 | 9 |

### Mechanism Movement

- baseline correct -> qwen wrong: 5
- baseline wrong -> qwen correct: 3
- largest added confusions:
  - `understated_flex -> self_aware_brag`: 2
  - `faux_modesty -> self_aware_brag`: 1
  - `scarcity_flex -> understated_flex`: 1
  - `achievement_drop -> understated_flex`: 1

## Strategy Comparison

- acceptable strategy rate: baseline 0.8667, qwen3.6-27b 0.8222
- baseline better than qwen on strategy score: 6 samples
- qwen better than baseline on strategy score: 2 samples
- qwen `validate` in `avoid_sycophancy` contexts: 0 samples (none)

### Preferred Strategy Hit Rate

| preferred strategy | baseline | qwen3.6-27b | delta |
|---|---:|---:|---:|
| `ask_followup` | 1/8 (0.125) | 1/8 (0.125) | +0.000 |
| `humor_tease` | 4/7 (0.571) | 2/7 (0.286) | -0.286 |
| `light_acknowledgment` | 12/13 (0.923) | 11/13 (0.846) | -0.077 |
| `neutral_observation` | 5/10 (0.500) | 4/10 (0.400) | -0.100 |
| `redirect` | 1/3 (0.333) | 1/3 (0.333) | +0.000 |
| `validate` | 0/4 (0.000) | 0/4 (0.000) | +0.000 |

### Predicted Strategy Distribution

| strategy | baseline count | qwen3.6-27b count | delta |
|---|---:|---:|---:|
| `ask_followup` | 1 | 1 | +0 |
| `humor_tease` | 7 | 3 | -4 |
| `light_acknowledgment` | 27 | 31 | +4 |
| `neutral_observation` | 9 | 9 | +0 |
| `redirect` | 1 | 1 | +0 |

## Risk and Response Comparison

| item | baseline | qwen3.6-27b | note |
|---|---:|---:|---|
| avg response length | 19.09 | 19.91 | qwen is slightly shorter |
| risk label `context_insensitivity` mentions | 2 | 8 | delta +6 |
| risk label `misrecognition` mentions | 45 | 45 | delta +0 |
| risk label `over_coldness` mentions | 0 | 1 | delta +1 |
| risk label `preachiness` mentions | 1 | 2 | delta +1 |
| risk label `sycophancy` mentions | 4 | 28 | delta +24 |

Most missed qwen risk labels:

- `context_insensitivity`: 14
- `strategy_inconsistency`: 2
- `sycophancy`: 1

Largest response token-F1 drops:

- `dev_seed_000422_a`: -0.252
- `dev_seed_000131_b`: -0.251
- `dev_seed_000519_b`: -0.250
- `dev_seed_000386_b`: -0.218
- `dev_seed_000274_a`: -0.150

## Representative Bad Cases

### Mechanism: baseline correct, qwen wrong

| episode_id | post | gold mechanism / strategy | baseline prediction | qwen3.6-27b prediction | reason | minimal fix direction |
|---|---|---|---|---|---|---|
| `dev_seed_000635_b` | Sorry, such a tweet, but just super happy after injury troubles and a bit of losing the running mojo in the past couple of years. Nice to be enjoying running and feeling positive ... | `faux_modesty` / `neutral_observation` | `faux_modesty` / `light_acknowledgment` | `self_aware_brag` / `light_acknowledgment` | qwen overweights explicit achievement/status wording and misses indirect context or comparison boundary. | Add a short boundary reminder for this mechanism pair. |
| `dev_seed_000691_b` | I was at that gig too John! Also but Hollie is my friend & when I was 17 she played my Grandma in our highschool production of Oklahoma. I am going to live off this story 4EVER | `understated_flex` / `humor_tease` | `understated_flex` / `light_acknowledgment` | `self_aware_brag` / `light_acknowledgment` | qwen overweights explicit achievement/status wording and misses indirect context or comparison boundary. | Add a short boundary reminder for this mechanism pair. |
| `dev_seed_000691_c` | I was at that gig too John! Also but Hollie is my friend & when I was 17 she played my Grandma in our highschool production of Oklahoma. I am going to live off this story 4EVER | `understated_flex` / `ask_followup` | `understated_flex` / `light_acknowledgment` | `self_aware_brag` / `light_acknowledgment` | qwen overweights explicit achievement/status wording and misses indirect context or comparison boundary. | Add a short boundary reminder for this mechanism pair. |
| `dev_seed_000695_b` | Turning a year older is a whole lot better when and Bobby Lopez sing "Happy Birthday" to you 🥰 Best surprise at dinner tonight. | `scarcity_flex` / `ask_followup` | `scarcity_flex` / `light_acknowledgment` | `understated_flex` / `ask_followup` | qwen overweights explicit achievement/status wording and misses indirect context or comparison boundary. | Add a short boundary reminder for this mechanism pair. |

### Strategy: baseline strategy score better than qwen

| episode_id | post | gold mechanism / strategy | baseline prediction | qwen3.6-27b prediction | reason | minimal fix direction |
|---|---|---|---|---|---|---|
| `dev_seed_000163_b` | True gaming skill is leaving your Switch on so Merc Missions can finish while you play another game in the meantime. | `comparison_superiority` / `humor_tease` | `understated_flex` / `humor_tease` | `understated_flex` / `light_acknowledgment` | qwen chooses a safer generic acknowledgment where the gold prefers a more interactive or playful response. | Prefer `ask_followup` or `humor_tease` when they are explicitly supported by playful/community context. |
| `dev_seed_000231_b` | You guys I do n't mean to brag but I just ate vegetables for the third day in a row:person_tipping_hand: ‍:female_sign: | `self_aware_brag` / `light_acknowledgment` | `self_aware_brag` / `light_acknowledgment` | `self_aware_brag` / `humor_tease` | qwen chooses a safer generic acknowledgment where the gold prefers a more interactive or playful response. | Prefer `ask_followup` or `humor_tease` when they are explicitly supported by playful/community context. |
| `dev_seed_000319_b` | The thirst on snapchat is real! Gotta literally turn the notifications off. | `humble_complaint` / `neutral_observation` | `humble_complaint` / `neutral_observation` | `humble_complaint` / `light_acknowledgment` | qwen chooses a safer generic acknowledgment where the gold prefers a more interactive or playful response. | Prefer `ask_followup` or `humor_tease` when they are explicitly supported by playful/community context. |
| `dev_seed_000402_a` | So... uhh.. bragging that this summer, after 45 years of failure, I've learned to reliably and intuitively kill them with my bare hands would be tasteless? I don't know what chang... | `understated_flex` / `humor_tease` | `self_aware_brag` / `humor_tease` | `self_aware_brag` / `light_acknowledgment` | qwen chooses a safer generic acknowledgment where the gold prefers a more interactive or playful response. | Prefer `ask_followup` or `humor_tease` when they are explicitly supported by playful/community context. |

## Minimal Prompt Calibration Candidates

| priority | target | proposed_change | expected_gain | risk |
|---:|---|---|---|---|
| 1 | strategy: avoid generic light_acknowledgment | Add one short rule: When the context is playful/community and the brag invites banter or curiosity, prefer `humor_tease` or `ask_followup` over generic `light_acknowledgment`; keep praise bounded in `avoid_sycophancy`. | Could recover several strategy-score losses; directly targets overuse of `light_acknowledgment` and underuse of `ask_followup`/`humor_tease`. | Medium: may overuse playful strategies in serious contexts unless scoped to playful/community cues. |
| 2 | mechanism: understated_flex vs achievement_drop | Add a short boundary note: if a concrete achievement is already present but the boast comes from an extra constraint/context that makes it look stronger, choose `understated_flex`; if the achievement itself is the main dropped fact, choose `achievement_drop`. | Targets the largest added mechanism confusion, affecting 2 baseline-correct samples. | Low-medium: could over-convert direct achievements with contextual details. |
| 3 | mechanism: comparison_superiority vs understated_flex | Add a small reminder that explicit superiority standards such as true skill, better than, top, or outperforming others usually indicate `comparison_superiority`, not `understated_flex`. | May recover comparison boundary misses. | Medium: lexical cues can be misleading when comparison is background context. |

## Recommendation

Proceed to a minimal next-step implementation only if the experiment is allowed to target strategy calibration. There is one stable strategy pattern affecting more than two dev samples: qwen3.6-27b overuses `light_acknowledgment` and underuses `ask_followup`/`humor_tease`, lowering strategy score by 6.7pp. The recommended single change is the priority-1 strategy calibration, kept under 120 English words and limited to `src/system_prompt_sections.py`.

Do not implement a mechanism-only calibration first: the mechanism errors are real but more dispersed, and the clearest pair (`understated_flex -> achievement_drop`) affects only two baseline-correct examples.

