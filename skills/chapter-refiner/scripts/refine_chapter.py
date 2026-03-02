#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说章节精修提示词构建器
参考: chapterRefiningService.js
功能: 加载上下文、合并模板、构建精修提示词
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml


@dataclass
class TemplateInfo:
    """模板信息"""
    id: str
    name: str
    category: str
    applicable_categories: List[str]
    difficulty: str
    estimated_time: int
    tags: List[str]
    default_selected: bool
    emoji: str
    description: str
    prompt_content: str = ""


@dataclass
class RefiningRequest:
    """精修请求"""
    chapter_text: str
    chapter_number: Optional[int] = None
    novel_category: str = "general"
    template_ids: List[str] = field(default_factory=list)
    fusion_strength: str = "balanced"
    output_file: Optional[str] = None


@dataclass
class RefiningPrompt:
    """精修提示词"""
    system_prompt: str
    user_message: str
    combined_prompt: str
    templates_used: List[str]
    context_loaded: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class TemplateLoader:
    """模板加载器"""
    
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self._cache: Dict[str, TemplateInfo] = {}
    
    def load_all_templates(self) -> List[TemplateInfo]:
        """加载所有模板"""
        if self._cache:
            return list(self._cache.values())
        
        templates = []
        for md_file in self.templates_dir.glob("*.md"):
            if md_file.name == "README.md":
                continue
            
            template = self._parse_template_file(md_file)
            if template:
                templates.append(template)
                self._cache[template.id] = template
        
        return templates
    
    def load_template(self, template_id: str) -> Optional[TemplateInfo]:
        """加载单个模板"""
        if template_id in self._cache:
            return self._cache[template_id]
        
        for md_file in self.templates_dir.glob("*.md"):
            template = self._parse_template_file(md_file)
            if template and template.id == template_id:
                self._cache[template_id] = template
                return template
        
        return None
    
    def load_templates_by_ids(self, template_ids: List[str]) -> List[TemplateInfo]:
        """根据ID列表加载模板"""
        templates = []
        for tid in template_ids:
            template = self.load_template(tid)
            if template:
                templates.append(template)
        return templates
    
    def _parse_template_file(self, file_path: Path) -> Optional[TemplateInfo]:
        """解析模板文件"""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            if not content.startswith("---"):
                return None
            
            parts = content.split("---", 2)
            if len(parts) < 3:
                return None
            
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            
            return TemplateInfo(
                id=fm.get("id", file_path.stem),
                name=fm.get("name", file_path.stem),
                category=fm.get("category", "未分类"),
                applicable_categories=fm.get("applicable_categories", []),
                difficulty=fm.get("difficulty", "medium"),
                estimated_time=fm.get("estimated_time", 120),
                tags=fm.get("tags", []),
                default_selected=fm.get("default_selected", False),
                emoji=fm.get("emoji", "📝"),
                description=fm.get("description", ""),
                prompt_content=body
            )
        except Exception as e:
            print(f"⚠️ 解析模板文件失败 {file_path}: {e}")
            return None
    
    def get_default_templates(self, novel_category: str = "general") -> List[TemplateInfo]:
        """获取默认模板"""
        all_templates = self.load_all_templates()
        
        defaults = []
        for t in all_templates:
            if t.default_selected:
                if not t.applicable_categories or novel_category in t.applicable_categories or "general" in t.applicable_categories:
                    defaults.append(t)
        
        return defaults
    
    def merge_template_prompts(self, template_ids: List[str]) -> str:
        """合并多个模板的提示词"""
        templates = self.load_templates_by_ids(template_ids)
        
        if not templates:
            return ""
        
        merged = []
        for t in templates:
            merged.append(f"【{t.emoji} {t.name}】\n{t.prompt_content}")
        
        return "\n\n---\n\n".join(merged)


