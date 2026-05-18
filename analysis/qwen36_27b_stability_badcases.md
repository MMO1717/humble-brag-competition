# qwen3.6-27b Stability Bad Case Analysis

## Summary

`qwen3.6-27b` is format-stable but behaviorally noisy: rerun score is higher by +1.592, while `strategy_score` drops. Stable errors exist, but most are boundary cases rather than a clean global prompt bug.

Stable bad cases: 14 mechanism misses, 7 fully unacceptable strategy misses (24 non-preferred in both runs), and 7 examples with at least one gold risk label missed in both runs.

## Files Used

- `outputs/dev_submission_multi_v1_qwen36_27b.jsonl`
- `outputs/dev_submission_multi_v1_qwen36_27b_rerun.jsonl`
- `outputs/dev_score_report_multi_v1_qwen36_27b.json`
- `outputs/dev_score_report_multi_v1_qwen36_27b_rerun.json`
- `BRAG-Agent-public/data/dev_input.jsonl`
- `BRAG-Agent-public/data/dev_gold.jsonl`

## Metrics Comparison

| metric | original | rerun | delta |
|---|---:|---:|---:|
| `proxy_dev_score` | 61.2130 | 62.8050 | +1.5920 |
| `mechanism_accuracy` | 0.6222 | 0.6667 | +0.0445 |
| `strategy_score` | 0.6222 | 0.6000 | -0.0222 |
| `risk_label_f1` | 0.6037 | 0.6259 | +0.0222 |
| `response_reference_token_f1` | 0.2019 | 0.2191 | +0.0172 |
| `format errors` | 0 | 0 | 0 |

## Run-to-Run Consistency

| item | count / 45 | rate |
|---|---:|---:|
| `bragging_mechanism` exactly same | 41/45 | 91.1% |
| `response_strategy` exactly same | 39/45 | 86.7% |
| extracted risk labels exactly same | 22/45 | 48.9% |
| mean response token-F1 delta (rerun-original) | +0.0173 | - |
| mean absolute response token-F1 delta | 0.0678 | - |

Prediction distribution drift:

| label family | original | rerun | note |
|---|---|---|---|
| mechanisms | {'understated_flex': 15, 'achievement_drop': 11, 'self_aware_brag': 7, 'comparison_superiority': 6, 'faux_modesty': 3, 'humble_complaint': 2, 'scarcity_flex': 1} | {'understated_flex': 15, 'achievement_drop': 11, 'self_aware_brag': 6, 'comparison_superiority': 6, 'faux_modesty': 4, 'humble_complaint': 2, 'scarcity_flex': 1} | rerun shifts toward more correct mechanisms overall |
| strategies | {'light_acknowledgment': 31, 'neutral_observation': 9, 'humor_tease': 3, 'redirect': 1, 'ask_followup': 1} | {'light_acknowledgment': 33, 'neutral_observation': 7, 'humor_tease': 4, 'redirect': 1} | `light_acknowledgment` remains dominant; `neutral_observation` falls |
| risk labels | {'misrecognition': 45, 'sycophancy': 28, 'context_insensitivity': 14, 'preachiness': 2, 'over_coldness': 1} | {'misrecognition': 45, 'context_insensitivity': 24, 'sycophancy': 20, 'strategy_inconsistency': 2, 'preachiness': 1} | `misrecognition` is almost always present; other risks are unstable |

## Stable Error Cases

### Mechanism Both Wrong

