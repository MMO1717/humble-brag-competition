# multi_v1 Mechanism Bad Case Analysis

## Summary

Analyzed `outputs/dev_submission_multi_v1_rerun.jsonl` against `BRAG-Agent-public/data/dev_gold.jsonl` with source text from `BRAG-Agent-public/data/dev_input.jsonl`. The run covers 45 dev examples and gets 32/45 mechanisms correct (`mechanism_accuracy` = 0.7111).

The main failure mode is not random label noise: it concentrates in pairs where an indirect status signal also contains explicit achievement, modesty, or comparison cues. `understated_flex` is the most important class because it is both the largest gold class and the class most often pulled into adjacent mechanisms.

## Overall Mechanism Metrics

- overall `mechanism_accuracy`: **0.7111** (32/45)

| gold mechanism | samples | correct | accuracy |
|---|---:|---:|---:|
| `achievement_drop` | 8 | 6 | 0.750 |
| `comparison_superiority` | 8 | 7 | 0.875 |
| `faux_modesty` | 5 | 5 | 1.000 |
| `humble_complaint` | 4 | 2 | 0.500 |
| `scarcity_flex` | 1 | 1 | 1.000 |
| `self_aware_brag` | 2 | 2 | 1.000 |
| `understated_flex` | 17 | 9 | 0.529 |

| predicted mechanism | prediction count |
|---|---:|
| `achievement_drop` | 11 |
| `understated_flex` | 11 |
| `comparison_superiority` | 8 |
| `faux_modesty` | 6 |
| `self_aware_brag` | 5 |
| `humble_complaint` | 2 |
| `scarcity_flex` | 2 |

## Confusion Matrix

| gold \ predicted | `achievement_drop` | `comparison_superiority` | `faux_modesty` | `humble_complaint` | `scarcity_flex` | `self_aware_brag` | `understated_flex` |
|---|---:|---:|---:|---:|---:|---:|---:|
| `achievement_drop` | 6 | 1 | 0 | 0 | 0 | 0 | 1 |
| `comparison_superiority` | 0 | 7 | 0 | 0 | 0 | 0 | 1 |
| `faux_modesty` | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| `humble_complaint` | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| `scarcity_flex` | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| `self_aware_brag` | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| `understated_flex` | 3 | 0 | 1 | 0 | 1 | 3 | 9 |

## Top Confusion Pairs

| rank | gold mechanism | predicted mechanism | errors |
|---:|---|---|---:|
| 1 | `understated_flex` | `achievement_drop` | 3 |
| 2 | `understated_flex` | `self_aware_brag` | 3 |
| 3 | `humble_complaint` | `achievement_drop` | 2 |
| 4 | `comparison_superiority` | `understated_flex` | 1 |
| 5 | `understated_flex` | `faux_modesty` | 1 |

Additional non-zero confusion pairs:

- `understated_flex` -> `scarcity_flex`: 1
- `achievement_drop` -> `understated_flex`: 1
- `achievement_drop` -> `comparison_superiority`: 1

## Understated Flex Deep Dive

Gold `understated_flex` has 17 examples. The model gets 9/17 correct.