class ContextLoader:
    """上下文加载器 - 调用novel-context-loader"""
    
    def __init__(self, project_path: Path, context_loader_script: Optional[Path] = None):
        self.project_path = project_path
        self.context_loader_script = context_loader_script
    
    def load_context_for_refining(self, chapter_text: str, chapter_number: Optional[int] = None) -> str:
        """为精修加载相关上下文"""
        context_parts = []
        
        context_parts.append(self._load_character_context())
        context_parts.append(self._load_worldview_context())
        context_parts.append(self._load_outline_context(chapter_number))
        context_parts.append(self._load_foreshadow_context())
        
        non_empty = [p for p in context_parts if p.strip()]
        
        if not non_empty:
            return ""
        
        return "\n\n".join(non_empty)
    
    def _load_character_context(self) -> str:
        """加载角色上下文"""
        char_dir = self.project_path / "设定" / "人物档案"
        if not char_dir.exists():
            return ""
        
        contexts = []
        for md_file in list(char_dir.glob("*.md"))[:5]:
            try:
                content = md_file.read_text(encoding="utf-8")
                fm, body = self._parse_frontmatter(content)
                name = fm.get("name", md_file.stem)
                summary = fm.get("summary", "")
                
                core_content = self._extract_core_content(body)
                
                if core_content:
                    contexts.append(f"**{name}**: {summary}\n{core_content[:500]}")
            except:
                continue
        
        if contexts:
            return f"【角色信息】\n" + "\n\n".join(contexts)
        return ""
    
    def _load_worldview_context(self) -> str:
        """加载世界观上下文"""
        wv_dir = self.project_path / "设定" / "世界观"
        if not wv_dir.exists():
            return ""
        
        contexts = []
        for md_file in list(wv_dir.glob("*.md"))[:3]:
            try:
                content = md_file.read_text(encoding="utf-8")
                fm, body = self._parse_frontmatter(content)
                name = fm.get("name", md_file.stem)
                core_content = self._extract_core_content(body)
                
                if core_content:
                    contexts.append(f"**{name}**:\n{core_content[:400]}")
            except:
                continue
        
        if contexts:
            return f"【世界观设定】\n" + "\n\n".join(contexts)
        return ""
    
    def _load_outline_context(self, chapter_number: Optional[int]) -> str:
        """加载大纲上下文"""
        if not chapter_number:
            return ""
        
        outline_dir = self.project_path / "大纲"
        if not outline_dir.exists():
            return ""
        
        for md_file in outline_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                fm, _ = self._parse_frontmatter(content)
                
                if fm.get("chapterNumber") == chapter_number or fm.get("chapter_number") == chapter_number:
                    name = fm.get("name", md_file.stem)
                    summary = fm.get("summary", "")
                    return f"【本章大纲】\n**第{chapter_number}章 {name}**: {summary}"
            except:
                continue
        
        return ""
    
    def _load_foreshadow_context(self) -> str:
        """加载伏笔上下文"""
        fs_dir = self.project_path / "状态追踪" / "伏笔管理"
        if not fs_dir.exists():
            return ""
        
        contexts = []
        for md_file in list(fs_dir.glob("*.md"))[:3]:
            try:
                content = md_file.read_text(encoding="utf-8")
                fm, body = self._parse_frontmatter(content)
                
                status = fm.get("status", "")
                if status in ["pending", "in_progress"]:
                    name = fm.get("name", md_file.stem)
                    summary = fm.get("summary", "")
                    contexts.append(f"- **{name}** ({status}): {summary}")
            except:
                continue
        
        if contexts:
            return f"【待回收伏笔】\n" + "\n".join(contexts)
        return ""
    
    def _parse_frontmatter(self, content: str) -> tuple:
        """解析frontmatter"""
        if not content.startswith("---"):
            return {}, content
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content
        
        try:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return fm, body
        except:
            return {}, content
    
    def _extract_core_content(self, body: str) -> str:
        """提取核心内容"""
        if "---" in body:
            return body.split("---")[0].strip()
        return body