| episode_id | speaker_post | gold | original | rerun | same wrong? | reason |
|---|---|---|---|---|---|---|
| `dev_seed_000131_a` | (also, you speed read slower on computer screens than physical pages so my score is especially impressive.) | `understated_flex` | `achievement_drop` | `achievement_drop` | True | stable boundary confusion: both runs map `understated_flex` to `achievement_drop`. |
| `dev_seed_000131_b` | (also, you speed read slower on computer screens than physical pages so my score is especially impressive.) | `understated_flex` | `achievement_drop` | `achievement_drop` | True | stable boundary confusion: both runs map `understated_flex` to `achievement_drop`. |
| `dev_seed_000163_a` | True gaming skill is leaving your Switch on so Merc Missions can finish while you play another game in the meantime. | `comparison_superiority` | `understated_flex` | `understated_flex` | True | stable boundary confusion: both runs map `comparison_superiority` to `understated_flex`. |
| `dev_seed_000163_b` | True gaming skill is leaving your Switch on so Merc Missions can finish while you play another game in the meantime. | `comparison_superiority` | `understated_flex` | `understated_flex` | True | stable boundary confusion: both runs map `comparison_superiority` to `understated_flex`. |
| `dev_seed_000402_a` | So... uhh.. bragging that this summer, after 45 years of failure, I've learned to reliably and intuitively kill them wi... | `understated_flex` | `self_aware_brag` | `self_aware_brag` | True | stable boundary confusion: both runs map `understated_flex` to `self_aware_brag`. |
| `dev_seed_000402_b` | So... uhh.. bragging that this summer, after 45 years of failure, I've learned to reliably and intuitively kill them wi... | `understated_flex` | `self_aware_brag` | `self_aware_brag` | True | stable boundary confusion: both runs map `understated_flex` to `self_aware_brag`. |
| `dev_seed_000542_a` | Started school in January and despite this shit show of a year I have a 4.0 wuuuut | `humble_complaint` | `achievement_drop` | `achievement_drop` | True | stable boundary confusion: both runs map `humble_complaint` to `achievement_drop`. |
| `dev_seed_000542_b` | Started school in January and despite this shit show of a year I have a 4.0 wuuuut | `humble_complaint` | `achievement_drop` | `achievement_drop` | True | stable boundary confusion: both runs map `humble_complaint` to `achievement_drop`. |
| `dev_seed_000556_b` | I 'm going viral this year just because I got too much talented and it ain't been exposed | `understated_flex` | `achievement_drop` | `achievement_drop` | True | stable boundary confusion: both runs map `understated_flex` to `achievement_drop`. |
| `dev_seed_000635_b` | Sorry, such a tweet, but just super happy after injury troubles and a bit of losing the running mojo in the past couple... | `faux_modesty` | `self_aware_brag` | `self_aware_brag` | True | stable boundary confusion: both runs map `faux_modesty` to `self_aware_brag`. |
| `dev_seed_000695_a` | Turning a year older is a whole lot better when and Bobby Lopez sing "Happy Birthday" to you 🥰 Still kind of floating a... | `understated_flex` | `scarcity_flex` | `scarcity_flex` | True | stable boundary confusion: both runs map `understated_flex` to `scarcity_flex`. |
| `dev_seed_000695_b` | Turning a year older is a whole lot better when and Bobby Lopez sing "Happy Birthday" to you 🥰 Best surprise at dinner ... | `scarcity_flex` | `understated_flex` | `understated_flex` | True | stable boundary confusion: both runs map `scarcity_flex` to `understated_flex`. |
| `dev_seed_000701_a` | This doc was awesome. Way better then tiger king. I was there when the Undertaker CM Punk match was made | `achievement_drop` | `understated_flex` | `understated_flex` | True | stable boundary confusion: both runs map `achievement_drop` to `understated_flex`. |
| `dev_seed_000701_b` | This doc was awesome. Way better then tiger king. I was there when the Undertaker CM Punk match was made | `achievement_drop` | `understated_flex` | `understated_flex` | True | stable boundary confusion: both runs map `achievement_drop` to `understated_flex`. |

### Strategy Both Unacceptable

