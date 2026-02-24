#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git 输入源使用示例
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.inputs.git_input import GitCodeInput


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python git_input_example.py <git_repo_path>")
        print("\n示例:")
        print("  python git_input_example.py /path/to/git/repo")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    
    try:
        # 1. 创建 Git 输入源
        print(f"初始化 Git 输入源: {repo_path}")
        git_input = GitCodeInput(repo_path, branch='main')
        
        # 2. 获取项目信息
        print("\n获取项目信息...")
        project_info = git_input.get_project_info()
        print(f"  项目名称: {project_info.name}")
        print(f"  项目路径: {project_info.path}")
        print(f"  版本: {project_info.version}")
        print(f"  分支: {project_info.metadata.get('branch', 'N/A')}")
        print(f"  Commit: {project_info.metadata.get('commit_hash', 'N/A')[:8]}")
        
        # 3. 获取 Java 文件
        print("\n获取 Java 文件...")
        java_files = list(git_input.get_files(pattern="*.java"))
        print(f"  找到 {len(java_files)} 个 Java 文件")
        
        # 显示前 5 个文件
        for i, file in enumerate(java_files[:5], 1):
            print(f"  {i}. {file.path} ({file.language}, {len(file.content)} 字符)")
        
        if len(java_files) > 5:
            print(f"  ... 还有 {len(java_files) - 5} 个文件")
        
        # 4. 获取 Python 文件
        print("\n获取 Python 文件...")
        python_files = list(git_input.get_files(pattern="*.py"))
        print(f"  找到 {len(python_files)} 个 Python 文件")
        
        # 5. 获取当前 commit
        print("\n获取当前 commit...")
        commit_hash = git_input.get_current_commit()
        print(f"  Commit Hash: {commit_hash}")
        
        print("\n✅ Git 输入源测试完成！")
        
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请安装: pip install GitPython")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
