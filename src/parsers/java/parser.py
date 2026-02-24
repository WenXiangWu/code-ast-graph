"""
Java Parser
实现 CodeParser 接口，解析 Java 代码（使用 javalang）
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Tuple

try:
    import javalang
except ImportError:
    javalang = None
    logging.warning("javalang module not found. Please install it with: pip install javalang")

from ...core.interfaces import CodeParser
from ...core.models import CodeFile, ProjectInfo, ParseResult
from .config import JavaParserConfig
from .transformer import JavaASTTransformer

logger = logging.getLogger(__name__)


class JavaParser(CodeParser):
    """Java 解析器（使用 javalang）"""
    
    def __init__(self, config: Optional[JavaParserConfig] = None):
        """
        初始化解析器
        
        Args:
            config: Java 解析器配置
        """
        if config is None:
            from .config import get_java_parser_config
            config = get_java_parser_config()
        
        self.config = config
        
        if javalang is None:
            raise ImportError("javalang module is not installed. Please install it with: pip install javalang")
    
    def supported_languages(self) -> List[str]:
        """返回支持的语言列表"""
        return ['java']
    
    def can_parse(self, file: CodeFile) -> bool:
        """判断是否能解析该文件"""
        if file.language != 'java':
            return False
        
        file_path = str(file.path)
        return not self.config.should_exclude_file(file_path)
    
    def parse(self, file: CodeFile, project_info: ProjectInfo) -> ParseResult:
        """
        解析单个代码文件
        
        Args:
            file: 代码文件
            project_info: 项目信息
        
        Returns:
            ParseResult: 解析结果
        """
        if not self.can_parse(file):
            return ParseResult(entities=[], relationships=[], errors=[])
        
        try:
            # 解析文件
            parse_result = self._parse_java_file(Path(file.path), file.content)
            
            # 转换为统一模型
            transformer = JavaASTTransformer(project_info.name, project_info.path)
            return transformer.transform_parse_result(
                classes=parse_result[0],
                methods=parse_result[1],
                fields=parse_result[2],
                calls=parse_result[3],
                imports=parse_result[4],
                packages=[parse_result[5]] if parse_result[5] else [],
                dubbo_references=parse_result[6],
                dubbo_services=parse_result[7],
                mq_listeners=parse_result[8],
                mq_senders=parse_result[9],
                mapper_tables=parse_result[10]
            )
        except Exception as e:
            logger.error(f"解析文件失败 {file.path}: {e}", exc_info=True)
            return ParseResult(
                entities=[],
                relationships=[],
                errors=[f"解析失败: {str(e)}"]
            )
    
    def parse_project(
        self,
        input_source,
        project_info: ProjectInfo
    ) -> ParseResult:
        """
        解析整个项目
        
        Args:
            input_source: 代码输入源
            project_info: 项目信息
        
        Returns:
            ParseResult: 解析结果
        """
        logger.info(f"开始解析项目（Python AST）: {project_info.name}")
        
        # 收集所有文件
        all_classes = []
        all_methods = []
        all_fields = []
        all_calls = []
        all_imports = []
        all_packages = set()
        all_dubbo_references = []
        all_dubbo_services = []
        all_mq_listeners = []
        all_mq_senders = []
        all_mapper_tables = []
        
        project_path = Path(project_info.path)
        java_files = self._find_java_files(project_path)
        logger.info(f"找到 {len(java_files)} 个 Java 文件")
        
        total_files = len(java_files)
        for idx, java_file in enumerate(java_files, 1):
            try:
                if idx % 10 == 0 or idx == total_files:
                    logger.info(f"正在解析文件 [{idx}/{total_files}]: {java_file.name}")
                
                with open(java_file, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
                
                file_result = self._parse_java_file(java_file, source_code)
                (file_classes, file_methods, file_fields, file_calls, file_imports, file_package,
                 file_dubbo_refs, file_dubbo_svcs, file_mq_listeners, file_mq_senders, file_mapper_tables) = file_result
                
                all_classes.extend(file_classes)
                all_methods.extend(file_methods)
                all_fields.extend(file_fields)
                all_calls.extend(file_calls)
                all_imports.extend(file_imports)
                all_dubbo_references.extend(file_dubbo_refs)
                all_dubbo_services.extend(file_dubbo_svcs)
                all_mq_listeners.extend(file_mq_listeners)
                all_mq_senders.extend(file_mq_senders)
                all_mapper_tables.extend(file_mapper_tables)
                
                if file_package:
                    all_packages.add(file_package)
                
                if file_classes or file_methods:
                    logger.debug(f"解析成功 {java_file.name}: {len(file_classes)} 类, {len(file_methods)} 方法")
            except Exception as e:
                logger.warning(f"解析文件失败 {java_file}: {e}", exc_info=True)
                continue
        
        logger.info(f"解析完成: {len(all_classes)} 类, {len(all_methods)} 方法, {len(all_fields)} 字段")
        
        # 转换为统一模型
        transformer = ASTTransformer(project_info.name, project_info.path)
        return transformer.transform_parse_result(
            classes=all_classes,
            methods=all_methods,
            fields=all_fields,
            calls=all_calls,
            imports=all_imports,
            packages=list(all_packages),
            dubbo_references=all_dubbo_references,
            dubbo_services=all_dubbo_services,
            mq_listeners=all_mq_listeners,
            mq_senders=all_mq_senders,
            mapper_tables=all_mapper_tables
        )
    
    def _find_java_files(self, project_dir: Path) -> List[Path]:
        """查找所有 Java 文件（根据配置过滤）"""
        java_files = []
        
        exclude_dirs = set(self.config.exclude_dirs)
        
        for root, dirs, files in os.walk(project_dir):
            # 过滤排除目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = Path(root) / file
                
                if not self.config.should_exclude_file(str(file_path)):
                    java_files.append(file_path)
        
        return java_files
    
    def _parse_java_file(self, java_file: Path, source_code: str) -> Tuple:
        """
        解析单个 Java 文件
        复用 PythonASTScanner 的解析逻辑
        
        Args:
            java_file: Java 文件路径
            source_code: 源代码内容（此参数保留以兼容接口，但 scanner 会重新读取文件）
        
        Returns:
            (classes, methods, fields, calls, imports, package_name,
             dubbo_references, dubbo_services, mq_listeners, mq_senders, mapper_tables)
        """
        # 直接使用 PythonASTScanner 的解析逻辑
        # scanner._parse_java_file 会读取文件，所以直接传入文件路径即可
        # 注意：虽然这里接受了 source_code 参数，但为了保持与生产代码的一致性，
        # 我们仍然使用 scanner 的逻辑，它会重新读取文件
        from .scanner import JavaASTScanner
        scanner = JavaASTScanner(config=self.config, client=None)
        return scanner._parse_java_file(java_file)
    
