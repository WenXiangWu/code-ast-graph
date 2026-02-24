"""
Java Parser 配置
"""

import os
import fnmatch
from dataclasses import dataclass, field
from typing import Optional, List, Set


@dataclass
class JavaParserConfig:
    """Java 解析器配置"""
    
    # 功能开关
    enabled: bool = True
    
    # 扫描配置
    exclude_dirs: List[str] = field(default_factory=lambda: ['target', 'build', '.git', 'node_modules', 'out', 'bin', 'test'])
    """排除的目录列表"""
    
    exclude_file_patterns: List[str] = field(default_factory=lambda: ['*Test.java', '*Tests.java', '*Mock.java'])
    """排除的文件模式（支持通配符）"""
    
    include_file_extensions: List[str] = field(default_factory=lambda: ['.java'])
    """包含的文件扩展名列表"""
    
    exclude_annotations: List[str] = field(default_factory=lambda: [])
    """排除的注解名称列表（带此注解的类/方法/字段将被忽略）"""
    
    exclude_annotation_patterns: List[str] = field(default_factory=lambda: [])
    """排除的注解模式（支持通配符，如 '*.Test', '*.Mock'）"""
    
    def should_exclude_file(self, file_path: str) -> bool:
        """
        检查文件是否应该被排除
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否应该排除
        """
        # 检查文件扩展名
        file_ext = os.path.splitext(file_path)[1]
        if file_ext not in self.include_file_extensions:
            return True
        
        # 检查文件模式
        file_name = os.path.basename(file_path)
        for pattern in self.exclude_file_patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return True
        
        return False
    
    def should_exclude_annotation(self, annotation_name: str) -> bool:
        """
        检查注解是否应该被排除
        
        Args:
            annotation_name: 注解名称（可以是简单名或FQN）
            
        Returns:
            是否应该排除
        """
        # 检查精确匹配
        if annotation_name in self.exclude_annotations:
            return True
        
        # 检查模式匹配
        for pattern in self.exclude_annotation_patterns:
            if fnmatch.fnmatch(annotation_name, pattern):
                return True
        
        # 检查简单名称匹配（如果注解名是FQN，也检查简单名）
        simple_name = annotation_name.split('.')[-1]
        if simple_name in self.exclude_annotations:
            return True
        
        for pattern in self.exclude_annotation_patterns:
            if fnmatch.fnmatch(simple_name, pattern):
                return True
        
        return False
    
    @staticmethod
    def from_env() -> 'JavaParserConfig':
        """从环境变量加载配置"""
        # 从环境变量读取排除目录
        exclude_dirs_str = os.getenv('JAVA_PARSER_EXCLUDE_DIRS', '') or os.getenv('PYTHON_AST_EXCLUDE_DIRS', '')
        exclude_dirs = [d.strip() for d in exclude_dirs_str.split(',') if d.strip()] if exclude_dirs_str else None
        
        # 从环境变量读取排除文件模式
        exclude_patterns_str = os.getenv('JAVA_PARSER_EXCLUDE_PATTERNS', '') or os.getenv('PYTHON_AST_EXCLUDE_PATTERNS', '')
        exclude_patterns = [p.strip() for p in exclude_patterns_str.split(',') if p.strip()] if exclude_patterns_str else None
        
        # 从环境变量读取排除注解
        exclude_annotations_str = os.getenv('JAVA_PARSER_EXCLUDE_ANNOTATIONS', '') or os.getenv('PYTHON_AST_EXCLUDE_ANNOTATIONS', '')
        exclude_annotations = [a.strip() for a in exclude_annotations_str.split(',') if a.strip()] if exclude_annotations_str else None
        
        # 从环境变量读取排除注解模式
        exclude_annotation_patterns_str = os.getenv('JAVA_PARSER_EXCLUDE_ANNOTATION_PATTERNS', '') or os.getenv('PYTHON_AST_EXCLUDE_ANNOTATION_PATTERNS', '')
        exclude_annotation_patterns = [p.strip() for p in exclude_annotation_patterns_str.split(',') if p.strip()] if exclude_annotation_patterns_str else None
        
        config = JavaParserConfig(
            enabled=os.getenv('JAVA_PARSER_ENABLED', os.getenv('PYTHON_AST_ENABLED', 'true')).lower() == 'true',
        )
        
        if exclude_dirs:
            config.exclude_dirs.extend(exclude_dirs)
        if exclude_patterns:
            config.exclude_file_patterns.extend(exclude_patterns)
        if exclude_annotations:
            config.exclude_annotations.extend(exclude_annotations)
        if exclude_annotation_patterns:
            config.exclude_annotation_patterns.extend(exclude_annotation_patterns)
        
        return config


# 单例模式
_config_instance: Optional[JavaParserConfig] = None


def get_java_parser_config() -> JavaParserConfig:
    """获取配置实例（单例）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = JavaParserConfig.from_env()
    return _config_instance


# 兼容性函数
def get_python_ast_config() -> JavaParserConfig:
    """获取配置实例（兼容旧名称）"""
    return get_java_parser_config()