class GenreRulesBuilder:
    """类别规则构建器"""
    
    GENRE_RULES = {
        "fantasy": """
【奇幻/玄幻/仙侠特殊规则】
- 允许古风词汇：眼眸、灵力、神识、威压、气息
- 战斗描写可用四字短语增强气势
- 修炼相关表达可意象化（"灵气如潮水般涌入"）
- 对话可偏文言风格，但不要过度
""",
        "historical": """
【历史类特殊规则】
- 允许文言化词汇和表达
- 对话需符合时代背景
- 注意礼仪、称谓、官职的准确性
- 环境描写要有古典意象
""",
        "science-fiction": """
【科幻类特殊规则】
- 允许理性表达词汇：分析、推测、计算、逻辑
- 科技描写要准确，避免明显错误
- 对话可简练理性
- 注意科学术语的正确使用
""",
        "romance": """
【言情类特殊规则】
- 心理描写要细腻但具体，避免抽象
- 禁止套路表达：心如鹿撞、小鹿乱撞、心跳加速
- 情感递进要自然，不要跳跃
- 肢体语言要服务于情感表达
""",
        "urban": """
【都市类特殊规则】
- 对话要口语化，贴近现代生活
- 禁止文言词汇和古风表达
- 环境描写要有现代都市细节
- 节奏要快，避免冗长铺垫
""",
        "mystery": """
【悬疑类特殊规则】
- 信息揭露要有节奏，不要一次说完
- 线索要精准，避免误导读者
- 多用观察性表达，少用心理直述
- 氛围要压抑紧张
""",
        "web-novel": """
【网文特殊规则】
- 每300字要有进展，避免注水
- 爽点要突出，不要平淡带过
- 对话要干脆，不要拖泥带水
- 可以使用网文特有的节奏手法（断章、悬念钩子）
""",
        "action": """
【动作冒险类特殊规则】
- 战斗场景多用短句连击
- 动作描写要有力量感和画面感
- 可用拟声词增强临场感
- 时间感要压缩，制造紧迫感
""",
        "general": """
【通用规则】
- 文风自然流畅，不刻意雕琢
- 对话符合人物性格
- 描写适度，不过度铺陈
"""
    }
    
    @classmethod
    def get_genre_rules(cls, category: str) -> str:
        """获取类别规则"""
        return cls.GENRE_RULES.get(category, cls.GENRE_RULES["general"])
    
    @classmethod
    def get_category_name(cls, category: str) -> str:
        """获取类别中文名"""
        names = {
            "fantasy": "奇幻/玄幻/仙侠",
            "historical": "历史",
            "science-fiction": "科幻",
            "romance": "言情",
            "urban": "都市",
            "mystery": "悬疑",
            "web-novel": "网络小说",
            "action": "动作冒险",
            "general": "通用"
        }
        return names.get(category, category)


