# Dev Bad Case Analysis Report

## 1. 总体分数摘要

| 指标 | 值 |
|------|-----|
| proxy_dev_score | **44.628** |
| mechanism_accuracy | 0.5778 |
| strategy_score | 0.5667 |
| risk_label_f1 | 0.0444 |
| response_reference_token_f1 | 0.0048 |
| preferred_strategy_accuracy | 0.4444 |
| acceptable_strategy_rate | 0.6889 |

## 2. 机制分类错误

共 19 / 45 条错误

### 机制准确率分布

| 机制 | 正确 | 总计 | 准确率 |
|------|------|------|--------|
| achievement_drop | 7 | 8 | 87.5% |
| comparison_superiority | 5 | 8 | 62.5% |
| faux_modesty | 0 | 5 | 0.0% |
| humble_complaint | 4 | 4 | 100.0% |
| scarcity_flex | 0 | 1 | 0.0% |
| self_aware_brag | 1 | 2 | 50.0% |
| understated_flex | 9 | 17 | 52.9% |

### 机制混淆 Top 10

| 预测 | 金标 | 次数 |
|------|------|------|
| understated_flex | faux_modesty | 5 |
| achievement_drop | understated_flex | 4 |
| self_aware_brag | understated_flex | 3 |
| scarcity_flex | comparison_superiority | 2 |
| understated_flex | comparison_superiority | 1 |
| faux_modesty | self_aware_brag | 1 |
| understated_flex | achievement_drop | 1 |
| faux_modesty | understated_flex | 1 |
| achievement_drop | scarcity_flex | 1 |

### 机制错误样本

- **dev_seed_000131_b**: pred=`achievement_drop` gold=`understated_flex` — "(also, you speed read slower on computer screens than physical pages so my score"
- **dev_seed_000163_b**: pred=`understated_flex` gold=`comparison_superiority` — "True gaming skill is leaving your Switch on so Merc Missions can finish while yo"
- **dev_seed_000231_b**: pred=`faux_modesty` gold=`self_aware_brag` — "You guys I do n't mean to brag but I just ate vegetables for the third day in a "
- **dev_seed_000330_a**: pred=`scarcity_flex` gold=`comparison_superiority` — "I have two of these exact cars in @USER"
- **dev_seed_000330_b**: pred=`scarcity_flex` gold=`comparison_superiority` — "I have two of these exact cars in @USER"
- **dev_seed_000386_a**: pred=`understated_flex` gold=`faux_modesty` — "I for one feel really blessed that even when my family disagrees at dinner, peop"
- **dev_seed_000386_b**: pred=`understated_flex` gold=`faux_modesty` — "Feeling grateful after a long family thread today. We argued on facts, not vibes"
- **dev_seed_000386_c**: pred=`understated_flex` gold=`faux_modesty` — "One thing I appreciate about my family is that even our big disagreements tend t"
- **dev_seed_000402_a**: pred=`self_aware_brag` gold=`understated_flex` — "So... uhh.. bragging that this summer, after 45 years of failure, I've learned t"
- **dev_seed_000402_b**: pred=`self_aware_brag` gold=`understated_flex` — "So... uhh.. bragging that this summer, after 45 years of failure, I've learned t"
- **dev_seed_000457_a**: pred=`understated_flex` gold=`achievement_drop` — "My stats in 2 games 17 tackles & 1 interception"
- **dev_seed_000461_a**: pred=`faux_modesty` gold=`understated_flex` — "I forgot what it's like to be good at school. Today I finished a thing we were d"
- **dev_seed_000556_b**: pred=`self_aware_brag` gold=`understated_flex` — "I 'm going viral this year just because I got too much talented and it ain't bee"
- **dev_seed_000635_a**: pred=`understated_flex` gold=`faux_modesty` — "Sorry, such a tweet, but just super happy after injury troubles and a bit of los"
- **dev_seed_000635_b**: pred=`understated_flex` gold=`faux_modesty` — "Sorry, such a tweet, but just super happy after injury troubles and a bit of los"

## 3. 策略选择错误

共 14 条不在 preferred 且不在 acceptable

### 策略混淆 Top 10

| 预测 | 金标preferred | 次数 |
|------|---------------|------|
| light_acknowledgment | neutral_observation | 4 |
| humor_tease | ask_followup | 3 |
| light_acknowledgment | ask_followup | 2 |
| light_acknowledgment | redirect | 2 |
| humor_tease | validate | 2 |
| light_acknowledgment | humor_tease | 1 |

