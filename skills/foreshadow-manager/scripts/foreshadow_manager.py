#!/usr/bin/env python3
"""
伏笔管理器 - 管理小说创作中的伏笔生命周期

Usage:
    python foreshadow_manager.py list --project <path> [--status <status>]
    python foreshadow_manager.py create --project <path> --name <name> --chapter <n>
    python foreshadow_manager.py advance --project <path> --id <fs_id> --chapter <n>
    python foreshadow_manager.py resolve --project <path> --id <fs_id> --chapter <n>
"""

import argparse
import yaml
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


def parse_markdown_with_frontmatter(file_path: Path) -> Dict:
    content = file_path.read_text(encoding='utf-8')
    
    if not content.startswith('---'):
        return {'frontmatter': {}, 'body': content}
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {'frontmatter': {}, 'body': content}
    
    frontmatter = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    
    return {'frontmatter': frontmatter, 'body': body}


def write_markdown_with_frontmatter(file_path: Path, frontmatter: Dict, body: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    content = f"---\n{yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)}---\n\n{body}"
    file_path.write_text(content, encoding='utf-8')


class ForeshadowManager:
    
    STATUS_PENDING = 'pending'
    STATUS_ADVANCED = 'advanced'
    STATUS_RESOLVED = 'resolved'
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.fs_dir = self.project_path / '状态追踪' / '伏笔管理'
        self._cache: Dict = {}
    
    def _get_next_id(self) -> str:
        if not self.fs_dir.exists():
            return 'fs_001'
        
        max_num = 0
        for fs_file in self.fs_dir.glob('fs_*.md'):
            try:
                num = int(fs_file.stem.split('_')[1].split('_')[0])
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                continue
        
        return f'fs_{max_num + 1:03d}'
    
    def list_foreshadows(self, status: Optional[str] = None) -> List[Dict]:
        foreshadows = []
        
        if not self.fs_dir.exists():
            return foreshadows
        
        for fs_file in self.fs_dir.glob('fs_*.md'):
            data = parse_markdown_with_frontmatter(fs_file)
            fm = data.get('frontmatter', {})
            
            if status is None or fm.get('status') == status:
                foreshadows.append({
                    'id': fm.get('id', ''),
                    'name': fm.get('name', ''),
                    'status': fm.get('status', self.STATUS_PENDING),
                    'importance': fm.get('importance', 'medium'),
                    'planted_chapter': fm.get('planted_chapter', 0),
                    'characters': fm.get('characters', []),
                    'summary': fm.get('summary', ''),
                    'file_path': fs_file
                })
        
        return sorted(foreshadows, key=lambda x: x['planted_chapter'])
    
    def get_foreshadow(self, fs_id: str) -> Optional[Dict]:
        fs_file = self.fs_dir / f"{fs_id}.md"
        if not fs_file.exists():
            for f in self.fs_dir.glob(f"{fs_id}_*.md"):
                fs_file = f
                break
        
        if not fs_file.exists():
            return None
        
        data = parse_markdown_with_frontmatter(fs_file)
        fm = data.get('frontmatter', {})
        
        return {
            'id': fm.get('id', ''),
            'name': fm.get('name', ''),
            'status': fm.get('status', self.STATUS_PENDING),
            'importance': fm.get('importance', 'medium'),
            'planted_chapter': fm.get('planted_chapter', 0),
            'characters': fm.get('characters', []),
            'summary': fm.get('summary', ''),
            'body': data.get('body', ''),
            'file_path': fs_file
        }
    
    def create_foreshadow(self, name: str, planted_chapter: int, 
                         characters: List[str] = None,
                         importance: str = 'medium',
                         summary: str = '') -> Dict:
        fs_id = self._get_next_id()
        file_name = f"{fs_id}_{name}.md"
        file_path = self.fs_dir / file_name
        
        frontmatter = {
            'id': fs_id,
            'type': 'foreshadow',
            'name': name,
            'status': self.STATUS_PENDING,
            'importance': importance,
            'planted_chapter': planted_chapter,
            'characters': characters or [],
            'summary': summary
        }
        
        body = f"""# 伏笔内容

## 埋设方式

**章节**：第{planted_chapter}章

**埋设方式**：
- 

**具体内容**：
- 

---

## 预期回收

**计划章节**：第N-M章

**回收方式**：
- 

---

## 推进记录

| 章节 | 推进内容 | 触发事件 |
|------|----------|----------|
| | | |

---

## 回收记录

**回收章节**：第N章

**回收方式**：
- 

---

## 备注

"""
        
        write_markdown_with_frontmatter(file_path, frontmatter, body)
        
        return {
            'id': fs_id,
            'name': name,
            'file_path': file_path
        }
    
    def advance_foreshadow(self, fs_id: str, chapter: int, 
                          content: str = '', trigger: str = '') -> bool:
        fs = self.get_foreshadow(fs_id)
        if not fs:
            return False
        
        fm = {'id': fs['id'], 'type': 'foreshadow', 
              'name': fs['name'], 'status': self.STATUS_ADVANCED,
              'importance': fs['importance'], 
              'planted_chapter': fs['planted_chapter'],
              'characters': fs['characters'], 'summary': fs['summary']}
        
        body = fs['body']
        advance_entry = f"| {chapter} | {content or '推进'} | {trigger or '事件'} |\n"
        
        if '## 推进记录' in body:
            lines = body.split('\n')
            new_lines = []
            inserted = False
            for i, line in enumerate(lines):
                new_lines.append(line)
                if '| 章节 | 推进内容' in line and not inserted:
                    new_lines.append(lines[i+1] if i+1 < len(lines) else '| | | |')
                    new_lines.append(advance_entry.strip())
                    inserted = True
            body = '\n'.join(new_lines)
        
        write_markdown_with_frontmatter(fs['file_path'], fm, body)
        return True
    
    def resolve_foreshadow(self, fs_id: str, chapter: int, content: str = '') -> bool:
        fs = self.get_foreshadow(fs_id)
        if not fs:
            return False
        
        fm = {'id': fs['id'], 'type': 'foreshadow',
              'name': fs['name'], 'status': self.STATUS_RESOLVED,
              'importance': fs['importance'],
              'planted_chapter': fs['planted_chapter'],
              'characters': fs['characters'], 'summary': fs['summary']}
        
        body = fs['body']
        resolve_section = f"""
**回收章节**：第{chapter}章

**回收方式**：
- {content or '按预期回收'}

**回收效果**：
- 

**读者反应预期**：
- 
"""
        
        if '## 回收记录' in body:
            body = body.replace('**回收章节**：第N章', resolve_section.strip())
        
        write_markdown_with_frontmatter(fs['file_path'], fm, body)
        return True
    
    def delete_foreshadow(self, fs_id: str) -> bool:
        fs = self.get_foreshadow(fs_id)
        if not fs:
            return False
        
        fs['file_path'].unlink()
        return True


def main():
    parser = argparse.ArgumentParser(description='伏笔管理器')
    parser.add_argument('command', choices=['list', 'create', 'advance', 'resolve', 'delete'])
    parser.add_argument('--project', '-p', required=True, help='项目路径')
    parser.add_argument('--id', '-i', help='伏笔ID')
    parser.add_argument('--name', '-n', help='伏笔名称')
    parser.add_argument('--chapter', '-c', type=int, help='章节号')
    parser.add_argument('--characters', help='相关角色ID（逗号分隔）')
    parser.add_argument('--importance', choices=['high', 'medium', 'low'], default='medium', help='重要性')
    parser.add_argument('--summary', '-s', help='伏笔摘要')
    parser.add_argument('--content', help='推进/回收内容')
    parser.add_argument('--status', choices=['pending', 'advanced', 'resolved'], help='按状态筛选')
    
    args = parser.parse_args()
    manager = ForeshadowManager(Path(args.project))
    
    if args.command == 'list':
        foreshadows = manager.list_foreshadows(args.status)
        
        if not foreshadows:
            print("没有找到伏笔")
            return
        
        print(f"共 {len(foreshadows)} 个伏笔：")
        print("-" * 60)
        
        for fs in foreshadows:
            status_icon = {'pending': '⏳', 'advanced': '🔄', 'resolved': '✅'}
            print(f"{status_icon.get(fs['status'], '?')} {fs['id']} {fs['name']}")
            print(f"   状态: {fs['status']} | 重要性: {fs['importance']} | 埋设: 第{fs['planted_chapter']}章")
            print(f"   摘要: {fs['summary'][:50]}..." if len(fs['summary']) > 50 else f"   摘要: {fs['summary']}")
            print()
    
    elif args.command == 'create':
        if not args.name or not args.chapter:
            print("错误: 创建伏笔需要 --name 和 --chapter 参数")
            return
        
        characters = args.characters.split(',') if args.characters else []
        
        result = manager.create_foreshadow(
            name=args.name,
            planted_chapter=args.chapter,
            characters=characters,
            importance=args.importance,
            summary=args.summary or ''
        )
        
        print(f"✅ 创建伏笔成功: {result['id']} {result['name']}")
        print(f"   文件: {result['file_path']}")
    
    elif args.command == 'advance':
        if not args.id or not args.chapter:
            print("错误: 推进伏笔需要 --id 和 --chapter 参数")
            return
        
        if manager.advance_foreshadow(args.id, args.chapter, args.content or ''):
            print(f"✅ 伏笔 {args.id} 已推进到第{args.chapter}章")
        else:
            print(f"❌ 找不到伏笔 {args.id}")
    
    elif args.command == 'resolve':
        if not args.id or not args.chapter:
            print("错误: 回收伏笔需要 --id 和 --chapter 参数")
            return
        
        if manager.resolve_foreshadow(args.id, args.chapter, args.content or ''):
            print(f"✅ 伏笔 {args.id} 已在第{args.chapter}章回收")
        else:
            print(f"❌ 找不到伏笔 {args.id}")
    
    elif args.command == 'delete':
        if not args.id:
            print("错误: 删除伏笔需要 --id 参数")
            return
        
        if manager.delete_foreshadow(args.id):
            print(f"✅ 伏笔 {args.id} 已删除")
        else:
            print(f"❌ 找不到伏笔 {args.id}")


if __name__ == '__main__':
    main()
