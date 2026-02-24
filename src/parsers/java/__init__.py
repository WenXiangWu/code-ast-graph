"""
Java 解析器
使用 javalang 解析 Java 代码
"""

from .parser import JavaParser
from .config import JavaParserConfig, get_java_parser_config, get_python_ast_config
from .transformer import JavaASTTransformer
from .scanner import JavaASTScanner

# 注意：不再导出旧名称，请使用新名称
# PythonASTParser = JavaParser  # 已移除，请使用 JavaParser
# PythonASTConfig = JavaParserConfig  # 已移除，请使用 JavaParserConfig
# ASTTransformer = JavaASTTransformer  # 已移除，请使用 JavaASTTransformer
# PythonASTScanner = JavaASTScanner  # 已移除，请使用 JavaASTScanner

__all__ = [
    'JavaParser',
    'JavaParserConfig',
    'JavaASTTransformer',
    'JavaASTScanner',
    'get_java_parser_config',
    # 兼容性导出
    'PythonASTParser',
    'PythonASTConfig',
    'ASTTransformer',
    'PythonASTScanner',
    'get_python_ast_config'
]
