#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说章节生成器
基于RTCO框架（P0+P1）构建上下文，生成连贯的小说章节
使用NovelContextLoader进行上下文加载
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List

CONTEXT_LOADER_PATH = Path(__file__).parent.parent.parent / "novel-context-loader" / "scripts"
if CONTEXT_LOADER_PATH.exists():
    sys.path.insert(0, str(CONTEXT_LOADER_PATH))

try:
    from context_loader import NovelContextLoader, FrontmatterIndex, LoadedContent
except ImportError:
    NovelContextLoader = None
    FrontmatterIndex = None
    LoadedContent = None


@dataclass
class PreCheckResult:
    """生成前预检结果"""
    ready: bool
    quality_score: int
    context_quality: str
    warnings: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    outline_missing: bool = False
    outline_quality: Optional[dict] = None


@dataclass
class ContextParts:
    """上下文组件"""
    outline: str = ""
    continuation_point: str = ""
    characters: str = ""
    character_relationships: str = ""
    character_attributes: str = ""
    character_dynamic_states: str = ""
    organizations: str = ""
    world_setting: str = ""
    story_timeline: str = ""
    causality_context: str = ""
    foreshadows: str = ""
    previous_content: str = ""
    previous_chapter_tail: str = ""
    writing_style: str = ""


@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    chapter_number: int
    file_path: str = ""
    word_count: int = 0
    prompt: str = ""
    error: str = ""


