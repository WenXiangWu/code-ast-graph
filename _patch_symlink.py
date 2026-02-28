#!/usr/bin/env python3
"""修复 base_agent.py 中 Windows symlink 权限问题，回退到 Junction"""

target_file = r"d:\cursor\bixin-ai-agent-platform\backend\agents\base_agent.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

old = '''    def link_skill(skill_key: str, source_dir: Path) -> bool:
        """尝试为指定 skill 创建符号链接"""
        if skill_key in linked_skills:
            return False
        
        source = source_dir / skill_key
        target = workspace_skills_dir / skill_key
        
        if source.exists() and source.is_dir():
            target.symlink_to(source)
            linked_skills.add(skill_key)
            logger.debug(f"Created skill symlink: {target} -> {source}")
            return True
        return False'''

new = '''    def link_skill(skill_key: str, source_dir: Path) -> bool:
        """尝试为指定 skill 创建符号链接（Windows 下回退到 Junction）"""
        if skill_key in linked_skills:
            return False
        
        source = source_dir / skill_key
        target = workspace_skills_dir / skill_key
        
        if not (source.exists() and source.is_dir()):
            return False
        
        try:
            target.symlink_to(source)
            linked_skills.add(skill_key)
            logger.debug(f"Created skill symlink: {target} -> {source}")
            return True
        except OSError:
            import sys, subprocess
            if sys.platform == "win32":
                try:
                    subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(target), str(source)],
                        check=True, capture_output=True
                    )
                    linked_skills.add(skill_key)
                    logger.debug(f"Created skill junction (win32): {target} -> {source}")
                    return True
                except Exception as e2:
                    logger.warning(f"Skill junction failed for '{skill_key}', skipping: {e2}")
                    return False
            logger.warning(f"Skill symlink failed for '{skill_key}', skipping")
            return False'''

if old in content:
    content = content.replace(old, new, 1)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: link_skill patched with Windows junction fallback")
else:
    print("ERROR: target string not found, check content")
    # 打印当前 link_skill 定义以便对比
    idx = content.find("def link_skill")
    if idx >= 0:
        print("Current link_skill:")
        print(content[idx:idx+600])
