#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说全能上下文加载器
支持语义定位、frontmatter索引和精准文件加载
"""

import argparse
import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class FrontmatterIndex:
    """Frontmatter索引项"""
    id: str = ""
    type: str = ""
    name: str = ""
    summary: str = ""
    tags: list = field(default_factory=list)
    file_path: str = ""
    relative_path: str = ""


@dataclass
class LoadedContent:
    """加载的内容"""
    frontmatter: dict = field(default_factory=dict)
    core_content: str = ""
    detail_content: str = ""
    full_content: str = ""


class SemanticMapper:
    """语义定位引擎"""
    
    DIRECTORY_MAP = {
        "character": {
            "path": "设定/人物档案",
            "keywords": ["角色", "人物", "主角", "配角", "char", "角色信息", "人物信息"],
            "type": "character"
        },
        "worldview": {
            "path": "设定/世界观",
            "keywords": ["世界观", "世界", "设定", "规则", "体系", "境界", "功法"],
            "type": "worldview"
        },
        "organization": {
            "path": "设定/组织势力",
            "keywords": ["组织", "势力", "门派", "宗门", "家族", "org", "帮派"],
            "type": "organization"
        },
        "relationship": {
            "path": "设定/关系网络.md",
            "keywords": ["关系", "人物关系", "关系网", "关系网络"],
            "type": "relationship"
        },
        "foreshadow": {
            "path": "状态追踪/伏笔管理",
            "keywords": ["伏笔", "铺垫", "fs", "悬念"],
            "type": "foreshadow"
        },
        "timeline": {
            "path": "状态追踪/时间线.md",
            "keywords": ["时间线", "时间", "事件顺序", "时间轴"],
            "type": "timeline"
        },
        "state": {
            "path": "状态追踪/当前状态.md",
            "keywords": ["当前状态", "角色状态", "状态快照", "状态"],
            "type": "state"
        },
        "outline": {
            "path": "大纲",
            "keywords": ["大纲", "章节大纲", "故事线", "ch", "剧情大纲"],
            "type": "outline"
        },
        "scene": {
            "path": "场景设计",
            "keywords": ["场景", "分场", "sc", "场景设计"],
            "type": "scene"
        },
        "content": {
            "path": "正文",
            "keywords": ["正文", "章节内容", "第", "章"],
            "type": "content"
        },
        "project": {
            "path": "项目信息",
            "keywords": ["项目", "配置", "宪法", "创作", "项目信息"],
            "type": "project"
        }
    }
    
    def __init__(self):
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """构建关键词到目录的反向索引"""
        self.keyword_to_dir = {}
        for dir_key, dir_info in self.DIRECTORY_MAP.items():
            for keyword in dir_info["keywords"]:
                self.keyword_to_dir[keyword.lower()] = dir_key
    
    def locate_directory(self, query: str) -> list:
        """
        根据语义查询定位目录
        返回匹配的目录列表，按匹配度排序
        """
        query_lower = query.lower()
        matched_dirs = {}
        
        for keyword, dir_key in self.keyword_to_dir.items():
            if keyword in query_lower:
                if dir_key not in matched_dirs:
                    matched_dirs[dir_key] = 0
                matched_dirs[dir_key] += len(keyword)
        
        results = []
        for dir_key, score in sorted(matched_dirs.items(), key=lambda x: -x[1]):
            results.append({
                "key": dir_key,
                "path": self.DIRECTORY_MAP[dir_key]["path"],
                "type": self.DIRECTORY_MAP[dir_key]["type"],
                "score": score
            })
        
        return results
    
    def get_directory_info(self, dir_key: str) -> Optional[dict]:
        """获取目录信息"""
        return self.DIRECTORY_MAP.get(dir_key)


class NovelContextLoader:
    """小说上下文加载器"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.mapper = SemanticMapper()
        self._index_cache = {}
    
    def parse_frontmatter(self, content: str) -> tuple:
        """解析markdown文件的frontmatter"""
        if not content.startswith("---"):
            return {}, content
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content
        
        try:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return fm, body
        except yaml.YAMLError:
            return {}, content
    
    def split_content_levels(self, body: str) -> tuple:
        """
        分割内容层级
        返回 (core_content, detail_content)
        """
        if "---" in body:
            parts = body.split("---", 1)
            return parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""
        
        lines = body.split("\n")
        core_lines = []
        detail_lines = []
        in_detail = False
        
        for line in lines:
            if re.match(r"^#+\s*(详细|补充|扩展)", line, re.IGNORECASE):
                in_detail = True
            
            if in_detail:
                detail_lines.append(line)
            else:
                core_lines.append(line)
        
        return "\n".join(core_lines).strip(), "\n".join(detail_lines).strip()
    
    def scan_directory_index(self, dir_path: Path) -> list:
        """扫描目录下所有md文件的frontmatter索引"""
        if not dir_path.exists():
            return []
        
        cache_key = str(dir_path)
        if cache_key in self._index_cache:
            return self._index_cache[cache_key]
        
        indices = []
        
        if dir_path.is_file() and dir_path.suffix == ".md":
            indices.extend(self._index_file(dir_path))
        elif dir_path.is_dir():
            for md_file in dir_path.rglob("*.md"):
                indices.extend(self._index_file(md_file))
        
        self._index_cache[cache_key] = indices
        return indices
    
    def _index_file(self, file_path: Path) -> list:
        """索引单个文件"""
        try:
            content = file_path.read_text(encoding="utf-8")
            fm, body = self.parse_frontmatter(content)
            
            if not fm:
                fm = self._extract_metadata_from_filename(file_path)
            
            index = FrontmatterIndex(
                id=fm.get("id", ""),
                type=fm.get("type", ""),
                name=fm.get("name", file_path.stem),
                summary=fm.get("summary", ""),
                tags=fm.get("tags", []),
                file_path=str(file_path),
                relative_path=str(file_path.relative_to(self.project_path))
            )
            
            return [index]
        except Exception as e:
            return []
    
    def _extract_metadata_from_filename(self, file_path: Path) -> dict:
        """从文件名提取元数据"""
        filename = file_path.stem
        fm = {}
        
        if filename.startswith("char_"):
            fm["type"] = "character"
            parts = filename.split("_", 2)
            if len(parts) >= 3:
                fm["id"] = f"{parts[0]}_{parts[1]}"
                fm["name"] = parts[2]
        elif filename.startswith("org_"):
            fm["type"] = "organization"
            parts = filename.split("_", 2)
            if len(parts) >= 3:
                fm["id"] = f"{parts[0]}_{parts[1]}"
                fm["name"] = parts[2]
        elif filename.startswith("ch_"):
            fm["type"] = "chapter"
            parts = filename.split("_", 2)
            if len(parts) >= 3:
                fm["id"] = f"{parts[0]}_{parts[1]}"
                fm["name"] = parts[2]
        elif filename.startswith("sc_"):
            fm["type"] = "scene"
            parts = filename.split("_", 3)
            if len(parts) >= 4:
                fm["id"] = f"{parts[0]}_{parts[1]}_{parts[2]}"
                fm["name"] = parts[3]
        elif filename.startswith("fs_"):
            fm["type"] = "foreshadow"
            parts = filename.split("_", 2)
            if len(parts) >= 3:
                fm["id"] = f"{parts[0]}_{parts[1]}"
                fm["name"] = parts[2]
        
        return fm
    
    def load_file(self, file_path: Path, level: int = 1) -> Optional[LoadedContent]:
        """加载文件内容"""
        try:
            content = file_path.read_text(encoding="utf-8")
            fm, body = self.parse_frontmatter(content)
            core, detail = self.split_content_levels(body)
            
            return LoadedContent(
                frontmatter=fm,
                core_content=core,
                detail_content=detail,
                full_content=body
            )
        except Exception as e:
            return None
    
    def search_by_query(self, query: str, level: int = 1, index_only: bool = False) -> dict:
        """根据语义查询搜索"""
        located_dirs = self.mapper.locate_directory(query)
        
        if not located_dirs:
            return {
                "success": False,
                "message": f"无法识别查询语义: {query}",
                "results": []
            }
        
        results = []
        for dir_info in located_dirs:
            dir_path = self.project_path / dir_info["path"]
            indices = self.scan_directory_index(dir_path)
            
            matched_indices = self._match_indices(indices, query)
            
            if index_only:
                for idx in matched_indices:
                    results.append({
                        "index": asdict(idx),
                        "content": None
                    })
            else:
                for idx in matched_indices:
                    file_path = Path(idx.file_path)
                    content = self.load_file(file_path, level)
                    
                    result = {
                        "index": asdict(idx),
                        "content": None
                    }
                    
                    if content:
                        if level == 0:
                            result["content"] = None
                        elif level == 1:
                            result["content"] = content.core_content
                        else:
                            result["content"] = content.full_content
                    
                    results.append(result)
        
        return {
            "success": True,
            "message": f"找到 {len(results)} 个匹配结果",
            "located_directories": located_dirs,
            "results": results
        }
    
    def _match_indices(self, indices: list, query: str) -> list:
        """匹配索引项"""
        query_lower = query.lower()
        matched = []
        
        for idx in indices:
            score = 0
            
            if idx.id and idx.id.lower() in query_lower:
                score += 10
            
            if idx.name and idx.name.lower() in query_lower:
                score += 8
            
            for tag in idx.tags:
                if tag.lower() in query_lower:
                    score += 5
            
            if idx.summary and any(kw in idx.summary.lower() for kw in query_lower.split()):
                score += 2
            
            if score > 0:
                matched.append((idx, score))
        
        if not matched:
            return indices[:10]
        
        matched.sort(key=lambda x: -x[1])
        return [m[0] for m in matched]
    
    def search_by_id(self, id_value: str, level: int = 1) -> dict:
        """根据ID精确搜索"""
        for dir_key, dir_info in self.mapper.DIRECTORY_MAP.items():
            dir_path = self.project_path / dir_info["path"]
            indices = self.scan_directory_index(dir_path)
            
            for idx in indices:
                if idx.id == id_value:
                    file_path = Path(idx.file_path)
                    content = self.load_file(file_path, level)
                    
                    return {
                        "success": True,
                        "message": f"找到ID为 {id_value} 的文件",
                        "results": [{
                            "index": asdict(idx),
                            "content": content.full_content if level >= 2 else (
                                content.core_content if level == 1 else None
                            ) if content else None
                        }]
                    }
        
        return {
            "success": False,
            "message": f"未找到ID为 {id_value} 的文件",
            "results": []
        }
    
    def search_by_directory(self, directory: str, level: int = 1, index_only: bool = False) -> dict:
        """根据目录路径搜索"""
        dir_path = self.project_path / directory
        
        if not dir_path.exists():
            return {
                "success": False,
                "message": f"目录不存在: {directory}",
                "results": []
            }
        
        indices = self.scan_directory_index(dir_path)
        results = []
        
        for idx in indices:
            result = {
                "index": asdict(idx),
                "content": None
            }
            
            if not index_only:
                file_path = Path(idx.file_path)
                content = self.load_file(file_path, level)
                
                if content:
                    result["content"] = content.full_content if level >= 2 else (
                        content.core_content if level == 1 else None
                    )
            
            results.append(result)
        
        return {
            "success": True,
            "message": f"在 {directory} 下找到 {len(results)} 个文件",
            "results": results
        }
    
    def search_by_tag(self, tag: str, level: int = 1) -> dict:
        """根据标签搜索"""
        all_indices = []
        
        for dir_key, dir_info in self.mapper.DIRECTORY_MAP.items():
            dir_path = self.project_path / dir_info["path"]
            indices = self.scan_directory_index(dir_path)
            all_indices.extend(indices)
        
        matched = [idx for idx in all_indices if tag.lower() in [t.lower() for t in idx.tags]]
        results = []
        
        for idx in matched:
            file_path = Path(idx.file_path)
            content = self.load_file(file_path, level)
            
            results.append({
                "index": asdict(idx),
                "content": content.full_content if level >= 2 else (
                    content.core_content if level == 1 else None
                ) if content else None
            })
        
        return {
            "success": True,
            "message": f"找到 {len(results)} 个带有标签 '{tag}' 的文件",
            "results": results
        }
    
    def search_by_type(self, type_value: str, level: int = 1) -> dict:
        """根据类型搜索"""
        all_indices = []
        
        for dir_key, dir_info in self.mapper.DIRECTORY_MAP.items():
            dir_path = self.project_path / dir_info["path"]
            indices = self.scan_directory_index(dir_path)
            all_indices.extend(indices)
        
        matched = [idx for idx in all_indices if idx.type == type_value]
        results = []
        
        for idx in matched:
            file_path = Path(idx.file_path)
            content = self.load_file(file_path, level)
            
            results.append({
                "index": asdict(idx),
                "content": content.full_content if level >= 2 else (
                    content.core_content if level == 1 else None
                ) if content else None
            })
        
        return {
            "success": True,
            "message": f"找到 {len(results)} 个类型为 '{type_value}' 的文件",
            "results": results
        }