class ChapterGenerator:
    """小说章节生成器"""
    
    SYSTEM_PROMPT = """你是一位专业的小说作家，擅长根据上下文和大纲创作章节。

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
   - 感官描写必须依附于角色动作或情节事件，禁止凭空插入"空气中弥漫着…""一阵…吹过""远处传来…"等模板化感官装饰
   - 禁止使用"他感到/她意识到/心中暗道"等直白心理陈述
   - 禁止连续3句以上以"他/她"开头
   - 对话标签禁止反复使用"说道""问道"，须用动作、神态替代
   - 零容忍词汇："不禁""此刻""眼眸""低眸""勾唇""薄唇轻启""宛如""仿若"
   - 限频词汇（每百字最多1次）："然而""突然""缓缓""微微""轻轻""淡淡"

5. **记忆系统**：
   - 角色行为符合性格设定和发展轨迹
   - 适当推进或回收伏笔，遵循世界规则"""
    
    DEFAULT_WRITING_RECIPE = """
---
【✍️ 写作风格配方 — 像人类作家一样写】
---

🎯 句子节奏：动作戏短句连击(5-15字) → 心理戏长句一拉(带逗号断点) → 偶尔单句成段制造停顿
🎯 感官即动作：感官细节必须从角色动作或情节事件中自然产生——角色碰到什么才写触觉，闻到什么才写嗅觉。禁止为了"丰富画面"凭空插入感官描写段。
   ✓ "他扶住墙，指腹蹭到粗糙的灰浆" — 触觉来自动作
   ✓ "锅底烧焦了，满屋糊味，她咳了一声没理" — 嗅觉来自事件
   ✓ "筷子夹起那块肉时手抖了一下——凉的" — 触觉服务于心理
   ✗ "空气中弥漫着淡淡的血腥味" — 无来由的嗅觉装饰
   ✗ "一阵刺骨的寒风吹过他的脸颊" — 模板化触觉开场
   ✗ "远处传来隐隐的钟声/鸟鸣" — 万能听觉背景板
🎯 情绪表达：角色情绪只通过动作和生理反应透露(攥拳、咬牙、喉结滚动)，不写"他感到/意识到"
🎯 对话动作化：对话前后嵌入小动作("她别过脸，'走吧'")，不用"说道/开口道"等标签
🎯 开头多样化：连续段落不以相同词开头，用环境/动作/对话/声音交替起句
🎯 收尾留白：章节结尾用动作定格或悬念引钩，不做总结性抒情
🎯 比喻克制：全章比喻≤3处，每个比喻必须服务于情绪或剧情，拒绝装饰性比喻"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.chapters_path = self.project_path / "正文"
        self.writing_style_path = self.project_path / "写作风格"
        self.project_info_path = self.project_path / "项目信息"
        self.settings_path = self.project_path / "设定"
        self.state_tracking_path = self.project_path / "状态追踪"
        self.outline_path = self.project_path / "大纲"
        
        if NovelContextLoader:
            self.context_loader = NovelContextLoader(project_path)
        else:
            self.context_loader = None
    
    def load_markdown_file(self, file_path: Path) -> str:
        """加载Markdown文件内容"""
        if file_path.exists() and file_path.suffix == '.md':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return ""
        return ""
    
    def load_writing_styles(self) -> str:
        """加载写作风格目录下的所有md文件"""
        styles = []
        
        if self.writing_style_path.exists() and self.writing_style_path.is_dir():
            for md_file in sorted(self.writing_style_path.glob("*.md")):
                content = self.load_markdown_file(md_file)
                if content:
                    style_name = md_file.stem
                    styles.append(f"### {style_name}\n\n{content}")
        
        if styles:
            return "---\n【🎨 写作风格套装】\n---\n\n" + "\n\n".join(styles) + "\n\n⚠️ 请严格按照上述风格套装进行创作，保持全章风格一致。"
        
        return ""
    
    def load_project_config(self) -> dict:
        """加载项目配置"""
        config_path = self.project_info_path / "项目配置.md"
        if config_path.exists():
            content = self.load_markdown_file(config_path)
            config = self._parse_frontmatter(content)
            return config
        
        config_json = self.project_path / "project-config.json"
        if config_json.exists():
            with open(config_json, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {}
    
    def _parse_frontmatter(self, content: str) -> dict:
        """解析Markdown文件的frontmatter"""
        config = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        config[key.strip()] = value.strip().strip('"\'')
        return config
    
    def truncate(self, text: str, max_length: int) -> str:
        """截断文本"""
        if not text or len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    def _extract_content_from_result(self, result: dict) -> str:
        """从NovelContextLoader结果中提取内容"""
        if not result or not result.get("success"):
            return ""
        
        contents = []
        for item in result.get("results", []):
            content = item.get("content", "")
            if content:
                idx = item.get("index", {})
                name = idx.get("name", "")
                if name:
                    contents.append(f"### {name}\n\n{content}")
                else:
                    contents.append(content)
        
        return "\n\n".join(contents)
    
    def _find_chapter_file(self, chapter_number: int) -> Optional[Path]:
        """查找章节文件"""
        if not self.chapters_path.exists():
            return None
        
        for volume_dir in self.chapters_path.iterdir():
            if volume_dir.is_dir():
                for file in volume_dir.iterdir():
                    match = re.match(r"第(\d+)章", file.name)
                    if match and int(match.group(1)) == chapter_number:
                        return file
        
        for file in self.chapters_path.glob("*.md"):
            match = re.match(r"第(\d+)章", file.name)
            if match and int(match.group(1)) == chapter_number:
                return file
        
        return None
    
    def pre_generation_check(self, chapter_number: int) -> PreCheckResult:
        """生成前预检"""
        warnings = []
        suggestions = []
        quality_score = 100
        
        outline_result = self.context_loader.search_by_directory("大纲", level=1) if self.context_loader else {"success": False}
        
        current_outline = None
        if outline_result.get("success"):
            for item in outline_result.get("results", []):
                idx = item.get("index", {})
                if idx.get("type") == "chapter":
                    name = idx.get("name", "")
                    match = re.search(r"(\d+)", name)
                    if match and int(match.group(1)) == chapter_number:
                        current_outline = item
                        break
        
        outline_missing = False
        outline_quality = None
        
        if not current_outline or not current_outline.get("content"):
            outline_missing = True
            warnings.append(f"❌ 第{chapter_number}章没有大纲，无法有效引导章节生成")
            suggestions.append(f"请先为第{chapter_number}章创建大纲（建议200-300字）")
            quality_score -= 40
        else:
            outline_quality = self._evaluate_outline_quality(current_outline.get("content", ""))
            if outline_quality["level"] == "poor":
                warnings.append(f"大纲质量{outline_quality['levelIcon']}{outline_quality['levelLabel']}（{outline_quality['score']}分）：内容过于简略")
                suggestions.extend(outline_quality["suggestions"])
                quality_score -= 30
            elif outline_quality["level"] == "fair":
                warnings.append(f"大纲质量{outline_quality['levelIcon']}{outline_quality['levelLabel']}（{outline_quality['score']}分）：建议补充更多细节")
                quality_score -= 15
        
        if chapter_number > 1:
            prev_chapter_path = self._find_chapter_file(chapter_number - 1)
            if not prev_chapter_path:
                warnings.append("上一章内容不足或未找到，衔接可能不顺畅")
                suggestions.append("建议先完成上一章或检查章节文件是否存在")
                quality_score -= 20
        
        char_result = self.context_loader.search_by_query("角色", level=0, index_only=True) if self.context_loader else {"success": False}
        char_count = len(char_result.get("results", [])) if char_result.get("success") else 0
        if char_count == 0:
            warnings.append("未配置任何角色信息，角色一致性无法保证")
            suggestions.append('建议在"设定/人物档案"目录添加主要角色')
            quality_score -= 15
        
        world_result = self.context_loader.search_by_query("世界观", level=0, index_only=True) if self.context_loader else {"success": False}
        world_count = len(world_result.get("results", [])) if world_result.get("success") else 0
        if world_count == 0:
            warnings.append("世界观设定不完整")
            suggestions.append('建议在"设定/世界观"目录添加世界观设定')
            quality_score -= 10
        
        project_config = self.load_project_config()
        if not project_config.get("genre"):
            warnings.append("未设置小说类型，AI可能无法准确把握风格")
            suggestions.append('建议在"项目信息/项目配置.md"中设置小说类型')
            quality_score -= 5
        
        if quality_score >= 80:
            context_quality = "high"
        elif quality_score >= 50:
            context_quality = "medium"
        else:
            context_quality = "low"
        
        return PreCheckResult(
            ready=len(warnings) == 0,
            quality_score=quality_score,
            context_quality=context_quality,
            warnings=warnings,
            suggestions=suggestions,
            outline_missing=outline_missing,
            outline_quality=outline_quality
        )
    
    def _evaluate_outline_quality(self, content: str) -> dict:
        """评估大纲质量"""
        word_count = len(content)
        
        if word_count < 50:
            return {
                "level": "poor",
                "levelLabel": "较差",
                "levelIcon": "🔴",
                "score": 30,
                "wordCount": word_count,
                "suggestions": ["大纲内容过短，建议扩充至200-300字", "添加主要情节点和角色互动"]
            }
        elif word_count < 150:
            return {
                "level": "fair",
                "levelLabel": "一般",
                "levelIcon": "🟡",
                "score": 60,
                "wordCount": word_count,
                "suggestions": ["建议补充更多细节", "添加场景描述和冲突设计"]
            }
        else:
            return {
                "level": "good",
                "levelLabel": "良好",
                "levelIcon": "🟢",
                "score": 85,
                "wordCount": word_count,
                "suggestions": []
            }
    
    def build_context(self, chapter_number: int, target_word_count: int = 2500) -> ContextParts:
        """构建上下文（P0+P1）使用NovelContextLoader"""
        context = ContextParts()
        
        if not self.context_loader:
            return context
        
        outline_result = self.context_loader.search_by_directory("大纲", level=2)
        if outline_result.get("success"):
            for item in outline_result.get("results", []):
                idx = item.get("index", {})
                name = idx.get("name", "")
                match = re.search(r"(\d+)", name)
                if match and int(match.group(1)) == chapter_number:
                    content = item.get("content", "")
                    title = idx.get("name", "")
                    context.outline = f"**{title}**\n{content}"
                    break
        
        if chapter_number > 1:
            context.continuation_point = self._load_previous_chapter_tail(chapter_number)
        
        char_result = self.context_loader.search_by_query("角色", level=1)
        context.characters = self._extract_content_from_result(char_result)
        
        rel_result = self.context_loader.search_by_query("关系", level=1)
        context.character_relationships = self._extract_content_from_result(rel_result)
        
        state_result = self.context_loader.search_by_query("当前状态", level=1)
        context.character_attributes = self._extract_content_from_result(state_result)
        
        org_result = self.context_loader.search_by_query("组织势力", level=1)
        context.organizations = self._extract_content_from_result(org_result)
        
        world_result = self.context_loader.search_by_query("世界观", level=1)
        context.world_setting = self._extract_content_from_result(world_result)
        
        if chapter_number >= 3:
            dynamic_result = self.context_loader.search_by_query("角色状态", level=1)
            context.character_dynamic_states = self._extract_content_from_result(dynamic_result)
        
        if chapter_number >= 5:
            timeline_result = self.context_loader.search_by_query("时间线", level=1)
            context.story_timeline = self._extract_content_from_result(timeline_result)
            
            content_result = self.context_loader.search_by_query("正文", level=1)
            context.causality_context = self._build_causality_from_content(content_result, chapter_number)
        
        if chapter_number > 5:
            fs_result = self.context_loader.search_by_query("伏笔", level=1)
            context.foreshadows = self._extract_content_from_result(fs_result)
        
        context.previous_content = self._build_previous_summaries(chapter_number)
        
        if chapter_number > 1:
            context.previous_chapter_tail = self._load_previous_chapter_tail(chapter_number, 2500)
        
        context.writing_style = self.load_writing_styles()
        
        return context
    
    def _load_previous_chapter_tail(self, chapter_number: int, max_length: int = 800) -> str:
        """加载上一章结尾"""
        if chapter_number <= 1:
            return ""
        
        prev_file = self._find_chapter_file(chapter_number - 1)
        if not prev_file:
            return ""
        
        try:
            with open(prev_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            content_start = 0
            for i, line in enumerate(lines):
                if i > 0 and line.strip():
                    content_start = i
                    break
            
            body = '\n'.join(lines[content_start:])
            
            if len(body) <= max_length:
                return body
            
            tail = body[-max_length:]
            first_para = tail.find('\n\n')
            if first_para > 0 and first_para < 200:
                return tail[first_para + 2:]
            return tail
        except Exception:
            return ""
    
    def _build_causality_from_content(self, content_result: dict, chapter_number: int) -> str:
        """从正文结果构建因果链"""
        if not content_result.get("success"):
            return ""
        
        recent = []
        for item in content_result.get("results", []):
            idx = item.get("index", {})
            name = idx.get("name", "")
            match = re.search(r"(\d+)", name)
            if match:
                ch = int(match.group(1))
                if ch < chapter_number:
                    recent.append({
                        "chapter": ch,
                        "name": name,
                        "content": item.get("content", "")[:200]
                    })
        
        recent = sorted(recent, key=lambda x: x["chapter"], reverse=True)[:5]
        recent.reverse()
        
        if not recent:
            return ""
        
        section = "## 关键事件因果链\n"
        for item in recent:
            section += f"- 第{item['chapter']}章《{item['name']}》: {self.truncate(item['content'], 50)}\n"
        
        return section
    
    def _build_previous_summaries(self, chapter_number: int) -> str:
        """构建前置章节摘要"""
        if chapter_number <= 1:
            return ""
        
        max_chapters = 2 if chapter_number <= 10 else 3 if chapter_number <= 30 else 5
        
        previous = []
        for ch in range(chapter_number - 1, max(0, chapter_number - max_chapters - 1), -1):
            ch_file = self._find_chapter_file(ch)
            if ch_file:
                content = self.load_markdown_file(ch_file)
                if content:
                    previous.append({
                        "chapter": ch,
                        "content": content[:500]
                    })
        
        previous.reverse()
        
        if not previous:
            return ""
        
        section = "## 已完成的前置章节摘要\n"
        
        for item in previous:
            section += f"\n【第{item['chapter']}章】\n"
            section += f"✅ 已完成事件（不得在新章节重复描写）：\n"
            section += f"  - {self.truncate(item['content'], 100)}\n"
            section += f"\n⚠️ 警告：以上事件已在第{item['chapter']}章完整呈现，新章节应从这些事件结束后的下一刻开始！\n"
        
        return section
    
    def build_pace_guidance(self, pace_level: int) -> str:
        """构建节奏指导"""
        pace_map = {
            1: "节奏偏慢：更多环境/心理描写，减少事件密度，重氛围铺陈。",
            2: "节奏较慢：以描写与情绪推进为主，事件推进适中。",
            3: "节奏中等：描写与事件推进均衡，保持清晰转折。",
            4: "节奏较快：以动作与冲突推进为主，减少冗长铺垫。",
            5: "节奏极快：高密度事件与转折，紧凑推进，避免长段描写。"
        }
        return pace_map.get(pace_level, pace_map[3])
    
    def build_prompt(self, chapter_number: int, context: ContextParts, 
                     chapter_goal: str, pace_level: int, 
                     target_word_count: int, project_config: dict) -> str:
        """构建完整提示词"""
        
        min_word_count = int(target_word_count * 0.85) if target_word_count >= 3000 else max(500, target_word_count - 500)
        max_word_count = int(target_word_count * 1.20) if target_word_count >= 3000 else target_word_count + 1000
        
        title = project_config.get("title", "未知书名")
        theme = project_config.get("theme", "未知主题")
        genre = project_config.get("genre", "未知类型")
        narrative_perspective = project_config.get("narrativePerspective", project_config.get("叙述视角", "第三人称"))
        
        current_outline = context.outline or "暂无大纲"
        chapter_title = f"第{chapter_number}章"
        if context.outline:
            match = re.search(r"\*\*(.+?)\*\*", context.outline)
            if match:
                chapter_title = match.group(1)
        
        writing_style_section = context.writing_style if context.writing_style else self.DEFAULT_WRITING_RECIPE
        
        prompt = f"""请根据以下信息创作本章内容：

