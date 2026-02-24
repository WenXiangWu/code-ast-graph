"""
测试 Git 输入源
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.inputs.git_input import GitCodeInput
from src.core.models import CodeFile


class TestGitInput(unittest.TestCase):
    """Git 输入源测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "test-repo"
        self.repo_path.mkdir()
        
        # 初始化 Git 仓库
        try:
            import git
            self.repo = git.Repo.init(str(self.repo_path))
            
            # 创建测试文件
            test_file = self.repo_path / "Test.java"
            test_file.write_text("public class Test { }", encoding='utf-8')
            
            # 提交
            self.repo.index.add([str(test_file)])
            self.repo.index.commit("Initial commit")
            
            # 创建并切换到 main 分支（如果默认是 master）
            try:
                self.repo.git.checkout('-b', 'main')
            except:
                pass  # 可能已经是 main 分支
            
        except ImportError:
            self.skipTest("GitPython not installed")
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_project_info(self):
        """测试获取项目信息"""
        git_input = GitCodeInput(str(self.repo_path))
        project_info = git_input.get_project_info()
        
        self.assertIsNotNone(project_info)
        self.assertEqual(project_info.name, "test-repo")
        self.assertEqual(project_info.path, str(self.repo_path))
        self.assertIsNotNone(project_info.version)
        self.assertIn('commit_hash', project_info.metadata)
    
    def test_get_files(self):
        """测试获取文件"""
        git_input = GitCodeInput(str(self.repo_path))
        files = list(git_input.get_files())
        
        self.assertGreater(len(files), 0)
        self.assertTrue(any(f.path.name == "Test.java" for f in files))
        
        # 检查文件内容
        test_file = next((f for f in files if f.path.name == "Test.java"), None)
        self.assertIsNotNone(test_file)
        self.assertEqual(test_file.language, "java")
        self.assertIn("class Test", test_file.content)
    
    def test_get_files_with_pattern(self):
        """测试使用模式过滤文件"""
        git_input = GitCodeInput(str(self.repo_path))
        files = list(git_input.get_files(pattern="*.java"))
        
        self.assertGreater(len(files), 0)
        self.assertTrue(all(f.path.suffix == ".java" for f in files))
    
    def test_get_current_commit(self):
        """测试获取当前 commit"""
        git_input = GitCodeInput(str(self.repo_path))
        commit_hash = git_input.get_current_commit()
        
        self.assertIsNotNone(commit_hash)
        self.assertEqual(len(commit_hash), 40)  # Git commit hash 长度


if __name__ == '__main__':
    unittest.main()