class AntiAiRulesBuilder:
    """去AI化规则构建器"""
    
    SYSTEM_PROMPT_BASE = '''你是一位专业的网络文学编辑，拥有丰富的小说精修经验。
你的任务是根据用户提供的精修方向，对章节内容进行精修和优化。

【核心原则】
1. 必须做出实质性修改，不能原样返回
2. 修改内容而非仅仅改标点符号或空格
3. 每次精修至少要有5处以上的内容改动
4. 保持原文的核心剧情、角色性格和作者独特声音

【文风要求 — 去AI化（最高优先级）】

1. **A类禁用词（出现即替换，零容忍）**：
   "心中暗道" "眼中闪过一丝" "嘴角微微上扬" "深吸一口气"
   "仿佛在诉说" "宛如...一般" "情不自禁" "低眸" "勾唇"
   "薄唇轻启" "墨发" "凤眸" "在这一刻"
   ↳ 这些词必须替换为更自然的表达

2. **B类高频词（每千字最多1次，超出则替换）**：
   "不禁" "此刻" "不由得" "下意识" "眼眸" "心绪"
   "然而" "突然" "竟然" "缓缓" "微微" "轻轻" "淡淡"
   "就在这时" "与此同时" "话音刚落" "猛地" "忽然"
   ↳ 这些词AI使用频率极高，需要严格控制

3. **句式禁令**：
   - 禁止连续3句以上用"他/她"开头 → 改用环境/动作/对话开头
   - 禁止"XX了XX，又XX了XX"的排比堆砌
   - 禁止"感到/感觉到/意识到"直接描写心理 → 改用动作、表情、生理反应间接表达
   - 禁止"不知道从什么时候开始""说不清道不明"等模糊表达

4. **对话标签去AI化**：
   | 禁用 | 替换为 |
   |------|--------|
   | "说道"、"开口道"、"出声道" | 动作标签（如"他扬起眉"、"她别过脸"） |
   | "回应道"、"接口道" | 直接写对话，或用神态描写 |
   
   > 同一种对话标签在全文最多出现2次

5. **节奏变化要求**：
   - 段落长度要有明显变化（短段、中段、长段交替）
   - 句子长度要有变化（避免全是20-30字的中等句）
   - 关键时刻用短句加速，舒缓场景可用长句

【推荐写法 — 正向引导】

✅ **动作代替情绪**："他很生气" → "他攥紧拳头，指甲掐进掌心"
✅ **环境暗示情绪**："他心情沉重" → "雨声砸在窗上"
✅ **对话穿插动作**："'走吧'他说道" → "他转身，'走吧'"
✅ **五感细节代替概括**：触觉/嗅觉/听觉比视觉更有沉浸感
✅ **长短句交替**：短句加速，长句放缓，单句成段制造停顿

【输出格式要求】

精修完成后，请在文末添加精修总结：

```
【精修总结】
- 修改数量：X处
- 主要改动：[列举3-5个主要改动点]
- 删除的AI痕迹：[列举删除的A类/B类禁用词]
```

请直接输出精修后的正文内容，不要添加任何解释或说明。'''
    
    @classmethod
    def build_system_prompt(cls, novel_category: str) -> str:
        """构建系统提示词"""
        genre_rules = GenreRulesBuilder.get_genre_rules(novel_category)
        
        return f'''{cls.SYSTEM_PROMPT_BASE}

{genre_rules}'''


class RefiningPromptBuilder:
    """精修提示词构建器"""
    
    def __init__(self, templates_dir: Path, project_path: Optional[Path] = None):
        self.template_loader = TemplateLoader(templates_dir)
        self.context_loader = ContextLoader(project_path) if project_path else None
    
    def build_prompt(self, request: RefiningRequest) -> RefiningPrompt:
        """构建完整的精修提示词"""
        
        system_prompt = AntiAiRulesBuilder.build_system_prompt(request.novel_category)
        
        template_ids = request.template_ids
        if not template_ids:
            default_templates = self.template_loader.get_default_templates(request.novel_category)
            template_ids = [t.id for t in default_templates]
        
        merged_prompt = self.template_loader.merge_template_prompts(template_ids)
        
        context_info = ""
        context_loaded = False
        if self.context_loader:
            context_info = self.context_loader.load_context_for_refining(
                request.chapter_text, 
                request.chapter_number
            )
            context_loaded = bool(context_info.strip())
        
        category_name = GenreRulesBuilder.get_category_name(request.novel_category)
        
        user_message = self._build_user_message(
            request.chapter_text,
            category_name,
            merged_prompt,
            context_info
        )
        
        combined_prompt = f"""# System Prompt

{system_prompt}

---

# User Message

{user_message}"""
        
        return RefiningPrompt(
            system_prompt=system_prompt,
            user_message=user_message,
            combined_prompt=combined_prompt,
            templates_used=template_ids,
            context_loaded=context_loaded,
            metadata={
                "chapter_number": request.chapter_number,
                "novel_category": request.novel_category,
                "fusion_strength": request.fusion_strength,
                "word_count": len(request.chapter_text)
            }
        )
    
    def _build_user_message(self, chapter_text: str, category_name: str, 
                            merged_prompt: str, context_info: str) -> str:
        """构建用户消息"""
        parts = [f"""【要精修的文本】
```
{chapter_text}
```

【精修要求】
小说类别：{category_name}

{merged_prompt}"""]
        
        if context_info.strip():
            parts.append(f"""
【相关背景信息】(供参考，确保精修不偏离设定)
{context_info}""")
        
        parts.append("""
请根据上述要求对文本进行精修。直接输出精修后的内容，文末附上精修总结。""")
        
        return "\n".join(parts)


