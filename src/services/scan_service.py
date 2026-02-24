"""
扫描服务：整合输入、解析、存储
"""

import logging
from typing import Dict, Optional
from pathlib import Path

from ..core.interfaces import CodeInput, CodeParser, GraphStorage
from ..core.models import ProjectInfo

logger = logging.getLogger(__name__)


class ScanService:
    """扫描服务"""
    
    def __init__(
        self,
        input_source: CodeInput,
        parser: CodeParser,
        storage: GraphStorage
    ):
        """
        初始化扫描服务
        
        Args:
            input_source: 代码输入源
            parser: 代码解析器
            storage: 图数据库存储
        """
        self.input_source = input_source
        self.parser = parser
        self.storage = storage
    
    def scan_project(
        self,
        project_name: str,
        project_path: Optional[str] = None,
        force_rescan: bool = False
    ) -> Dict:
        """
        扫描项目并构建知识图谱
        
        Args:
            project_name: 项目名称
            project_path: 项目路径（可选，如果输入源已包含路径信息）
            force_rescan: 是否强制全量重新扫描
        
        Returns:
            {
                'success': bool,
                'entities_count': int,
                'relationships_count': int,
                'errors': List[str],
                'project_info': Dict
            }
        """
        logger.info(f"开始扫描项目: {project_name}")
        
        # 1. 检查项目是否已存在
        if not force_rescan and self.storage.project_exists(project_name):
            logger.info(f"项目 {project_name} 已存在，跳过扫描（使用 force_rescan=True 强制重新扫描）")
            return {
                "success": True,
                "message": "项目已存在",
                "skipped": True,
                "entities_count": 0,
                "relationships_count": 0
            }
        
        # 2. 确保存储连接
        if not self.storage.is_connected():
            if not self.storage.connect():
                return {
                    "success": False,
                    "error": "无法连接到图数据库",
                    "entities_count": 0,
                    "relationships_count": 0
                }
        
        # 3. 获取项目信息及 Git commit（用于记录构建时 commit）
        scanned_commit_id = ''
        try:
            project_info = self.input_source.get_project_info()
            project_info.name = project_name
            if project_path:
                project_info.path = project_path
            
            # 获取 Git commit（如果是 Git 仓库）
            if project_info.path:
                try:
                    from ..git_tools import GitTool
                    git_tool = GitTool()
                    repo_info = git_tool.get_repo_info(project_info.path)
                    if repo_info and repo_info.get('commit_hash'):
                        scanned_commit_id = repo_info['commit_hash']
                        logger.info(f"项目 Git commit: {scanned_commit_id[:8]}")
                except Exception as ge:
                    logger.debug(f"获取 Git 信息失败（可能非 Git 仓库）: {ge}")
        except Exception as e:
            logger.error(f"获取项目信息失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"获取项目信息失败: {e}",
                "entities_count": 0,
                "relationships_count": 0
            }
        
        # 4. 解析代码
        try:
            logger.info(f"开始解析项目: {project_info.name}")
            parse_result = self.parser.parse_project(self.input_source, project_info)
            logger.info(f"解析完成: {len(parse_result.entities)} 个实体, {len(parse_result.relationships)} 个关系")
        except Exception as e:
            logger.error(f"解析项目失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"解析项目失败: {e}",
                "entities_count": 0,
                "relationships_count": 0
            }
        
        # 5. 存储到图数据库
        try:
            logger.info("开始存储到图数据库...")
            
            # 先创建项目节点
            from ..core.models import CodeEntity, EntityType
            project_entity = CodeEntity(
                id=f"Project:{project_info.name}",
                type=EntityType.PROJECT,
                name=project_info.name,
                qualified_name=project_info.name,
                file_path='',
                start_line=0,
                end_line=0,
                language=project_info.language or 'unknown',
                project=project_info.name,
                metadata={
                    'path': project_info.path,
                    'version': project_info.version or '',
                    'scanned_commit_id': scanned_commit_id
                }
            )
            self.storage.create_entities([project_entity])
            
            # 然后创建其他实体和关系
            entities_count = self.storage.create_entities(parse_result.entities)
            relationships_count = self.storage.create_relationships(parse_result.relationships)
            
            logger.info(f"存储完成: {entities_count} 个实体, {relationships_count} 个关系")
        except Exception as e:
            logger.error(f"存储失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"存储失败: {e}",
                "entities_count": 0,
                "relationships_count": 0
            }
        
        return {
            "success": True,
            "message": "扫描成功",
            "entities_count": entities_count,
            "relationships_count": relationships_count,
            "errors": parse_result.errors or [],
            "project_info": {
                "name": project_info.name,
                "path": project_info.path,
                "version": project_info.version
            }
        }