### 策略错误样本

- **dev_seed_000131_b**: pred=`light_acknowledgment` preferred=`ask_followup` acceptable=['ask_followup', 'neutral_observation']
- **dev_seed_000274_a**: pred=`light_acknowledgment` preferred=`neutral_observation` acceptable=['neutral_observation']
- **dev_seed_000274_b**: pred=`humor_tease` preferred=`ask_followup` acceptable=['ask_followup', 'neutral_observation']
- **dev_seed_000319_b**: pred=`light_acknowledgment` preferred=`neutral_observation` acceptable=['neutral_observation', 'redirect']
- **dev_seed_000330_a**: pred=`light_acknowledgment` preferred=`redirect` acceptable=['neutral_observation', 'redirect']
- **dev_seed_000351_a**: pred=`light_acknowledgment` preferred=`neutral_observation` acceptable=['ask_followup', 'neutral_observation', 'validate']
- **dev_seed_000386_b**: pred=`light_acknowledgment` preferred=`neutral_observation` acceptable=['neutral_observation', 'redirect']
- **dev_seed_000386_c**: pred=`light_acknowledgment` preferred=`ask_followup` acceptable=['ask_followup', 'neutral_observation']
- **dev_seed_000422_a**: pred=`light_acknowledgment` preferred=`redirect` acceptable=['neutral_observation', 'redirect']
- **dev_seed_000461_a**: pred=`humor_tease` preferred=`validate` acceptable=['ask_followup', 'validate']
- **dev_seed_000461_b**: pred=`humor_tease` preferred=`validate` acceptable=['light_acknowledgment', 'neutral_observation', 'validate']
- **dev_seed_000556_b**: pred=`humor_tease` preferred=`ask_followup` acceptable=['ask_followup', 'light_acknowledgment', 'validate']
- **dev_seed_000695_b**: pred=`humor_tease` preferred=`ask_followup` acceptable=['ask_followup', 'light_acknowledgment', 'validate']
- **dev_seed_000738_a**: pred=`light_acknowledgment` preferred=`humor_tease` acceptable=['humor_tease', 'redirect']

## 4. 风险标签问题

risk_label_f1 < 0.5 的样本: 43 / 45

### 缺少的风险标签分布

- **misrecognition**: 35 次未被包含在 risk_assessment 中
- **context_insensitivity**: 21 次未被包含在 risk_assessment 中
- **sycophancy**: 4 次未被包含在 risk_assessment 中
- **strategy_inconsistency**: 2 次未被包含在 risk_assessment 中

### 典型低 F1 样本

- **dev_seed_000131_a**: f1=0.0, pred_labels=[], gold_labels=['context_insensitivity', 'misrecognition']
- **dev_seed_000131_b**: f1=0.0, pred_labels=[], gold_labels=['misrecognition']
- **dev_seed_000163_a**: f1=0.0, pred_labels=[], gold_labels=['context_insensitivity', 'misrecognition']
- **dev_seed_000163_b**: f1=0.0, pred_labels=[], gold_labels=['misrecognition']
- **dev_seed_000231_a**: f1=0.0, pred_labels=[], gold_labels=['misrecognition']
- **dev_seed_000274_a**: f1=0.0, pred_labels=[], gold_labels=['sycophancy']
- **dev_seed_000274_b**: f1=0.0, pred_labels=[], gold_labels=['misrecognition', 'sycophancy']
- **dev_seed_000319_a**: f1=0.0, pred_labels=[], gold_labels=['misrecognition']
- **dev_seed_000319_b**: f1=0.0, pred_labels=[], gold_labels=['context_insensitivity', 'misrecognition']
- **dev_seed_000330_a**: f1=0.0, pred_labels=[], gold_labels=['context_insensitivity', 'misrecognition']

## 5. 回复质量问题

response_reference_token_f1 < 0.1 的样本: 44 / 45

- **dev_seed_000131_a**: f1=0.0
  - pred: "确实，屏幕阅读效率通常低一些，能维持这个数据也不简单。"
  - ref: "Fair point that screen reading conditions can affect pace, s"
- **dev_seed_000131_b**: f1=0.0
  - pred: "屏幕阅读确实慢点，不过能跑这数据还是挺稳的。"
  - ref: "Interesting point. Do you know whether the benchmark for tha"