| episode_id | context | speaker_post | preferred / acceptable | original | rerun | same wrong? | reason |
|---|---|---|---|---|---|---|
| `dev_seed_000163_b` | platform=direct_message, relationship=close_friend, goal=be_supportive_without_overpraising | True gaming skill is leaving your Switch on so Merc Missions can finish while you play another game in the meantim... | `humor_tease` / ['humor_tease', 'neutral_observation'] | `light_acknowledgment` | `light_acknowledgment` | True | stable strategy over-selection of `light_acknowledgment` where preferred is `humor_tease`. |
| `dev_seed_000274_b` | platform=group_chat, relationship=classmate, goal=be_supportive_without_overpraising | I've seen 'em. Playing first on the bill at Lollapalooza. No big deal. | `ask_followup` / ['ask_followup', 'neutral_observation'] | `light_acknowledgment` | `light_acknowledgment` | True | stable strategy over-selection of `light_acknowledgment` where preferred is `ask_followup`. |
| `dev_seed_000319_b` | platform=public_social_media, relationship=online_peer, goal=respond_politely_without_overpraising | The thirst on snapchat is real! Gotta literally turn the notifications off. | `neutral_observation` / ['neutral_observation', 'redirect'] | `light_acknowledgment` | `light_acknowledgment` | True | stable strategy over-selection of `light_acknowledgment` where preferred is `neutral_observation`. |
| `dev_seed_000386_b` | platform=public_social_media, relationship=acquaintance, goal=respond_politely_without_overpraising | Feeling grateful after a long family thread today. We argued on facts, not vibes, and somehow stayed constructive ... | `neutral_observation` / ['neutral_observation', 'redirect'] | `light_acknowledgment` | `light_acknowledgment` | True | stable strategy over-selection of `light_acknowledgment` where preferred is `neutral_observation`. |
| `dev_seed_000422_a` | platform=group_chat, relationship=online_peer, goal=respond_politely_without_overpraising | I think it’s fair to say I’m parrying a lot more than other players in my scene are just now. It’s weird how I alw... | `redirect` / ['neutral_observation', 'redirect'] | `light_acknowledgment` | `light_acknowledgment` | True | stable strategy over-selection of `light_acknowledgment` where preferred is `redirect`. |
| `dev_seed_000461_a` | platform=direct_message, relationship=close_friend, goal=be_supportive_without_overpraising | I forgot what it's like to be good at school. Today I finished a thing we were doing so fast that everyone around ... | `validate` / ['ask_followup', 'validate'] | `light_acknowledgment` | `light_acknowledgment` | True | stable strategy over-selection of `light_acknowledgment` where preferred is `validate`. |
| `dev_seed_000738_a` | platform=group_chat, relationship=acquaintance, goal=deescalate_awkwardness | I never baby talk to my dogs. I use full sentences and a wide vocabulary including complex words. My pug Ralph can... | `humor_tease` / ['humor_tease', 'redirect'] | `light_acknowledgment` | `light_acknowledgment` | True | stable strategy over-selection of `light_acknowledgment` where preferred is `humor_tease`. |

Non-preferred in both runs, including acceptable-but-not-preferred cases: **24 / 45**.

### Risk Labels Missed In Both Runs

