"""
Git 代码输入源
"""

import os
import logging
from pathlib import Path
from typing import Iterator, Optional, List, Dict
from datetime import datetime

try:
    import git
except ImportError:
    git = None
    logging.warning("GitPython not found. Install with: pip install GitPython")

from ..core.interfaces import CodeInput
from ..core.models import CodeFile, ProjectInfo

logger = logging.getLogger(__name__)


class GitCodeInput(CodeInput):
    """Git 代码输入源"""
    
    def __init__(self, repo_path: str, branch: str = 'main'):
        """
        初始化 Git 输入源
        
        Args:
            repo_path: Git 仓库路径
            branch: 分支名称（默认 main）
        """
        if git is None:
            raise ImportError("GitPython is required. Install with: pip install GitPython")
        
        self.repo_path = Path(repo_path).resolve()
        self.branch = branch
        self.repo = None
        
        # 初始化 Git 仓库
        try:
            self.repo = git.Repo(str(self.repo_path))
            logger.info(f"Git 仓库已加载: {self.repo_path}")
        except git.InvalidGitRepositoryError:
            raise ValueError(f"不是有效的 Git 仓库: {repo_path}")
        except Exception as e:
            raise RuntimeError(f"加载 Git 仓库失败: {e}")
    
    def get_files(self, pattern: Optional[str] = None) -> Iterator[CodeFile]:
        """
        获取代码文件迭代器
        
        Args:
            pattern: 文件匹配模式（如 '*.java', '*.py'）
        
        Yields:
            CodeFile: 代码文件对象
        """
        if self.repo is None:
            raise RuntimeError("Git 仓库未初始化")
        
        # 切换到指定分支
        try:
            if self.repo.active_branch.name != self.branch:
                self.repo.git.checkout(self.branch)
                logger.info(f"切换到分支: {self.branch}")
        except git.GitCommandError as e:
            logger.warning(f"切换分支失败（可能分支不存在）: {e}")
        
        # 获取代码文件扩展名映射
        code_extensions = {
            '.java': 'java',
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp'
        }
        
        # 遍历仓库中的所有文件
        for item in self.repo.head.commit.tree.traverse():
            if item.type == 'blob':  # blob 表示文件
                file_path = Path(item.path)
                
                # 检查文件扩展名
                if file_path.suffix not in code_extensions:
                    continue
                
                # 检查模式匹配
                if pattern and not file_path.match(pattern):
                    continue
                
                # 跳过二进制文件（通过检查路径）
                if self._is_binary_file(file_path):
                    continue
                
                try:
                    # 获取文件内容
                    file_content = item.data_stream.read().decode('utf-8', errors='ignore')
                    
                    # 获取文件统计信息
                    file_stat = None
                    full_path = self.repo_path / file_path
                    if full_path.exists():
                        stat = full_path.stat()
                        file_stat = stat
                    
                    # 创建 CodeFile 对象
                    code_file = CodeFile(
                        path=file_path,
                        content=file_content,
                        language=code_extensions.get(file_path.suffix, 'unknown'),
                        encoding='utf-8',
                        size=len(file_content.encode('utf-8')),
                        modified_time=datetime.fromtimestamp(file_stat.st_mtime) if file_stat else None
                    )
                    
                    yield code_file
                    
                except Exception as e:
                    logger.warning(f"读取文件失败 {item.path}: {e}")
                    continue
    
    def get_project_info(self) -> ProjectInfo:
        """获取项目信息"""
        if self.repo is None:
            raise RuntimeError("Git 仓库未初始化")
        
        # 获取项目名称（从目录名或远程 URL）
        project_name = self.repo_path.name
        
        # 尝试从远程 URL 获取项目名
        try:
            if self.repo.remotes:
                remote_url = self.repo.remotes.origin.url
                # 从 URL 提取项目名（如 git@github.com:user/repo.git -> repo）
                if remote_url:
                    project_name = remote_url.split('/')[-1].replace('.git', '')
        except Exception:
            pass
        
        # 获取当前 commit 信息
        commit = self.repo.head.commit
        version = commit.hexsha[:8]  # 使用短 commit hash 作为版本
        
        metadata = {
            'git_repo_path': str(self.repo_path),
            'branch': self.branch,
            'commit_hash': commit.hexsha,
            'commit_message': commit.message.split('\n')[0],
            'commit_time': datetime.fromtimestamp(commit.committed_date).isoformat(),
            'author': commit.author.name if commit.author else None
        }
        
        return ProjectInfo(
            name=project_name,
            path=str(self.repo_path),
            version=version,
            language=None,  # 需要从文件推断
            metadata=metadata
        )
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """判断是否为二进制文件"""
        # 常见的二进制文件扩展名
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',
            '.pdf', '.zip', '.tar', '.gz', '.jar', '.war',
            '.class', '.so', '.dll', '.exe', '.bin'
        }
        return file_path.suffix.lower() in binary_extensions
    
    def get_current_commit(self) -> str:
        """获取当前 commit hash"""
        if self.repo is None:
            raise RuntimeError("Git 仓库未初始化")
        return self.repo.head.commit.hexsha
    
    def get_changes_since(self, commit_hash: str) -> List[Dict]:
        """
        获取自指定 commit 以来的变更
        
        Args:
            commit_hash: 基准 commit hash
        
        Returns:
            变更列表，每个变更包含：
            - file_path: 文件路径
            - change_type: 变更类型（added, modified, deleted, renamed）
        """
        if self.repo is None:
            raise RuntimeError("Git 仓库未初始化")
        
        try:
            last_commit = self.repo.commit(commit_hash)
        except git.BadName:
            logger.warning(f"Commit {commit_hash} 不存在，返回所有文件作为新增")
            return [
                {'file_path': item.path, 'change_type': 'added'}
                for item in self.repo.head.commit.tree.traverse()
                if item.type == 'blob'
            ]
        
        current_commit = self.repo.head.commit
        changes = []
        
        diff = last_commit.diff(current_commit)
        for item in diff:
            if item.deleted_file:
                changes.append({
                    'file_path': item.a_path,
                    'change_type': 'deleted'
                })
            elif item.new_file:
                changes.append({
                    'file_path': item.b_path,
                    'change_type': 'added'
                })
            elif item.renamed_file:
                changes.append({
                    'file_path': item.b_path,
                    'old_path': item.a_path,
                    'change_type': 'renamed'
                })
            else:
                changes.append({
                    'file_path': item.b_path,
                    'change_type': 'modified'
                })
        
        return changes
