"""
Java Parser V2 - 技术方案导向版本
使用 Scanner V2 进行解析
"""

import logging
from pathlib import Path
from typing import List, Optional

from ...core.interfaces import CodeParser
from ...core.models import CodeFile, ProjectInfo, ParseResult, CodeEntity, CodeRelationship
from .config import JavaParserConfig
from .scanner_v2 import JavaASTScannerV2

logger = logging.getLogger(__name__)


class JavaParserV2(CodeParser):
    """Java 解析器 V2 (技术方案导向)"""
    
    def __init__(self, config: Optional[JavaParserConfig] = None, storage=None):
        """
        初始化解析器
        
        Args:
            config: Java 解析器配置
            storage: Neo4j 存储 (Scanner V2 需要)
        """
        if config is None:
            from .config import get_java_parser_config
            config = get_java_parser_config()
        
        self.config = config
        self.storage = storage
        self.scanner = JavaASTScannerV2(config=config, client=storage)
    
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
        
        注意: Scanner V2 是项目级扫描,不支持单文件解析
        此方法返回空结果
        """
        logger.warning("Scanner V2 不支持单文件解析,请使用 parse_project 方法")
        return ParseResult(entities=[], relationships=[], errors=[])
    
    def parse_project(
        self,
        input_source,
        project_info: ProjectInfo
    ) -> ParseResult:
        """
        解析整个项目
        
        Args:
            input_source: 代码输入源 (未使用,Scanner V2 直接扫描目录)
            project_info: 项目信息
        
        Returns:
            ParseResult: 解析结果
        """
        logger.info(f"开始解析项目 (Scanner V2): {project_info.name}")
        
        # 使用 Scanner V2 扫描项目
        result = self.scanner.scan_project(
            project_name=project_info.name,
            project_path=project_info.path,
            force_rescan=True
        )
        
        if not result['success']:
            logger.error(f"扫描失败: {result.get('error')}")
            return ParseResult(
                entities=[],
                relationships=[],
                errors=[result.get('error', '未知错误')]
            )
        
        # Scanner V2 直接写入 Neo4j,这里返回统计信息
        stats = result.get('stats', {})
        logger.info(f"✓ 扫描完成: {stats}")
        
        # 返回空的 ParseResult (因为数据已经写入 Neo4j)
        # 但设置 metadata 包含统计信息
        return ParseResult(
            entities=[],
            relationships=[],
            errors=[],
            metadata={
                'scanner_version': 'v2',
                'stats': stats,
                'direct_write': True,
                'message': 'Scanner V2 已直接写入 Neo4j'
            }
        )