| episode_id | post | predicted | correct | speaker_intention | desired_feedback | strategy | response_text | judgment |
|---|---|---|---:|---|---|---|---|---|
| `dev_seed_000131_a` | (also, you speed read slower on computer screens than physical pages so my score is especially impressive.) | `achievement_drop` | no | Asserting high reading speed capability by contextualizing a score against standard screen limitations. | Recognition of the nuance and validation of the achievement level. | `neutral_observation` | Fair point about screen versus print. That context definitely changes how we should view that number. | Likely read as achievement_drop because the post foregrounds a concrete result or performance claim. Text cues: contains explicit achievement/result wording, contains comparison/superiority language. |
| `dev_seed_000131_b` | (also, you speed read slower on computer screens than physical pages so my score is especially impressive.) | `achievement_drop` | no | Sharing a specific test score and adding context to frame it as superior due to difficulty. | Recognition of the achievement without excessive enthusiasm or questioning. | `neutral_observation` | That makes sense, screens can be trickier. Still, hitting a high score under those conditions counts. | Likely read as achievement_drop because the post foregrounds a concrete result or performance claim. Text cues: contains explicit achievement/result wording, contains comparison/superiority language. |
| `dev_seed_000274_a` | I've seen 'em. Playing first on the bill at Lollapalooza. No big deal. | `understated_flex` | yes | Casually boasting about securing a prime opening slot at a major festival while downplaying its significance. | Recognition of the achievement without excessive excitement or agreement. | `neutral_observation` | Opening slots at Lolla are competitive. Landing one is notable regardless of how casually you're presenting it. | Prediction matched understated_flex; the status signal is implied through offhand context rather than stated directly. |
| `dev_seed_000274_b` | I've seen 'em. Playing first on the bill at Lollapalooza. No big deal. | `understated_flex` | yes | Casually boasting about exclusive festival access by downplaying its significance. | Playful recognition of their cool experience without excessive praise. | `humor_tease` | Yeah, totally no big deal that you got front row access at Lollapalooza. Send pics so we can see the view. | Prediction matched understated_flex; the status signal is implied through offhand context rather than stated directly. |
| `dev_seed_000402_a` | So... uhh.. bragging that this summer, after 45 years of failure, I've learned to reliably and intuitively kill them with my bare hands would be tasteless? I don't know what changed... I can just swat them every time no... | `self_aware_brag` | no | Playfully boasting about finally mastering bug killing after decades of failure, explicitly framing it as a potential brag. | Playful recognition of their new skill without excessive seriousness or overpraising. | `humor_tease` | Haha, 45 years to master the swat? We finally have a human shield against insects. Just promise you won't accidentally swat us instead. | Likely read as self_aware_brag because the speaker explicitly flags the utterance as a brag or jokes about reusing the brag. Text cues: contains explicit achievement/result wording, uses casual hedging that can signal understatement. |
| `dev_seed_000402_b` | So... uhh.. bragging that this summer, after 45 years of failure, I've learned to reliably and intuitively kill them with my bare hands would be tasteless? I don't know what changed... I can just swat them every time no... | `self_aware_brag` | no | Openly framing a new skill acquisition as a boast to invite playful engagement. | Humorous recognition of their persistence and success without judgment. | `light_acknowledgment` | Haha, 45 years to finally crack the code! That takes dedication. Hope your home stays completely pest-free from now on. | Likely read as self_aware_brag because the speaker explicitly flags the utterance as a brag or jokes about reusing the brag. Text cues: contains explicit achievement/result wording, uses casual hedging that can signal understatement. |
| `dev_seed_000461_a` | I forgot what it's like to be good at school. Today I finished a thing we were doing so fast that everyone around me started asking ME for help instead of the prof :') | `understated_flex` | yes | Casually boasting about returning to peak academic performance by framing it as a nostalgic feeling. | Recognition of their competence and return to form without excessive celebration. | `light_acknowledgment` | Glad you're back in the zone! It's always satisfying when you know the material inside out. | Prediction matched understated_flex; the status signal is implied through offhand context rather than stated directly. Text cues: contains explicit achievement/result wording. |
| `dev_seed_000461_b` | I forgot what it's like to be good at school. Today I finished a thing we were doing so fast that everyone around me started asking ME for help instead of the prof :') | `faux_modesty` | no | Boasting about academic competence by claiming forgetfulness of their own skills while highlighting peer reliance. | Subtle recognition of their academic success without excessive praise. | `light_acknowledgment` | Glad you got into the groove. Helping others is a good sign you understood it well. | Likely read as faux_modesty because the post has a modest/hedged surface while still seeking recognition. Text cues: contains explicit achievement/result wording. |
| `dev_seed_000556_a` | I 'm going viral this year just because I got too much talented and it ain't been exposed | `achievement_drop` | no | Boasting about achieving viral status by attributing it to excessive hidden talent. | Recognition of the success without requiring deep emotional support. | `light_acknowledgment` | Cool to hear you're getting traction! Viral waves are tricky, but glad the work is finally finding its audience. | Likely read as achievement_drop because the post foregrounds a concrete result or performance claim. Text cues: contains explicit achievement/result wording, uses casual hedging that can signal understatement. |
| `dev_seed_000556_b` | I 'm going viral this year just because I got too much talented and it ain't been exposed | `understated_flex` | yes | Boasting about viral status and inherent talent while framing it as an inevitable outcome. | Recognition of success and validation of their confidence without excessive flattery. | `light_acknowledgment` | That's huge! Talent definitely matters, but timing helps too. Really glad you're finally getting the attention. | Prediction matched understated_flex; the status signal is implied through offhand context rather than stated directly. Text cues: contains explicit achievement/result wording, uses casual hedging that can signal understatement. |
| `dev_seed_000691_a` | I was at that gig too John! Also but Hollie is my friend & when I was 17 she played my Grandma in our highschool production of Oklahoma. I am going to live off this story 4EVER | `understated_flex` | yes | Casually boasting about a unique personal connection to a performer to elevate social standing. | Recognition of the cool connection and amusement at the story. | `light_acknowledgment` | That is such a funny connection! Definitely worth saving for future conversations. Sounds like a classic tale. | Prediction matched understated_flex; the status signal is implied through offhand context rather than stated directly. |
| `dev_seed_000691_b` | I was at that gig too John! Also but Hollie is my friend & when I was 17 she played my Grandma in our highschool production of Oklahoma. I am going to live off this story 4EVER | `self_aware_brag` | no | Playfully admitting they will repeatedly share a cool personal connection story to maintain relevance and excitement. | Recognition of the story's fun value without dismissing the brag or making them feel awkward. | `humor_tease` | Haha, fair enough! Just promise to leave a few variations for the rest of us in the group chat before you exhaust the plot entirely. | Likely read as self_aware_brag because the speaker explicitly flags the utterance as a brag or jokes about reusing the brag. |
| `dev_seed_000691_c` | I was at that gig too John! Also but Hollie is my friend & when I was 17 she played my Grandma in our highschool production of Oklahoma. I am going to live off this story 4EVER | `understated_flex` | yes | Casually showcasing a social connection by mentioning knowing 'Hollie' as a side note. | Recognition of the connection and validation of the story's value. | `light_acknowledgment` | That is a really crazy connection! Definitely makes the gig feel more personal. I totally get why you're keeping that story forever. | Prediction matched understated_flex; the status signal is implied through offhand context rather than stated directly. |
| `dev_seed_000695_a` | Turning a year older is a whole lot better when and Bobby Lopez sing "Happy Birthday" to you 🥰 Still kind of floating after tonight. | `scarcity_flex` | no | Boasting about exclusive access to a celebrity birthday performance. | Recognition of the special experience without excessive flattery. | `light_acknowledgment` | That sounds like a magical night. Having a famous artist sing to you is definitely a rare treat to cherish. | Likely read as scarcity_flex because the status signal depends on access, rarity, or invitation. Text cues: contains comparison/superiority language. |
| `dev_seed_000738_a` | I never baby talk to my dogs. I use full sentences and a wide vocabulary including complex words. My pug Ralph can carry a full conversation. Adults at family gatherings are shocked at his social aptitude. | `understated_flex` | yes | Casually boasting about their dog's advanced language skills and the shock it causes others. | Recognition of the unique training method without heavy praise. | `light_acknowledgment` | That's pretty rare. Most owners stick to basic commands. Sounds like you two have a special bond though. | Prediction matched understated_flex; the status signal is implied through offhand context rather than stated directly. |
| `dev_seed_000738_b` | I never baby talk to my dogs. I use full sentences and a wide vocabulary including complex words. My pug Ralph can carry a full conversation. Adults at family gatherings are shocked at his social aptitude. | `understated_flex` | yes | Casually boasting about owning an unusually intelligent pug who communicates fluently, implying superior training or luck. | Recognition of the dog's unique skill without excessive flattery about the owner. | `light_acknowledgment` | That's pretty unique having a pug that carries a full conversation. Family gatherings must be entertaining with him around. | Prediction matched understated_flex; the status signal is implied through offhand context rather than stated directly. |
| `dev_seed_000738_c` | I never baby talk to my dogs. I use full sentences and a wide vocabulary including complex words. My pug Ralph can carry a full conversation. Adults at family gatherings are shocked at his social aptitude. | `understated_flex` | yes | Boasting about their dog's exceptional intelligence and conversational ability as if it is normal behavior. | Playful acknowledgment of the dog's weirdness without excessive awe. | `humor_tease` | Honestly, sounds like Ralph is basically the only adult in the room. You better hope he pays rent eventually. | Prediction matched understated_flex; the status signal is implied through offhand context rather than stated directly. |