---
【🎯 核心任务 - 最高优先级】
---

本章信息：
- 章节序号：第{chapter_number}章
- 章节标题：{chapter_title}
- 本章目标：{chapter_goal}

【章节大纲 - 必须执行】
{current_outline}

【衔接锚点 - 必须承接】
上一章结尾：
「{context.continuation_point}」
⚠️ 从此处自然续写，绝对不得重复上述内容！

【角色关系网络 - 必须遵循】
{context.character_relationships or "暂无角色关系信息"}

---
【📚 背景参考 - 中等优先级】
---

项目信息：
- 书名：{title}
- 主题：{theme}
- 类型：{genre}
- 叙事视角：{narrative_perspective}

世界观（智能匹配本章相关设定）：
{context.world_setting or "暂无世界观设定"}

角色基础信息：
{context.characters or "暂无角色信息"}

【组织与势力】
{context.organizations or "暂无组织势力信息"}

【已完成的前置章节摘要】
{context.previous_content or "暂无前置章节内容"}

【上一章尾段实文 - 仅供文风参考，严禁复述情节】
以下内容仅用于参考写作风格和语言节奏，不得以任何形式重复、改写或概括其中的情节、对话和描写。
---
{context.previous_chapter_tail}
---
⛔ 以上尾段内容已在上一章呈现完毕，本章必须从新的动作、结果或场景开始。

