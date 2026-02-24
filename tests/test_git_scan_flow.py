"""
测试 Git 输入全流程
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.inputs.git_input import GitCodeInput
from src.inputs.filesystem_input import FileSystemCodeInput
from src.services.scan_service import ScanService


class MockParser:
    """模拟解析器（用于测试）"""
    
    def supported_languages(self):
        return ['java']
    
    def can_parse(self, file):
        return file.language == 'java'
    
    def parse(self, file, project_info):
        from src.core.models import ParseResult, CodeEntity, EntityType
        
        # 简单解析：创建一个类型实体
        entity = CodeEntity(
            id=f"{project_info.name}:{file.path}",
            type=EntityType.TYPE,
            name="TestClass",
            qualified_name=f"com.example.TestClass",
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
    """模拟存储（用于测试）"""
    
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
        self.projects.add(entities[0].project if entities else "")
        return len(entities)
    
    def create_relationships(self, relationships):
        if not self.in_transaction:
            raise RuntimeError("Not in transaction")
        self.relationships.extend(relationships)
        return len(relationships)


class TestGitScanFlow(unittest.TestCase):
    """Git 扫描全流程测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "test-repo"
        self.repo_path.mkdir()
        
        # 初始化 Git 仓库
        try:
            import git
            self.repo = git.Repo.init(str(self.repo_path))
            
            # 创建测试 Java 文件
            java_file = self.repo_path / "Test.java"
            java_file.write_text("""
public class Test {
    public void method() {
        System.out.println("Hello");
    }
}
""", encoding='utf-8')
            
            # 创建另一个 Java 文件
            java_file2 = self.repo_path / "Another.java"
            java_file2.write_text("""
public class Another {
    public void doSomething() {
    }
}
""", encoding='utf-8')
            
            # 提交
            self.repo.index.add([str(java_file), str(java_file2)])
            self.repo.index.commit("Add test files")
            
            # 创建并切换到 main 分支
            try:
                self.repo.git.checkout('-b', 'main')
            except:
                pass
            
        except ImportError:
            self.skipTest("GitPython not installed")
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_git_input_scan_flow(self):
        """测试 Git 输入扫描全流程"""
        # 1. 创建 Git 输入源
        git_input = GitCodeInput(str(self.repo_path))
        
        # 2. 创建模拟解析器和存储
        parser = MockParser()
        storage = MockStorage()
        
        # 3. 创建扫描服务
        scan_service = ScanService(
            input_source=git_input,
            parser=parser,
            storage=storage
        )
        
        # 4. 执行扫描
        result = scan_service.scan_project(
            project_name="test-project",
            force_rescan=True
        )
        
        # 5. 验证结果
        self.assertTrue(result['success'])
        self.assertGreater(result['entities_count'], 0)
        self.assertEqual(result['entities_count'], 2)  # 两个 Java 文件
        self.assertIn('project_info', result)
        self.assertEqual(result['project_info']['name'], "test-project")
    
    def test_git_input_get_files(self):
        """测试 Git 输入获取文件"""
        git_input = GitCodeInput(str(self.repo_path))
        
        files = list(git_input.get_files(pattern="*.java"))
        
        self.assertGreaterEqual(len(files), 2)
        file_names = [f.path.name for f in files]
        self.assertIn("Test.java", file_names)
        self.assertIn("Another.java", file_names)
    
    def test_git_input_project_info(self):
        """测试 Git 输入项目信息"""
        git_input = GitCodeInput(str(self.repo_path))
        project_info = git_input.get_project_info()
        
        self.assertEqual(project_info.name, "test-repo")
        self.assertIsNotNone(project_info.version)
        self.assertIn('commit_hash', project_info.metadata)
        self.assertIn('branch', project_info.metadata)


if __name__ == '__main__':
    unittest.main()