def format_output(result: dict, index_only: bool = False) -> str:
    """格式化输出"""
    if not result["success"]:
        return f"❌ {result['message']}"
    
    lines = [f"✅ {result['message']}"]
    
    if "located_directories" in result:
        lines.append("\n📂 定位目录:")
        for dir_info in result["located_directories"]:
            lines.append(f"   - {dir_info['path']} (匹配度: {dir_info['score']})")
    
    for i, item in enumerate(result["results"], 1):
        idx = item["index"]
        lines.append(f"\n{'─' * 50}")
        lines.append(f"📄 [{i}] {idx['name']}")
        lines.append(f"   ID: {idx['id']}")
        lines.append(f"   类型: {idx['type']}")
        lines.append(f"   路径: {idx['relative_path']}")
        
        if idx["summary"]:
            lines.append(f"   摘要: {idx['summary']}")
        
        if idx["tags"]:
            lines.append(f"   标签: {', '.join(idx['tags'])}")
        
        if not index_only and item.get("content"):
            lines.append(f"\n   【内容】")
            content_lines = item["content"].split("\n")[:20]
            for line in content_lines:
                lines.append(f"   {line}")
            
            if len(item["content"].split("\n")) > 20:
                lines.append("   ... (内容已截断)")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="小说全能上下文加载器")
    parser.add_argument("--project", required=True, help="项目目录路径")
    parser.add_argument("--query", help="自然语言查询")
    parser.add_argument("--id", dest="id_value", help="文件ID精确匹配")
    parser.add_argument("--directory", help="目录路径")
    parser.add_argument("--tag", help="标签筛选")
    parser.add_argument("--type", dest="type_value", help="类型筛选")
    parser.add_argument("--level", type=int, default=1, choices=[0, 1, 2],
                        help="加载层级: 0=仅索引, 1=核心信息, 2=完整内容")
    parser.add_argument("--index-only", action="store_true", help="仅返回索引信息")
    parser.add_argument("--output", help="输出文件路径(json格式)")
    
    args = parser.parse_args()
    
    loader = NovelContextLoader(args.project)
    
    if args.query:
        result = loader.search_by_query(args.query, args.level, args.index_only)
    elif args.id_value:
        result = loader.search_by_id(args.id_value, args.level)
    elif args.directory:
        result = loader.search_by_directory(args.directory, args.level, args.index_only)
    elif args.tag:
        result = loader.search_by_tag(args.tag, args.level)
    elif args.type_value:
        result = loader.search_by_type(args.type_value, args.level)
    else:
        print("请指定查询方式: --query, --id, --directory, --tag 或 --type")
        return
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 结果已保存到: {args.output}")
    else:
        print(format_output(result, args.index_only))


if __name__ == "__main__":
    main()
