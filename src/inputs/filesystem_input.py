"""
文件系统代码输入源
"""

import os
import logging
from pathlib import Path
from typing import Iterator, Optional
from datetime import datetime

from ..core.interfaces import CodeInput
from ..core.models import CodeFile, ProjectInfo

logger = logging.getLogger(__name__)


class FileSystemCodeInput(CodeInput):
    """文件系统代码输入源"""
    
    def __init__(self, root_path: str, exclude_dirs: Optional[list] = None):
        """
        初始化文件系统输入源
        
        Args:
            root_path: 根目录路径
            exclude_dirs: 排除的目录列表
        """
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise ValueError(f"路径不存在: {root_path}")
        
        self.exclude_dirs = set(exclude_dirs or ['.git', 'node_modules', 'target', 'build'])
        
        # 代码文件扩展名映射
        self.code_extensions = {
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
    
    def get_files(self, pattern: Optional[str] = None) -> Iterator[CodeFile]:
        """
        获取代码文件迭代器
        
        Args:
            pattern: 文件匹配模式（如 '*.java', '*.py'）
        
        Yields:
            CodeFile: 代码文件对象
        """
        for file_path in self._scan_files():
            # 检查模式匹配
            if pattern and not file_path.match(pattern):
                continue
            
            try:
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 获取文件统计信息
                stat = file_path.stat()
                
                # 创建 CodeFile 对象
                code_file = CodeFile(
                    path=file_path.relative_to(self.root_path),
                    content=content,
                    language=self.code_extensions.get(file_path.suffix, 'unknown'),
                    encoding='utf-8',
                    size=stat.st_size,
                    modified_time=datetime.fromtimestamp(stat.st_mtime)
                )
                
                yield code_file
                
            except Exception as e:
                logger.warning(f"读取文件失败 {file_path}: {e}")
                continue
    
    def get_project_info(self) -> ProjectInfo:
        """获取项目信息"""
        project_name = self.root_path.name
        
        metadata = {
            'root_path': str(self.root_path),
            'scan_time': datetime.now().isoformat()
        }
        
        return ProjectInfo(
            name=project_name,
            path=str(self.root_path),
            version=None,
            language=None,
            metadata=metadata
        )
    
    def _scan_files(self) -> Iterator[Path]:
        """扫描代码文件"""
        for root, dirs, files in os.walk(self.root_path):
            # 排除目录
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            
            for file_name in files:
                file_path = Path(root) / file_name
                
                # 检查文件扩展名
                if file_path.suffix not in self.code_extensions:
                    continue
                
                # 跳过二进制文件
                if self._is_binary_file(file_path):
                    continue
                
                yield file_path
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """判断是否为二进制文件"""
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',
            '.pdf', '.zip', '.tar', '.gz', '.jar', '.war',
            '.class', '.so', '.dll', '.exe', '.bin'
        }
        return file_path.suffix.lower() in binary_extensions