- **dev_seed_000163_a**: f1=0.0
  - pred: "哈哈，这算“挂机流”大师吗？效率是高了，但 Switch 电池顶得住吗（狗头）"
  - ref: "Honestly that sounds like min-maxing your free time more tha"
- **dev_seed_000163_b**: f1=0.0
  - pred: "哈哈，这算不算当代游戏人的摸鱼最高境界？下次教教我怎么边玩边挂机😏"
  - ref: "Very efficient, I’ll give you that. Feels like peak side-que"
- **dev_seed_000231_a**: f1=0.0
  - pred: "哈哈，三天不吃肉简直是修行！佩服佩服，今晚是不是得奖励顿大餐压压惊？🍖"
  - ref: "Honestly, three days in a row is real progress. Very proud o"
- **dev_seed_000231_b**: f1=0.0
  - pred: "哈哈，这也叫不炫耀？三天连吃素可是大工程，这凡尔赛浓度我服了！"
  - ref: "That counts as progress in my book. Small victories are stil"
- **dev_seed_000274_a**: f1=0.0
  - pred: "Lolla 主舞台开场听着挺硬核，行吧你说是小事那就是小事。（狗头）"
  - ref: "Nice bit of concert trivia to have in your back pocket. It's"
- **dev_seed_000274_b**: f1=0.0
  - pred: "Lolla 首秀位确实难得，但这“没啥大不了”的语气，我可不信哈（狗头）。"
  - ref: "That's a fun flex. I'm curious whether you knew they'd blow "
- **dev_seed_000319_a**: f1=0.0
  - pred: "哈哈，这算是幸福的烦恼吧！看来魅力太大挡不住，注意休息哈~"
  - ref: "Yeah, that does sound kind of overwhelming. Turning them off"
- **dev_seed_000319_b**: f1=0.0
  - pred: "哈哈，这种“甜蜜的负担”确实难搞，关静音保平安嘛。"
  - ref: "That definitely seems like a good time to put the notificati"
- **dev_seed_000330_a**: f1=0.0
  - pred: "同款双车确实难得，品味在线啊，就是不知道保养费咋样？"
  - ref: "Sounds like that model is a big favorite for you."
- **dev_seed_000330_b**: f1=0.0
  - pred: "同款双车确实少见，这配置在同级里算顶配了。"
  - ref: "If you own two, your practical take on reliability or drivin"
- **dev_seed_000351_b**: f1=0.0
  - pred: "五年 900 台这成绩真扎实，难怪你看人这么准。以后有朋友想买车的我肯定第一个推荐你。"
  - ref: "That’s a lot of experience. No surprise you’ve gotten good a"
- **dev_seed_000386_a**: f1=0.0
  - pred: "确实，现在这种能理性沟通的家庭环境太难得了，替你开心～"
  - ref: "Honestly, that sounds like a solid family dynamic. Being abl"
- **dev_seed_000386_b**: f1=0.0
  - pred: "理性沟通在家庭里确实稀缺，能保持这种良性互动挺难得的，赞一个~"
  - ref: "Sounds like that conversation went better than most do latel"

## 6. 下一轮 Prompt 调优建议

### 6.1 机制分类
- 低准确率机制需要补 few-shot: **faux_modesty, scarcity_flex**
- 当前 few-shot 中缺少 `comparison_superiority` 和 `scarcity_flex` 的示例，建议补充
- 机制定义需要更强调区分边界，特别是 `understated_flex` vs `faux_modesty` vs `humble_complaint`

### 6.2 策略选择
- `light_acknowledgment` 过度使用（占比过高），需要在 prompt 中强调何时应选择其他策略
- `validate` 策略使用不足，few-shot 中可增加 validate 示例
- 对于 `online_peer` 关系和 `community_peer` 角色，应更倾向 `humor_tease` / `ask_followup`

### 6.3 风险标签
- **关键问题**: risk_assessment 中几乎不包含官方风险标签关键词，导致 risk_label_f1 接近 0
- 建议在 prompt 中明确要求 risk_assessment 包含以下关键词之一: sycophancy, preachiness, misrecognition, strategy_inconsistency, context_insensitivity, over_coldness
- 在 few-shot 示例的 risk_assessment 字段中显式使用这些关键词

### 6.4 回复质量
- response_text 与 reference 的 token F1 极低(0.48%)，说明回复风格与金标差异大
- 中文口语化回复 vs 英文 reference 的语言差异是主因，需确认是否应生成英文回复
- 考虑将 response_text 的语言与输入语言匹配（英文输入 → 英文回复）