---
【⚡ 关键约束 - 必须遵守】
---

【角色当前状态 - 写作时必须参考】
{context.character_attributes or "暂无角色状态信息"}

【角色动态变化 - 反映最新进展】
{context.character_dynamic_states or "暂无动态状态"}

【故事时间线 - 确保时序一致】
{context.story_timeline or "暂无时间线"}

【因果链 - 注意前因后果】
{context.causality_context or "暂无因果链"}

【伏笔处理 - 注意回收或埋设】
{context.foreshadows or "暂无伏笔信息"}

【节奏控制】
{self.build_pace_guidance(pace_level)}

---
【✍️ 创作要求 - 严格执行】
---

1. **剧情连贯性（最重要）**：从【衔接锚点】续写，不得重复已述内容

2. **角色一致性（关键）**：
   - 严格遵循【角色关系网络】中的关系设定
   - 根据【角色当前状态】描写角色的身份、能力和行为
   - 角色互动必须符合已建立的关系类型

3. **情节推进**：
   - 严格按照【章节大纲】展开情节
   - 推动故事向前发展，确保本章有叙事价值

4. **写作风格**：
   - 使用{narrative_perspective}视角，目标{target_word_count}字（{min_word_count}-{max_word_count}字区间均可），优先情节完整性
   - 语言自然克制，按照写作风格指引创作