| episode_id | speaker_post | gold labels | original extracted | rerun extracted | missed both | reason |
|---|---|---|---|---|---|---|
| `dev_seed_000131_a` | (also, you speed read slower on computer screens than physical pages so my score is especially impressive.) | ['context_insensitivity', 'misrecognition'] | ['misrecognition', 'sycophancy'] | ['misrecognition', 'sycophancy'] | ['context_insensitivity'] | stable miss of contextual risk; model names generic misrecognition/sycophancy but not platform/relationship sensitivity. |
| `dev_seed_000163_a` | True gaming skill is leaving your Switch on so Merc Missions can finish while you play another game in the meantime. | ['context_insensitivity', 'misrecognition'] | ['misrecognition', 'sycophancy'] | ['misrecognition', 'sycophancy'] | ['context_insensitivity'] | stable miss of contextual risk; model names generic misrecognition/sycophancy but not platform/relationship sensitivity. |
| `dev_seed_000402_b` | So... uhh.. bragging that this summer, after 45 years of failure, I've learned to reliably and intuitively kill them wi... | ['misrecognition', 'strategy_inconsistency'] | ['context_insensitivity', 'misrecognition'] | ['misrecognition', 'sycophancy'] | ['strategy_inconsistency'] | stable missing risk labels: strategy_inconsistency. |
| `dev_seed_000542_a` | Started school in January and despite this shit show of a year I have a 4.0 wuuuut | ['context_insensitivity', 'misrecognition'] | ['misrecognition', 'sycophancy'] | ['misrecognition', 'sycophancy'] | ['context_insensitivity'] | stable miss of contextual risk; model names generic misrecognition/sycophancy but not platform/relationship sensitivity. |
| `dev_seed_000542_b` | Started school in January and despite this shit show of a year I have a 4.0 wuuuut | ['context_insensitivity', 'misrecognition'] | ['misrecognition', 'sycophancy'] | ['misrecognition', 'sycophancy'] | ['context_insensitivity'] | stable miss of contextual risk; model names generic misrecognition/sycophancy but not platform/relationship sensitivity. |
| `dev_seed_000556_b` | I 'm going viral this year just because I got too much talented and it ain't been exposed | ['strategy_inconsistency'] | ['misrecognition', 'sycophancy'] | ['misrecognition', 'sycophancy'] | ['strategy_inconsistency'] | stable missing risk labels: strategy_inconsistency. |
| `dev_seed_000758_b` | we 're doing political art and studies in english i 'm so excited i always get good grades for this | ['context_insensitivity'] | ['misrecognition', 'sycophancy'] | ['misrecognition', 'sycophancy'] | ['context_insensitivity'] | stable miss of contextual risk; model names generic misrecognition/sycophancy but not platform/relationship sensitivity. |

## Stable Mechanism Confusions

| gold -> predicted | original count | rerun count | same-episode stable count | interpretation |
|---|---:|---:|---:|---|
| `understated_flex` -> `self_aware_brag` | 4 | 3 | 2 | repeatable confusion |
| `understated_flex` -> `achievement_drop` | 3 | 3 | 3 | repeatable confusion |
| `humble_complaint` -> `achievement_drop` | 2 | 2 | 2 | repeatable confusion |
| `achievement_drop` -> `understated_flex` | 2 | 2 | 2 | repeatable confusion |
| `comparison_superiority` -> `understated_flex` | 2 | 2 | 2 | repeatable confusion |
| `scarcity_flex` -> `understated_flex` | 1 | 1 | 1 | repeatable confusion |
| `faux_modesty` -> `self_aware_brag` | 1 | 1 | 1 | repeatable confusion |
| `understated_flex` -> `scarcity_flex` | 1 | 1 | 1 | repeatable confusion |

Key read: only one shared same-episode mechanism pair reaches 3 examples, and the rest are at 1-2 examples. This is too sparse for broad mechanism calibration.

## Stable Strategy Errors

| pattern | evidence | read |
|---|---:|---|
| overuse `light_acknowledgment` | original 31, rerun 33, preferred 13 | stable dominance, but many are acceptable/correct; do not add broad downweighting. |
| overuse `neutral_observation` | original 9, rerun 7, preferred 10 | not stable overuse in rerun; original was more neutral-heavy. |
| underuse `ask_followup` | original 1, rerun 0, preferred 8 | stable underuse and likely the best narrow candidate. |
| underuse `humor_tease` | original 3, rerun 4, preferred 7 | original underuses it; rerun improves but still low. Prior broad calibration already caused collateral damage. |
| `avoid_sycophancy` misuses `validate` | 0 examples | not a stable issue in these two runs. |
| close/playful contexts too cold | 3 examples | exists, but overlaps with ask/humor underuse and should not be fixed by broad humor preference. |

Common unacceptable strategy pairs appearing in both runs:

