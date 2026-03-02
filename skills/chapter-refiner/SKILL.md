---
name: chapter-refiner
description: 小说章节精修提示词构建器。根据章节内容、小说类别和精修模板构建完整的AI精修提示词。触发词：章节精修、章节美化、精修提示词、章节润色、去AI味、小说精修。
---

# 小说章节精修提示词构建器

为小说章节构建专业的精修提示词，支持22个精修模板、9种小说类别、自动上下文加载。

## 快速开始

```bash
# 列出所有可用模板
python scripts/refine_chapter.py --list-templates

# 构建精修提示词（使用默认模板）
python scripts/refine_chapter.py --input chapter.txt --project ./my-novel

# 指定模板和类别
python scripts/refine_chapter.py --input chapter.txt --category fantasy --templates pacing-optimization dialogue-refine

# 输出到文件
python scripts/refine_chapter.py --input chapter.txt --output prompt.md
```

## 核心功能

### 1. 模板系统

22个专业精修模板，分为7大类：

| 分类 | 模板 |
|------|------|
| 节奏与结构 | 节奏优化、爽点提升、悬念营造、紧张感营造 |
| 描写与细节 | 动作描写、对话优化、感官细节、氛围烘托 |
| 逻辑与世观 | 逻辑一致性、悬疑线索、世界建设 |
| 表达与文笔 | 文笔打磨、科普平衡、情感表达、历史呈现 |
| 专项检查 | 角色互动、升级节奏、科学合理性 |
| 去AI味专项 | 去AI味深度净化 |
| 素材融合 | 素材融合改写、词汇润色、句式优化 |

### 2. 类别规则

9种小说类别的差异化规则：

- `fantasy` - 奇幻/玄幻/仙侠
- `historical` - 历史类
- `science-fiction` - 科幻类
- `romance` - 言情类
- `urban` - 都市类
- `mystery` - 悬疑类
- `web-novel` - 网络小说
- `action` - 动作冒险
- `general` - 通用

### 3. 去AI化系统

三层禁用词控制：

- **A类禁用词**：零容忍，出现即替换
- **B类限频词**：每千字最多1次
- **句式禁令**：禁止特定句式结构

### 4. 上下文加载

自动从项目目录加载：

- 角色信息（设定/人物档案/）
- 世界观设定（设定/世界观/）
- 章节大纲（大纲/）
- 待回收伏笔（状态追踪/伏笔管理/）

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input, -i` | 输入章节文件路径 | 必填 |
| `--output, -o` | 输出提示词文件路径 | 标准输出 |
| `--project, -p` | 小说项目目录 | 无 |
| `--chapter, -c` | 章节编号 | 无 |
| `--category` | 小说类别 | general |
| `--templates, -t` | 模板ID列表 | 默认模板 |
| `--format` | 输出格式 (full/system/user/json) | full |
| `--list-templates` | 列出所有模板 | - |

## 输出格式

### full（默认）

完整的提示词，包含System Prompt和User Message：

```
# System Prompt
[系统提示词，包含去AI化规则和类别规则]

---

# User Message
[用户消息，包含章节文本、模板要求和上下文]
```

### json

JSON格式，便于程序处理：

```json
{
  "system_prompt": "...",
  "user_message": "...",
  "combined_prompt": "...",
  "templates_used": ["pacing-optimization", "dialogue-refine"],
  "context_loaded": true,
  "metadata": {
    "chapter_number": 1,
    "novel_category": "fantasy",
    "word_count": 3000
  }
}
```

## 模板推荐组合

### 通用精修
- 节奏优化
- 对话优化
- 逻辑一致性
- 文笔打磨
- 去AI味深度净化

### 网文爽文
- 节奏优化
- 爽点提升
- 对话优化
- 升级节奏
- 去AI味深度净化

### 悬疑推理
- 悬念营造
- 紧张感营造
- 逻辑一致性
- 悬疑线索
- 去AI味深度净化

## 项目目录结构

```
my-novel/
├── 设定/
│   ├── 人物档案/          # 角色信息
│   ├── 世界观/            # 世界观设定
│   └── 组织势力/          # 组织势力
├── 状态追踪/
│   ├── 伏笔管理/          # 伏笔信息
│   └── 时间线.md
├── 大纲/                  # 章节大纲
└── 正文/                  # 章节内容
```

## 与novel-context-loader集成

本skill的上下文加载功能与 `novel-context-loader` skill 兼容，使用相同的目录结构和frontmatter格式。

## 模板文件格式

模板使用YAML frontmatter格式：

```yaml
---
id: pacing-optimization
name: 节奏优化
category: 节奏与结构类
applicable_categories:
  - general
  - web-novel
difficulty: medium
estimated_time: 120
tags:
  - 快速
  - 网文
  - 必选
default_selected: true
emoji: ⏱️
description: 优化叙事节奏，确保快慢搭配合理
---

# 精修方向

[模板的具体精修指导内容]
```