def list_templates(templates_dir: Path, novel_category: Optional[str] = None):
    """列出所有可用模板"""
    loader = TemplateLoader(templates_dir)
    templates = loader.load_all_templates()
    
    print("\n📋 可用的精修模板：\n")
    print("=" * 70)
    
    current_category = None
    for t in sorted(templates, key=lambda x: (x.category, x.name)):
        if t.category != current_category:
            current_category = t.category
            print(f"\n【{current_category}】")
        
        default_mark = "✅" if t.default_selected else "  "
        applicable = ", ".join(t.applicable_categories[:3]) if t.applicable_categories else "全部"
        
        print(f"  {default_mark} {t.emoji} {t.name}")
        print(f"      ID: {t.id}")
        print(f"      难度: {t.difficulty} | 耗时: {t.estimated_time}s | 适用: {applicable}")
        print(f"      描述: {t.description[:50]}...")
    
    print("\n" + "=" * 70)
    print(f"共 {len(templates)} 个模板")
    print("✅ = 默认选中")


def main():
    parser = argparse.ArgumentParser(
        description="小说章节精修提示词构建器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有模板
  python refine_chapter.py --list-templates
  
  # 构建精修提示词
  python refine_chapter.py --input chapter.txt --project ./my-novel
  
  # 指定模板
  python refine_chapter.py --input chapter.txt --templates pacing-optimization dialogue-refine
  
  # 指定类别
  python refine_chapter.py --input chapter.txt --category fantasy
        """
    )
    
    parser.add_argument("--input", "-i", help="输入章节文件路径")
    parser.add_argument("--output", "-o", help="输出提示词文件路径")
    parser.add_argument("--project", "-p", help="小说项目目录")
    parser.add_argument("--chapter", "-c", type=int, help="章节编号")
    parser.add_argument("--category", default="general", 
                       choices=["general", "fantasy", "historical", "science-fiction", 
                               "romance", "urban", "mystery", "web-novel", "action"],
                       help="小说类别")
    parser.add_argument("--templates", "-t", nargs="+", help="模板ID列表")
    parser.add_argument("--list-templates", action="store_true", help="列出所有可用模板")
    parser.add_argument("--format", choices=["full", "system", "user", "json"], 
                       default="full", help="输出格式")
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    templates_dir = script_dir.parent / "templates"
    
    if args.list_templates:
        list_templates(templates_dir, args.category)
        return
    
    if not args.input:
        parser.error("请指定输入文件: --input <file>")
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 输入文件不存在: {input_path}")
        sys.exit(1)
    
    chapter_text = input_path.read_text(encoding="utf-8")
    
    project_path = Path(args.project) if args.project else None
    
    builder = RefiningPromptBuilder(templates_dir, project_path)
    
    request = RefiningRequest(
        chapter_text=chapter_text,
        chapter_number=args.chapter,
        novel_category=args.category,
        template_ids=args.templates or []
    )
    
    prompt = builder.build_prompt(request)
    
    if args.format == "json":
        output_content = json.dumps(asdict(prompt), ensure_ascii=False, indent=2)
    elif args.format == "system":
        output_content = prompt.system_prompt
    elif args.format == "user":
        output_content = prompt.user_message
    else:
        output_content = prompt.combined_prompt
    
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output_content, encoding="utf-8")
        print(f"✅ 提示词已保存到: {output_path}")
    else:
        print(output_content)
    
    print(f"\n📊 统计信息:", file=sys.stderr)
    print(f"   - 使用模板: {len(prompt.templates_used)} 个", file=sys.stderr)
    print(f"   - 上下文加载: {'是' if prompt.context_loaded else '否'}", file=sys.stderr)
    print(f"   - 提示词长度: {len(prompt.combined_prompt)} 字符", file=sys.stderr)


if __name__ == "__main__":
    main()
