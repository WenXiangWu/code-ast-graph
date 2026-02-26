"""
统一的知识图谱数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
from datetime import datetime
from pathlib import Path


class EntityType(Enum):
    """实体类型枚举"""
    PROJECT = "Project"
    REPO = "Repo"  # 新增: git仓库节点
    PACKAGE = "Package"
    MODULE = "Module"
    TYPE = "Type"  # Class, Interface, Enum, etc.
    METHOD = "Method"
    FIELD = "Field"
    VARIABLE = "Variable"
    FUNCTION = "Function"
    PARAMETER = "Parameter"
    ANNOTATION = "Annotation"  # 注解节点
    MQ_TOPIC = "MQTopic"  # MQ主题节点
    TABLE = "Table"  # 数据库表节点
    JOB = "Job"  # 新增: 定时/延时任务节点
    RPC_ENDPOINT = "RpcEndpoint"  # 新增: RPC/HTTP入口节点


class RelationshipType(Enum):
    """关系类型枚举"""
    CONTAINS = "CONTAINS"           # 包含关系
    DEPENDS_ON = "DEPENDS_ON"       # 依赖关系（保留但不再用于调用）
    CALLS = "CALLS"                 # 普通方法调用（Method->Method，Internal/Resource/Autowired）
    IMPLEMENTS = "IMPLEMENTS"       # 实现关系
    EXTENDS = "EXTENDS"             # 继承关系
    IMPORTS = "IMPORTS"             # 导入关系
    ANNOTATED_BY = "ANNOTATED_BY"   # 注解关系
    RETURNS = "RETURNS"             # 返回类型关系
    HAS_PARAMETER = "HAS_PARAMETER" # 参数关系
    DECLARES = "DECLARES"           # 声明关系（类声明方法/字段）
    DUBBO_CALLS = "DUBBO_CALLS"     # Dubbo方法调用（Method->Method，跨项目RPC调用）
    DUBBO_DEPENDS = "DUBBO_DEPENDS"    # Dubbo类依赖（Class->Interface，通过@Reference/@DubboReference注入）
    DUBBO_PROVIDES = "DUBBO_PROVIDES"  # Dubbo服务提供关系（Class->Interface）
    LISTENS_TO_MQ = "LISTENS_TO_MQ"    # MQ监听关系
    SENDS_TO_MQ = "SENDS_TO_MQ"        # MQ发送关系
    MQ_KAFKA_CONSUMER = "MQ_KAFKA_CONSUMER"       # Class -> MQ_TOPIC (Kafka 消费)
    MQ_KAFKA_PRODUCER = "MQ_KAFKA_PRODUCER"       # Method -> MQ_TOPIC (Kafka 发送)
    MQ_ROCKET_CONSUMER = "MQ_ROCKET_CONSUMER"     # Class -> MQ_TOPIC (RocketMQ 消费)
    MQ_ROCKET_PRODUCER = "MQ_ROCKET_PRODUCER"     # Method -> MQ_TOPIC (RocketMQ 发送)
    MQ_CONSUMES_METHOD = "MQ_CONSUMES_METHOD"     # MQ_TOPIC -> Method (Topic 由该方法消费)
    MAPPER_FOR_TABLE = "MAPPER_FOR_TABLE"  # Mapper和表的关系
    ENTITY_FOR_TABLE = "ENTITY_FOR_TABLE"  # 新增: Entity和表的关系
    EXECUTES_JOB = "EXECUTES_JOB"      # 新增: 方法执行任务
    EXPOSES = "EXPOSES"                # 新增: 方法暴露RPC入口


@dataclass
class CodeFile:
    """代码文件表示"""
    path: Path
    content: str
    language: str
    encoding: str = 'utf-8'
    size: int = 0
    modified_time: Optional[datetime] = None


@dataclass
class ProjectInfo:
    """项目信息"""
    name: str
    path: str
    version: Optional[str] = None
    language: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class CodeEntity:
    """代码实体基类"""
    id: str                    # 唯一标识符
    type: EntityType          # 实体类型
    name: str                 # 名称
    qualified_name: str       # 完全限定名
    file_path: str           # 文件路径
    start_line: int          # 起始行号
    end_line: int           # 结束行号
    language: str           # 编程语言
    project: str            # 所属项目
    metadata: Dict = field(default_factory=dict)  # 扩展元数据


@dataclass
class CodeRelationship:
    """代码关系"""
    id: str
    type: RelationshipType
    source_id: str          # 源实体 ID
    target_id: str         # 目标实体 ID
    metadata: Dict = field(default_factory=dict)  # 扩展元数据（如调用次数、参数等）


@dataclass
class ParseResult:
    """解析结果"""
    entities: List[CodeEntity]
    relationships: List[CodeRelationship]
    errors: List[str] = field(default_factory=list)  # 解析错误列表
    metadata: Dict = field(default_factory=dict)  # 解析元数据（如解析时间、文件数等）