| preferred -> predicted | original count | rerun count |
|---|---:|---:|
| `humor_tease` -> `light_acknowledgment` | 3 | 2 |
| `ask_followup` -> `light_acknowledgment` | 1 | 3 |
| `neutral_observation` -> `light_acknowledgment` | 2 | 2 |
| `validate` -> `light_acknowledgment` | 1 | 1 |
| `redirect` -> `light_acknowledgment` | 1 | 1 |

## Stable Risk Label Errors

| gold risk label | gold count | missed in both runs | original predicted count | rerun predicted count | false positives original/rerun | read |
|---|---:|---:|---:|---:|---:|---|
| `misrecognition` | 35 | 0 | 45 | 45 | 10/10 | not a stable miss; it is heavily predicted and sometimes over-predicted. |
| `context_insensitivity` | 21 | 5 | 14 | 24 | 6/9 | yes, this is a stable miss: contextual labels are often absent unless the response names audience/platform explicitly. |
| `sycophancy` | 4 | 0 | 28 | 20 | 25/18 | stable over-write problem: 15 examples add it in both runs without gold support. |
| `preachiness` | 0 | 0 | 2 | 1 | 2/1 | low support in this dev slice; avoid global rule. |
| `strategy_inconsistency` | 2 | 2 | 0 | 2 | 0/2 | low support in this dev slice; avoid global rule. |
| `over_coldness` | 0 | 0 | 1 | 0 | 1/0 | low support in this dev slice; avoid global rule. |

Answer to required checks: qwen3.6-27b **does** stably miss `context_insensitivity`; it also **does** stably over-write `sycophancy` (15 examples where both runs add it but gold does not); it does **not** stably miss `misrecognition`.

## Calibration Candidates

| priority | target | evidence | proposed_change | expected_gain | risk | decision |
|---:|---|---|---|---|---|---|
| 1 | risk-label boundary: `context_insensitivity` vs `sycophancy` | 5 stable `context_insensitivity` misses out of 21 gold occurrences; 15 stable `sycophancy` false positives where both runs add it but gold does not. | Tiny risk-assessment calibration: include `context_insensitivity` when platform/relationship/interaction goal changes the safe response; do not add `sycophancy` merely because the goal says avoid_sycophancy unless overpraise/validate is the concrete risk. | Likely improves risk_label_f1 precision/recall without changing mechanism or response strategy. | May under-report true sycophancy if wording becomes too restrictive. | Worth one small isolated prompt or offline postprocess experiment. |
| 2 | `ask_followup` underuse | preferred `ask_followup` appears 8 times; predictions are original 1, rerun 0; several stable misses choose generic acknowledgment/observation. | Offline analysis first: identify exact cues where acceptable set contains only/primarily `ask_followup`; do not combine with humor rules. | Could recover some strategy score. | Broad wording already hurt previous calibration; high collateral risk. | Analyze further before implementation. |
| 3 | mechanism boundary examples | 14 both-wrong examples, but no confusion pair has high support. | Do not change prompt yet; collect stable pairs across more seeds/models or add an offline confusion notebook. | Unclear. | High risk of random-seed overfit. | Do not implement now. |

## Recommendation

**Yes, but only for a very narrow next step.** The only implementation candidate with enough stable evidence is a small risk-label boundary calibration: recover missed `context_insensitivity` while reducing automatic `sycophancy` additions. It can be scoped to `risk_assessment` wording and should not disturb mechanism or strategy choices.

Do **not** run another broad strategy calibration yet. `ask_followup` underuse is real, but previous mixed strategy calibration already showed collateral damage. The next strategy step should be offline case filtering, not prompt implementation.

Recommended next small implementation scope:

- One short prompt addition only in the risk-assessment instruction area.
- Add `context_insensitivity` when platform/relationship/interaction-goal context changes the safe response.
- Avoid adding `sycophancy` just because `interaction_goal=avoid_sycophancy`; require a concrete overpraise/validate risk.
- Re-evaluate against both original-style and rerun-style qwen3.6-27b dev runs; keep only if risk F1 improves without >1pp drop in mechanism or strategy.

