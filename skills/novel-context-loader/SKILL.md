---
name: novel-context-loader
description: 小说全能上下文加载器。根据用户语义智能定位目录，加载markdown文件的yaml frontmatter和内容。触发词：加载上下文、查找内容、定位文件、加载设定、查看角色、世界观查询。
---

# 小说全能上下文加载器

智能语义定位与上下文加载工具，支持自然语言查询、yaml frontmatter解析和精准文件加载。

## 核心功能

### 1. 语义定位引擎

将用户自然语言查询映射到项目目录：

| 用户语义 | 目标目录 | 匹配关键词 |
|----------|----------|------------|
| 角色/人物/主角/配角 | 设定/人物档案/ | 角色、人物、主角、配角、char |
| 世界观/设定/世界 | 设定/世界观/ | 世界观、世界、设定、规则 |
| 组织/势力/门派/宗门 | 设定/组织势力/ | 组织、势力、门派、宗门、org |
| 关系/人物关系 | 设定/关系网络.md | 关系、人物关系、关系网 |
| 伏笔/铺垫 | 状态追踪/伏笔管理/ | 伏笔、铺垫、fs |
| 时间线/时间 | 状态追踪/时间线.md | 时间线、时间、事件顺序 |
| 当前状态/角色状态 | 状态追踪/当前状态.md | 当前状态、角色状态、状态快照 |
| 大纲/章节大纲/故事线 | 大纲/ | 大纲、章节、故事线、ch |
| 场景/分场 | 场景设计/ | 场景、分场、sc |
| 正文/章节内容 | 正文/ | 正文、章节内容、第N章 |
| 项目信息/配置/宪法 | 项目信息/ | 项目、配置、宪法、创作 |

### 2. Frontmatter索引

自动扫描目录下所有markdown文件的yaml frontmatter，构建索引：

```yaml
---
id: char_001
type: character
name: 林叶
summary: "天才少年，家族灭门后踏上修行之路"
tags: [主角, 天才, 复仇]
---
```

索引字段：
- `id`: 唯一标识符
- `type`: 文件类型
- `name`: 显示名称
- `summary`: 一句话摘要
- `tags`: 标签列表

### 3. 精准文件加载

根据索引匹配结果，加载完整文件内容或指定层级。

## 使用方法

### 基本用法

```bash
# 语义查询
python scripts/context_loader.py --query "主角的信息" --project ./my-novel

# 按ID加载
python scripts/context_loader.py --id char_001 --project ./my-novel

# 按目录加载
python scripts/context_loader.py --directory "设定/人物档案" --project ./my-novel

# 加载特定层级
python scripts/context_loader.py --query "林叶" --level 2 --project ./my-novel
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--query` | 自然语言查询 | - |
| `--id` | 文件ID精确匹配 | - |
| `--directory` | 目录路径 | - |
| `--project` | 项目目录（必填） | - |
| `--level` | 加载层级(0/1/2) | 1 |
| `--index-only` | 仅返回索引信息 | False |

### 层级说明

| 层级 | 内容 | 用途 |
|------|------|------|
| Level 0 | 仅frontmatter | 快速预览、筛选 |
| Level 1 | 核心信息部分 | 默认加载 |
| Level 2 | 完整内容 | 深度查询 |

## 输出示例

### 索引模式输出

```
📋 目录索引: 设定/人物档案/

┌─────────────────────────────────────────────────────┐
│ ID: char_001                                         │
│ 名称: 林叶                                           │
│ 类型: character                                      │
│ 摘要: 天才少年，家族灭门后踏上修行之路               │
│ 标签: [主角, 天才, 复仇]                             │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ ID: char_002                                         │
│ 名称: 楚天                                           │
│ 类型: character                                      │
│ 摘要: 天澜宗内门弟子，林叶的引路人                   │
│ 标签: [配角, 导师]                                   │
└─────────────────────────────────────────────────────┘
```

### 内容加载输出

```
📄 加载文件: char_001_林叶.md

【核心信息】
身份: 天澜宗外门弟子
性格: 坚毅、谨慎、重情义
境界: 筑基初期

【详细信息】(Level 2)
背景故事: 林家曾是修仙世家...
```

## 项目目录结构

```
my-novel/
├── 项目信息/                    # 项目配置
├── 设定/                        # 静态设定
│   ├── 世界观/
│   ├── 人物档案/
│   ├── 组织势力/
│   └── 关系网络.md
├── 状态追踪/                    # 动态数据
│   ├── 当前状态.md
│   ├── 伏笔管理/
│   └── 时间线.md
├── 大纲/                        # 故事规划
├── 场景设计/                    # 场景规划
└── 正文/                        # 章节产出
```

## 高级用法

### 组合查询

```bash
# 查询多个关键词
python scripts/context_loader.py --query "林叶 楚天" --project ./my-novel

# 按标签筛选
python scripts/context_loader.py --tag "主角" --project ./my-novel

# 按类型筛选
python scripts/context_loader.py --type character --project ./my-novel
```

### 批量导出

```bash
# 导出整个目录的索引
python scripts/context_loader.py --directory "设定" --index-only --output index.json

# 导出匹配文件的内容
python scripts/context_loader.py --query "伏笔" --output ./context/
```

## 注意事项

1. **frontmatter必需**: 文件必须包含yaml frontmatter才能被索引
2. **编码要求**: 所有markdown文件使用UTF-8编码
3. **层级分隔**: 使用`---`分隔核心信息与详细信息
4. **ID命名**: 遵循类型前缀命名规范 (char_, org_, ch_, sc_, fs_)