{writing_style_section}

请直接输出章节正文内容，不要包含章节标题和其他说明文字。"""
        
        return prompt
    
    def generate_chapter(self, chapter_number: int, target_word_count: int = 2500,
                         pace_level: int = 3, chapter_goal: str = "延续剧情发展",
                         output_dir: Optional[str] = None) -> GenerationResult:
        """生成章节"""
        
        print(f"📝 开始生成第{chapter_number}章")
        
        print("🔍 生成前预检...")
        pre_check = self.pre_generation_check(chapter_number)
        
        print(f"📊 预检结果: 质量={pre_check.context_quality} ({pre_check.quality_score}分)")
        
        if pre_check.warnings:
            for warning in pre_check.warnings[:3]:
                print(f"  ⚠️ {warning}")
        
        if pre_check.outline_missing:
            print("❌ 缺少大纲，无法生成章节")
            return GenerationResult(
                success=False,
                chapter_number=chapter_number,
                error="请先创建章节大纲"
            )
        
        print("📖 构建上下文（使用NovelContextLoader）...")
        context = self.build_context(chapter_number, target_word_count)
        
        print("✅ 上下文构建完成")
        
        if context.writing_style:
            print("   - 写作风格: 已加载项目风格文件")
        
        project_config = self.load_project_config()
        
        print("📄 组装提示词...")
        prompt = self.build_prompt(
            chapter_number=chapter_number,
            context=context,
            chapter_goal=chapter_goal,
            pace_level=pace_level,
            target_word_count=target_word_count,
            project_config=project_config
        )
        
        chapter_title = f"第{chapter_number}章"
        if context.outline:
            match = re.search(r"\*\*(.+?)\*\*", context.outline)
            if match:
                chapter_title = match.group(1)
        
        output_path = Path(output_dir) if output_dir else self.chapters_path / "第一卷"
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_name = f"第{chapter_number}章_{chapter_title}.md"
        file_path = output_path / file_name
        
        prompt_file = output_path / f"第{chapter_number}章_prompt.md"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(f"# 系统提示词\n\n{self.SYSTEM_PROMPT}\n\n# 用户提示词\n\n{prompt}")
        
        print(f"✅ 提示词已保存: {prompt_file}")
        print(f"📏 提示词长度: {len(prompt)} 字符")
        
        print("\n" + "="*60)
        print("📋 提示词内容预览（前2000字符）:")
        print("="*60)
        print(prompt[:2000])
        if len(prompt) > 2000:
            print(f"\n... (共 {len(prompt)} 字符)")
        print("="*60)
        
        print(f"\n✅ 章节生成准备完成：第{chapter_number}章")
        print(f"   - 目标字数: {target_word_count}")
        print(f"   - 节奏等级: {pace_level}")
        print(f"   - 本章目标: {chapter_goal}")
        print(f"   - 提示词文件: {prompt_file}")
        
        return GenerationResult(
            success=True,
            chapter_number=chapter_number,
            file_path=str(file_path),
            word_count=0,
            prompt=prompt
        )


def deduplicate_check(content: str, previous_chapters: list) -> dict:
    """内容去重验证"""
    if not previous_chapters:
        return {"isValid": True, "score": 100, "issues": []}
    
    issues = []
    score = 100
    
    content_normalized = content.lower().replace("\n", "").replace(" ", "")
    
    for i, prev_content in enumerate(previous_chapters):
        if not prev_content:
            continue
        
        prev_normalized = prev_content.lower().replace("\n", "").replace(" ", "")
        
        ngram_size = 10
        content_ngrams = set()
        for j in range(len(content_normalized) - ngram_size + 1):
            content_ngrams.add(content_normalized[j:j+ngram_size])
        
        prev_ngrams = set()
        for j in range(len(prev_normalized) - ngram_size + 1):
            prev_ngrams.add(prev_normalized[j:j+ngram_size])
        
        if content_ngrams and prev_ngrams:
            overlap = len(content_ngrams & prev_ngrams) / len(content_ngrams)
            if overlap > 0.3:
                issues.append({
                    "severity": "high",
                    "description": f"与第{i+1}章内容N-gram重叠率过高: {overlap*100:.1f}%"
                })
                score -= 20
            elif overlap > 0.15:
                issues.append({
                    "severity": "medium",
                    "description": f"与第{i+1}章存在部分重复: {overlap*100:.1f}%"
                })
                score -= 10
    
    return {
        "isValid": score >= 60,
        "score": max(0, score),
        "issues": issues
    }


def main():
    parser = argparse.ArgumentParser(description="小说章节生成器")
    parser.add_argument("--chapter", type=int, required=True, help="章节号")
    parser.add_argument("--project", type=str, required=True, help="项目目录")
    parser.add_argument("--words", type=int, default=2500, help="目标字数")
    parser.add_argument("--pace", type=int, default=3, choices=[1,2,3,4,5], help="节奏等级")
    parser.add_argument("--goal", type=str, default="延续剧情发展", help="本章目标")
    parser.add_argument("--output", type=str, help="输出目录")
    
    args = parser.parse_args()
    
    generator = ChapterGenerator(args.project)
    result = generator.generate_chapter(
        chapter_number=args.chapter,
        target_word_count=args.words,
        pace_level=args.pace,
        chapter_goal=args.goal,
        output_dir=args.output
    )
    
    if result.success:
        print(f"\n🎉 第{result.chapter_number}章生成准备完成！")
        print(f"📝 请使用提示词调用AI模型生成章节内容")
    else:
        print(f"\n❌ 生成失败: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