### Understated Flex Misread Buckets

- `understated_flex -> achievement_drop`: 3 examples (dev_seed_000131_a, dev_seed_000131_b, dev_seed_000556_a).
- `understated_flex -> self_aware_brag`: 3 examples (dev_seed_000402_a, dev_seed_000402_b, dev_seed_000691_b).
- `understated_flex -> faux_modesty`: 1 examples (dev_seed_000461_b).
- `understated_flex -> scarcity_flex`: 1 examples (dev_seed_000695_a).
- `understated_flex -> comparison_superiority`: 0 examples in this run.

## Error Pattern Summary

- Explicit result words such as score, completed, accepted, or impressive make indirect flexes look like `achievement_drop`.
- Casual hedge words such as just, apparently, somehow, or turns out are useful understated-flex evidence only when they do not also imply self-deprecation.
- Comparison terms are strong attractors for `comparison_superiority`; when they simply intensify the implied status signal, hard keyword rules would be brittle.
- `scarcity_flex` has too little dev support for reliable tuning from this split alone.

## Rule Candidate Assessment

| candidate | type | expected_fix | risk | decision |
|---|---|---:|---|---|
| If gold-like cue is achievement wording plus contextual handicap/qualifier, prefer understated_flex over achievement_drop. | `safe_candidate` | 3 | Low-medium: only apply when the result is already known and the extra clause reframes it as harder/more impressive. | Good v1.2 candidate; keep trigger narrow around context-boosting clauses. |
| If post has hedges like just/apparently/turns out but no explicit self-deprecation, prefer understated_flex over faux_modesty. | `risky_candidate` | 1 | Medium-high: faux_modesty and understated_flex share humility cues; rules can easily over-normalize genuine modesty. | Use only as reranking evidence, not as a hard postprocess rule. |
| If superiority terms are generic style markers but the speaker's own status is implied indirectly, prefer understated_flex over comparison_superiority. | `reject` | 0 | High: comparison_superiority is defined by comparison terms, so lexical overrides can damage true positives. | Better handled by pairwise reranking than deterministic rules. |
| Map rarity/access words directly to scarcity_flex. | `reject` | 1 | High: scarcity language can be background context; needs intent and access-status interpretation. | Do not add a standalone keyword rule. |

