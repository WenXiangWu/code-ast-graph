#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git 输入全流程集成测试
"""

import sys
import io
from pathlib import Path

# 设置 UTF-8 编码（Windows 兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.inputs.git_input import GitCodeInput
from src.services.scan_service import ScanService


class MockParser:
    """模拟解析器"""
    
    def supported_languages(self):
        return ['java', 'python']
    
    def can_parse(self, file):
        return file.language in ['java', 'python']
    
    def parse(self, file, project_info):
        from src.core.models import ParseResult, CodeEntity, EntityType
        
        entity = CodeEntity(
            id=f"{project_info.name}:{file.path}",
            type=EntityType.TYPE,
            name=file.path.stem,
            qualified_name=f"com.example.{file.path.stem}",
            file_path=str(file.path),
            start_line=1,
            end_line=10,
            language=file.language,
            project=project_info.name
        )
        
        return ParseResult(
            entities=[entity],
            relationships=[],
            errors=[],
            metadata={'file_count': 1}
        )
    
    def parse_project(self, input_source, project_info):
        from src.core.models import ParseResult, CodeEntity, EntityType
        
        entities = []
        file_count = 0
        
        for file in input_source.get_files():
            if self.can_parse(file):
                entity = CodeEntity(
                    id=f"{project_info.name}:{file.path}",
                    type=EntityType.TYPE,
                    name=file.path.stem,
                    qualified_name=f"com.example.{file.path.stem}",
                    file_path=str(file.path),
                    start_line=1,
                    end_line=10,
                    language=file.language,
                    project=project_info.name
                )
                entities.append(entity)
                file_count += 1
        
        return ParseResult(
            entities=entities,
            relationships=[],
            errors=[],
            metadata={'file_count': file_count}
        )


class MockStorage:
    """模拟存储"""
    
    def __init__(self):
        self.connected = False
        self.projects = set()
        self.entities = []
        self.relationships = []
        self.in_transaction = False
    
    def connect(self):
        self.connected = True
        return True
    
    def disconnect(self):
        self.connected = False
    
    def is_connected(self):
        return self.connected
    
    def project_exists(self, project_name):
        return project_name in self.projects
    
    def begin_transaction(self):
        self.in_transaction = True
    
    def commit_transaction(self):
        self.in_transaction = False
    
    def rollback_transaction(self):
        self.entities = []
        self.relationships = []
        self.in_transaction = False
    
    def create_entities(self, entities):
        if not self.in_transaction:
            raise RuntimeError("Not in transaction")
        self.entities.extend(entities)
        if entities:
            self.projects.add(entities[0].project)
        return len(entities)
    
    def create_relationships(self, relationships):
        if not self.in_transaction:
            raise RuntimeError("Not in transaction")
        self.relationships.extend(relationships)
        return len(relationships)


def main():
    """主函数"""
    print("=" * 60)
    print("Git 输入全流程集成测试")
    print("=" * 60)
    
    # 检查是否有 Git 仓库路径参数
    if len(sys.argv) < 2:
        print("\n用法: python test_git_input_integration.py <git_repo_path>")
        print("\n示例:")
        print("  python test_git_input_integration.py /path/to/git/repo")
        print("  python test_git_input_integration.py ./git-repos/my-project")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    
    try:
        # 1. 创建 Git 输入源
        print(f"\n[1] 初始化 Git 输入源: {repo_path}")
        git_input = GitCodeInput(repo_path)
        print("   [OK] Git 输入源初始化成功")
        
        # 2. 获取项目信息
        print("\n[2] 获取项目信息...")
        project_info = git_input.get_project_info()
        print(f"   [OK] 项目名称: {project_info.name}")
        print(f"   [OK] 项目路径: {project_info.path}")
        print(f"   [OK] 版本: {project_info.version}")
        print(f"   [OK] Commit Hash: {project_info.metadata.get('commit_hash', 'N/A')[:8]}")
        
        # 3. 获取文件列表
        print("\n[3] 获取代码文件列表...")
        files = list(git_input.get_files(pattern="*.java"))
        print(f"   [OK] 找到 {len(files)} 个 Java 文件")
        if files:
            print(f"   [示例] 文件: {files[0].path.name} ({files[0].language})")
        
        # 4. 创建解析器和存储
        print("\n[4] 初始化解析器和存储...")
        parser = MockParser()
        storage = MockStorage()
        print("   [OK] 解析器和存储初始化成功")
        
        # 5. 创建扫描服务
        print("\n[5] 创建扫描服务...")
        scan_service = ScanService(
            input_source=git_input,
            parser=parser,
            storage=storage
        )
        print("   [OK] 扫描服务创建成功")
        
        # 6. 执行扫描
        print("\n[6] 执行项目扫描...")
        result = scan_service.scan_project(
            project_name=project_info.name,
            force_rescan=True
        )
        
        if result['success']:
            print(f"   [OK] 扫描成功")
            print(f"   [OK] 实体数量: {result['entities_count']}")
            print(f"   [OK] 关系数量: {result['relationships_count']}")
            if result.get('errors'):
                print(f"   [WARN] 错误数量: {len(result['errors'])}")
        else:
            print(f"   [FAIL] 扫描失败: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
        # 7. 验证结果
        print("\n[7] 验证扫描结果...")
        if storage.project_exists(project_info.name):
            print(f"   [OK] 项目已存储在数据库中")
        else:
            print(f"   [FAIL] 项目未存储在数据库中")
            sys.exit(1)
        
        if len(storage.entities) == result['entities_count']:
            print(f"   [OK] 实体数量验证通过: {len(storage.entities)}")
        else:
            print(f"   [FAIL] 实体数量不匹配: 期望 {result['entities_count']}, 实际 {len(storage.entities)}")
            sys.exit(1)
        
        print("\n" + "=" * 60)
        print("[SUCCESS] Git 输入全流程测试通过！")
        print("=" * 60)
        print(f"\n总结:")
        print(f"  - 项目: {project_info.name}")
        print(f"  - 文件数: {len(files)}")
        print(f"  - 实体数: {result['entities_count']}")
        print(f"  - 关系数: {result['relationships_count']}")
        
    except ImportError as e:
        print(f"\n[ERROR] 缺少依赖: {e}")
        print("请安装: pip install GitPython")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
