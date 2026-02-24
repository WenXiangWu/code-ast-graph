"""
核心接口定义
"""

from abc import ABC, abstractmethod
from typing import Iterator, Optional, List, Dict
from .models import CodeFile, ProjectInfo, ParseResult, CodeEntity, CodeRelationship


class CodeInput(ABC):
    """代码输入抽象接口"""
    
    @abstractmethod
    def get_files(self, pattern: Optional[str] = None) -> Iterator[CodeFile]:
        """
        获取代码文件迭代器
        
        Args:
            pattern: 文件匹配模式（如 '*.java', '*.py'）
        
        Yields:
            CodeFile: 代码文件对象
        """
        pass
    
    @abstractmethod
    def get_project_info(self) -> ProjectInfo:
        """获取项目信息（名称、路径、版本等）"""
        pass


class CodeParser(ABC):
    """代码解析器抽象接口"""
    
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """返回支持的语言列表"""
        pass
    
    @abstractmethod
    def can_parse(self, file: CodeFile) -> bool:
        """判断是否能解析该文件"""
        pass
    
    @abstractmethod
    def parse(self, file: CodeFile, project_info: ProjectInfo) -> ParseResult:
        """
        解析代码文件
        
        Args:
            file: 代码文件
            project_info: 项目信息
        
        Returns:
            ParseResult: 解析结果
        """
        pass
    
    @abstractmethod
    def parse_project(
        self, 
        input_source: CodeInput, 
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
        pass


class GraphStorage(ABC):
    """图数据库存储抽象接口"""
    
    @abstractmethod
    def connect(self) -> bool:
        """连接数据库"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass
    
    @abstractmethod
    def create_entities(self, entities: List[CodeEntity]) -> int:
        """
        批量创建实体
        
        Returns:
            创建的实体数量
        """
        pass
    
    @abstractmethod
    def create_relationships(self, relationships: List[CodeRelationship]) -> int:
        """
        批量创建关系
        
        Returns:
            创建的关系数量
        """
        pass
    
    @abstractmethod
    def project_exists(self, project_name: str) -> bool:
        """检查项目是否存在"""
        pass
    
    @abstractmethod
    def begin_transaction(self):
        """开始事务（如果支持）"""
        pass
    
    @abstractmethod
    def commit_transaction(self):
        """提交事务"""
        pass
    
    @abstractmethod
    def rollback_transaction(self):
        """回滚事务"""
        pass


class GraphQuerier(ABC):
    """图查询抽象接口"""
    
    @abstractmethod
    def find_entity(self, entity_id: str) -> Optional[CodeEntity]:
        """根据 ID 查找实体"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, parameters: Dict = None) -> List[Dict]:
        """执行查询"""
        pass