## Candidate Reranking Assessment

Candidate reranking is a better fit than broad postprocessing for the high-confusion mechanism pairs. The useful scope is a narrow top-2 judge that only activates when the generator's first answer is one of the known neighboring labels and the post contains mixed cues.

| pair | suitability | rationale |
|---|---|---|
| `understated_flex vs achievement_drop` | high | The dev errors often hinge on whether a concrete achievement is being directly announced or indirectly boosted by context. |
| `understated_flex vs faux_modesty` | medium | Both can share modest/hedged wording; a judge can inspect whether there is actual self-deprecation. |
| `understated_flex vs comparison_superiority` | medium | Comparison cues are lexical traps; pairwise reasoning may avoid overcorrecting true superiority claims. |
| `achievement_drop vs comparison_superiority` | medium | Useful when direct achievements are phrased through rank or standards, but the class boundary is less central than understated_flex. |
| `scarcity_flex vs understated_flex` | low | Only one gold scarcity example in dev, so a reranker would be under-calibrated. |

Expected upside is modest but plausible: fixing even 1-3 mechanism errors would move mechanism accuracy by 2.2-6.7pp on this 45-example dev set. The instability risk comes from adding another LLM decision point; this should be mitigated by activating only on specific pair sets and requiring an explicit reason to override the original prediction.

## Recommendation for multi_v1.2

Proceed with a minimal `multi_v1.2` candidate-reranking experiment rather than a broad prompt rewrite or many deterministic rules. The first implementation should target only `understated_flex <-> achievement_drop` and optionally log decisions for `understated_flex <-> faux_modesty` without overriding until the behavior is measured.

Minimum next scope:

- Keep `multi_v1` generation unchanged.
- Add an optional mechanism-only reranking step for selected top-2 pairs.
- Override only when the judge identifies contextual boosting or indirect offhand status signaling with high confidence.
- Re-run dev and compare mechanism accuracy, risk label F1, and acceptable strategy rate together; do not optimize mechanism accuracy alone.

