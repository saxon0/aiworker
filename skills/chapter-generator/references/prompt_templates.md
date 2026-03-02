# 提示词模板参考

## 章节生成模板

### 系统提示词

```
你是一位专业的小说作家，擅长根据上下文和大纲创作章节。

核心创作原则：
1. **剧情连贯与防重复（最重要）**：
   - 必须承接前文剧情，从衔接锚点之后的新动作开始
   - 绝对不要重复叙述已发生的事件、对话或心理过程
   - 保持时间线、角色状态的连续性，场景转换要明确

2. **情节推进**：
   - 严格按照本章大纲展开，不要原地踏步
   - 确保本章有独特叙事价值，开头承接上章，结尾铺垫下章

3. **角色一致性**：
   - 符合角色性格设定，延续前文中的成长和变化
   - 保持角色关系的连贯性

4. **写作红线（所有风格必须遵守的禁令）**：
   - 感官描写必须依附于角色动作或情节事件
   - 禁止使用"他感到/她意识到/心中暗道"等直白心理陈述
   - 禁止连续3句以上以"他/她"开头
   - 对话标签禁止反复使用"说道""问道"
   - 零容忍词汇："不禁""此刻""眼眸""低眸""勾唇""薄唇轻启""宛如""仿若"
   - 限频词汇（每百字最多1次）："然而""突然""缓缓""微微""轻轻""淡淡"

5. **记忆系统**：
   - 角色行为符合性格设定和发展轨迹
   - 适当推进或回收伏笔，遵循世界规则
```

### 用户提示词结构

```
请根据以下信息创作本章内容：

---
【🎯 核心任务 - 最高优先级】
---

本章信息：
- 章节序号：第{chapter_number}章
- 章节标题：{chapter_title}
- 本章目标：{chapter_goal}

【章节大纲 - 必须执行】
{chapter_outline}

【衔接锚点 - 必须承接】
上一章结尾：
「{continuation_point}」
⚠️ 从此处自然续写，绝对不得重复上述内容！

【角色关系网络 - 必须遵循】
{character_relationships}

---
【📚 背景参考 - 中等优先级】
---

项目信息：
- 书名：{title}
- 主题：{theme}
- 类型：{genre}
- 叙事视角：{narrative_perspective}

世界观（智能匹配本章相关设定）：
{world_setting_context}

角色基础信息：
{characters_info}

【组织与势力】
{organizations_info}

【已完成的前置章节摘要】
{previous_content}

【上一章尾段实文 - 仅供文风参考，严禁复述情节】
---
{previous_chapter_tail}
---
⛔ 以上尾段内容已在上一章呈现完毕，本章必须从新的动作、结果或场景开始。

---
【⚡ 关键约束 - 必须遵守】
---

【角色当前状态 - 写作时必须参考】
{character_attributes}

【角色动态变化 - 反映最新进展】
{character_dynamic_states}

【故事时间线 - 确保时序一致】
{story_timeline}

【因果链 - 注意前因后果】
{causality_context}

【伏笔处理 - 注意回收或埋设】
{foreshadow_context}

【节奏控制】
{pace_guidance}

---
【✍️ 创作要求 - 严格执行】
---

1. **剧情连贯性（最重要）**：从【衔接锚点】续写，不得重复已述内容

2. **角色一致性（关键）**：
   - 严格遵循【角色关系网络】中的关系设定
   - 根据【角色当前状态】描写角色的身份、能力和行为

3. **情节推进**：
   - 严格按照【章节大纲】展开情节
   - 推动故事向前发展，确保本章有叙事价值

4. **写作风格**：
   - 使用{narrative_perspective}视角
   - 目标{target_word_count}字（{min_word_count}-{max_word_count}字区间）
   - 语言自然克制，按照写作风格指引创作

{writing_style_recipe}

请直接输出章节正文内容，不要包含章节标题和其他说明文字。
```

## 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `chapter_number` | int | 章节序号 |
| `chapter_title` | str | 章节标题 |
| `chapter_goal` | str | 本章创作目标 |
| `chapter_outline` | str | 章节大纲内容 |
| `continuation_point` | str | 上一章结尾（衔接锚点） |
| `title` | str | 书名 |
| `theme` | str | 主题 |
| `genre` | str | 类型 |
| `narrative_perspective` | str | 叙事视角 |
| `world_setting_context` | str | 世界观设定 |
| `characters_info` | str | 角色信息 |
| `character_relationships` | str | 角色关系 |
| `character_attributes` | str | 角色状态 |
| `character_dynamic_states` | str | 动态状态 |
| `organizations_info` | str | 组织势力 |
| `previous_content` | str | 前置章节摘要 |
| `previous_chapter_tail` | str | 上一章尾段 |
| `story_timeline` | str | 故事时间线 |
| `causality_context` | str | 因果链 |
| `foreshadow_context` | str | 伏笔信息 |
| `pace_guidance` | str | 节奏指导 |
| `target_word_count` | int | 目标字数 |
| `min_word_count` | int | 最小字数 |
| `max_word_count` | int | 最大字数 |
| `writing_style_recipe` | str | 写作风格配方 |
