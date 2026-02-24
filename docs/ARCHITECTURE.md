# Code AST Graph 架构设计文档

> 版本: 1.0.0  
> 最后更新: 2026-02-10  
> 设计原则: 高扩展性、可插拔、分层解耦

## 📋 目录

1. [架构概述](#架构概述)
2. [核心设计原则](#核心设计原则)
3. [分层架构设计](#分层架构设计)
4. [可扩展性设计](#可扩展性设计)
5. [数据模型设计](#数据模型设计)
6. [接口规范](#接口规范)
7. [实现指南](#实现指南)
8. [参考项目](#参考项目)

---

## 架构概述

Code AST Graph 是一个**可扩展的代码知识图谱构建与分析系统**，采用**分层架构**和**插件化设计**，支持多语言代码解析和多种图数据库存储。

### 核心能力

- 🔍 **多语言代码解析**：支持 Java、Python、TypeScript/JavaScript 等
- 🗄️ **多图数据库支持**：Neo4j、Memgraph、ArangoDB 等
- 📊 **统一知识图谱模型**：跨语言的统一代码表示
- 🔌 **可插拔架构**：解析器、存储后端、查询引擎均可插拔
- 🚀 **高性能**：支持增量更新、批量写入、并行处理

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     应用层 (Application Layer)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Web UI     │  │   CLI Tool   │  │   MCP Server │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   服务层 (Service Layer)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Scan Service│  │ Query Service│  │ Index Service│    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   核心层 (Core Layer)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Input Layer │  │ Parser Layer │  │ Storage Layer│    │
│  │              │  │              │  │              │    │
│  │ - Git        │  │ - Java       │  │ - Neo4j     │    │
│  │ - FileSystem │  │ - Python     │  │ - Memgraph  │    │
│  │ - Archive    │  │ - TypeScript │  │ - ArangoDB  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            │                               │
│                   ┌─────────▼─────────┐                    │
│                   │  Knowledge Graph │                    │
│                   │     Model Layer  │                    │
│                   └──────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心设计原则

### 1. 分层解耦 (Layered Decoupling)

每一层只依赖下层，不依赖上层，确保：
- **可测试性**：每层可独立测试
- **可替换性**：实现可替换而不影响其他层
- **可维护性**：清晰的职责边界

### 2. 接口抽象 (Interface Abstraction)

使用抽象接口定义契约，具体实现可插拔：
- **Parser Interface**：统一的解析器接口
- **Storage Interface**：统一的存储接口
- **Query Interface**：统一的查询接口

### 3. 依赖注入 (Dependency Injection)

通过依赖注入实现松耦合：
- 配置驱动的组件选择
- 运行时动态加载插件
- 便于单元测试和模拟

### 4. 单一职责 (Single Responsibility)

每个组件只负责一个明确的功能：
- **Input Layer**：只负责代码输入
- **Parser Layer**：只负责代码解析
- **Storage Layer**：只负责数据存储

### 5. 开放封闭 (Open-Closed Principle)

对扩展开放，对修改封闭：
- 新增语言解析器：实现接口即可
- 新增存储后端：实现接口即可
- 无需修改核心代码

---

## 分层架构设计

### 第一层：代码输入层 (Input Layer)

**职责**：从各种来源获取代码

**设计要点**：
- 统一的输入接口
- 支持多种输入源
- 代码预处理和过滤

#### 接口定义

```python
from abc import ABC, abstractmethod
from typing import Iterator, Optional
from pathlib import Path

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

class CodeFile:
    """代码文件表示"""
    path: Path
    content: str
    language: str
    encoding: str = 'utf-8'
    size: int
    modified_time: datetime
```

#### 实现示例

```python
# Git 输入源
class GitCodeInput(CodeInput):
    """从 Git 仓库获取代码"""
    def __init__(self, repo_path: str, branch: str = 'main'):
        self.repo_path = Path(repo_path)
        self.branch = branch
    
    def get_files(self, pattern: Optional[str] = None) -> Iterator[CodeFile]:
        # 实现 Git 文件遍历逻辑
        pass

# 文件系统输入源
class FileSystemCodeInput(CodeInput):
    """从文件系统获取代码"""
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
    
    def get_files(self, pattern: Optional[str] = None) -> Iterator[CodeFile]:
        # 实现文件系统遍历逻辑
        pass

# 归档文件输入源
class ArchiveCodeInput(CodeInput):
    """从 ZIP/TAR 归档获取代码"""
    def __init__(self, archive_path: str):
        self.archive_path = Path(archive_path)
    
    def get_files(self, pattern: Optional[str] = None) -> Iterator[CodeFile]:
        # 实现归档文件解压和遍历逻辑
        pass
```

---

### 第二层：代码解析层 (Parser Layer)

**职责**：将源代码解析为结构化的知识图谱实体

**设计要点**：
- 语言无关的统一输出格式
- 可插拔的解析器实现
- 支持增量解析和错误恢复

#### 统一知识图谱模型

```python
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from enum import Enum

class EntityType(Enum):
    """实体类型枚举"""
    PROJECT = "Project"
    PACKAGE = "Package"
    MODULE = "Module"
    TYPE = "Type"  # Class, Interface, Enum, etc.
    METHOD = "Method"
    FIELD = "Field"
    VARIABLE = "Variable"
    FUNCTION = "Function"
    PARAMETER = "Parameter"

class RelationshipType(Enum):
    """关系类型枚举"""
    CONTAINS = "CONTAINS"           # 包含关系
    DEPENDS_ON = "DEPENDS_ON"       # 依赖关系
    CALLS = "CALLS"                 # 调用关系
    IMPLEMENTS = "IMPLEMENTS"       # 实现关系
    EXTENDS = "EXTENDS"             # 继承关系
    IMPORTS = "IMPORTS"             # 导入关系
    ANNOTATED_BY = "ANNOTATED_BY"   # 注解关系
    RETURNS = "RETURNS"             # 返回类型关系
    HAS_PARAMETER = "HAS_PARAMETER" # 参数关系

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
    metadata: Dict[str, any] = None  # 扩展元数据

@dataclass
class CodeRelationship:
    """代码关系"""
    id: str
    type: RelationshipType
    source_id: str          # 源实体 ID
    target_id: str         # 目标实体 ID
    metadata: Dict[str, any] = None  # 扩展元数据（如调用次数、参数等）

@dataclass
class ParseResult:
    """解析结果"""
    entities: List[CodeEntity]
    relationships: List[CodeRelationship]
    errors: List[str] = None  # 解析错误列表
    metadata: Dict[str, any] = None  # 解析元数据（如解析时间、文件数等）
```

#### 解析器接口

```python
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
```

#### 解析器实现示例

```python
# Java 解析器（使用 javalang）
class JavaParser(CodeParser):
    """Java 代码解析器"""
    
    def supported_languages(self) -> List[str]:
        return ['java']
    
    def can_parse(self, file: CodeFile) -> bool:
        return file.language == 'java' and file.path.suffix == '.java'
    
    def parse(self, file: CodeFile, project_info: ProjectInfo) -> ParseResult:
        # 使用 javalang 解析 Java 代码
        # 转换为统一的 CodeEntity 和 CodeRelationship
        pass

# Python 解析器（使用 ast）
class PythonParser(CodeParser):
    """Python 代码解析器"""
    
    def supported_languages(self) -> List[str]:
        return ['python']
    
    def can_parse(self, file: CodeFile) -> bool:
        return file.language == 'python' and file.path.suffix == '.py'
    
    def parse(self, file: CodeFile, project_info: ProjectInfo) -> ParseResult:
        # 使用 Python ast 模块解析
        # 转换为统一的 CodeEntity 和 CodeRelationship
        pass

# TypeScript/JavaScript 解析器（使用 Tree-sitter）
class TypeScriptParser(CodeParser):
    """TypeScript/JavaScript 代码解析器"""
    
    def supported_languages(self) -> List[str]:
        return ['typescript', 'javascript']
    
    def can_parse(self, file: CodeFile) -> bool:
        return file.path.suffix in ['.ts', '.tsx', '.js', '.jsx']
    
    def parse(self, file: CodeFile, project_info: ProjectInfo) -> ParseResult:
        # 使用 Tree-sitter 解析
        # 转换为统一的 CodeEntity 和 CodeRelationship
        pass
```

#### 解析器注册与发现

```python
class ParserRegistry:
    """解析器注册表"""
    
    _parsers: Dict[str, CodeParser] = {}
    
    @classmethod
    def register(cls, parser: CodeParser):
        """注册解析器"""
        for lang in parser.supported_languages():
            cls._parsers[lang] = parser
    
    @classmethod
    def get_parser(cls, language: str) -> Optional[CodeParser]:
        """根据语言获取解析器"""
        return cls._parsers.get(language)
    
    @classmethod
    def list_parsers(cls) -> List[str]:
        """列出所有已注册的语言"""
        return list(cls._parsers.keys())
```

---

### 第三层：知识图谱存储层 (Storage Layer)

**职责**：将解析结果持久化到图数据库

**设计要点**：
- 统一的存储接口
- 支持多种图数据库
- 批量写入和事务支持
- 增量更新能力

#### 存储接口

```python
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
    def update_entity(self, entity: CodeEntity) -> bool:
        """更新实体"""
        pass
    
    @abstractmethod
    def delete_project(self, project_name: str) -> bool:
        """删除项目及其所有相关数据"""
        pass
    
    @abstractmethod
    def project_exists(self, project_name: str) -> bool:
        """检查项目是否存在"""
        pass
    
    @abstractmethod
    def get_project_info(self, project_name: str) -> Optional[Dict]:
        """获取项目信息"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, parameters: Dict = None) -> List[Dict]:
        """
        执行查询
        
        Args:
            query: 查询语句（Cypher/Gremlin/等）
            parameters: 查询参数
        
        Returns:
            查询结果列表
        """
        pass
    
    @abstractmethod
    def begin_transaction(self):
        """开始事务"""
        pass
    
    @abstractmethod
    def commit_transaction(self):
        """提交事务"""
        pass
    
    @abstractmethod
    def rollback_transaction(self):
        """回滚事务"""
        pass
```

#### 存储实现示例

```python
# Neo4j 存储实现
class Neo4jStorage(GraphStorage):
    """Neo4j 图数据库存储实现"""
    
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
    
    def connect(self) -> bool:
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"Neo4j 连接失败: {e}")
            return False
    
    def create_entities(self, entities: List[CodeEntity]) -> int:
        """使用 Cypher 批量创建实体"""
        with self.driver.session() as session:
            # 构建批量创建 Cypher 语句
            query = """
            UNWIND $entities AS entity
            CREATE (e:CodeEntity {
                id: entity.id,
                type: entity.type,
                name: entity.name,
                qualified_name: entity.qualified_name,
                file_path: entity.file_path,
                start_line: entity.start_line,
                end_line: entity.end_line,
                language: entity.language,
                project: entity.project
            })
            RETURN count(e) as count
            """
            result = session.run(query, entities=[self._entity_to_dict(e) for e in entities])
            return result.single()['count']
    
    def _entity_to_dict(self, entity: CodeEntity) -> Dict:
        """将实体转换为字典"""
        return {
            'id': entity.id,
            'type': entity.type.value,
            'name': entity.name,
            'qualified_name': entity.qualified_name,
            'file_path': entity.file_path,
            'start_line': entity.start_line,
            'end_line': entity.end_line,
            'language': entity.language,
            'project': entity.project
        }

# Memgraph 存储实现（兼容 Neo4j Cypher）
class MemgraphStorage(Neo4jStorage):
    """Memgraph 图数据库存储实现（兼容 Neo4j 接口）"""
    
    def connect(self) -> bool:
        # Memgraph 使用相同的 Bolt 协议
        return super().connect()

# ArangoDB 存储实现
class ArangoDBStorage(GraphStorage):
    """ArangoDB 图数据库存储实现"""
    
    def __init__(self, url: str, database: str, username: str, password: str):
        self.url = url
        self.database = database
        self.username = username
        self.password = password
        self.client = None
    
    def connect(self) -> bool:
        try:
            from arango import ArangoClient
            self.client = ArangoClient(hosts=self.url)
            self.db = self.client.db(
                self.database,
                username=self.username,
                password=self.password
            )
            return True
        except Exception as e:
            logger.error(f"ArangoDB 连接失败: {e}")
            return False
    
    def create_entities(self, entities: List[CodeEntity]) -> int:
        """使用 AQL 批量创建实体"""
        collection = self.db.collection('entities')
        documents = [self._entity_to_dict(e) for e in entities]
        collection.import_bulk(documents)
        return len(documents)
```

---

### 第四层：查询层 (Query Layer)

**职责**：提供统一的知识图谱查询接口

**设计要点**：
- 高级查询 API
- 查询结果标准化
- 支持复杂图查询

#### 查询接口

```python
class GraphQuerier(ABC):
    """图查询抽象接口"""
    
    @abstractmethod
    def find_entity(self, entity_id: str) -> Optional[CodeEntity]:
        """根据 ID 查找实体"""
        pass
    
    @abstractmethod
    def find_entities_by_name(self, name: str, entity_type: Optional[EntityType] = None) -> List[CodeEntity]:
        """根据名称查找实体"""
        pass
    
    @abstractmethod
    def find_dependencies(self, entity_id: str, max_depth: int = 1) -> List[CodeEntity]:
        """查找依赖关系"""
        pass
    
    @abstractmethod
    def find_callers(self, method_id: str) -> List[CodeEntity]:
        """查找调用者"""
        pass
    
    @abstractmethod
    def find_callees(self, method_id: str) -> List[CodeEntity]:
        """查找被调用者"""
        pass
    
    @abstractmethod
    def get_project_statistics(self, project_name: str) -> Dict:
        """获取项目统计信息"""
        pass
    
    @abstractmethod
    def execute_custom_query(self, query: str, parameters: Dict = None) -> List[Dict]:
        """执行自定义查询"""
        pass
```

---

## 可扩展性设计

### 1. 插件系统

```python
# 插件基类
class Plugin(ABC):
    """插件基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict) -> bool:
        """初始化插件"""
        pass

# 解析器插件
class ParserPlugin(Plugin, CodeParser):
    """解析器插件"""
    pass

# 存储插件
class StoragePlugin(Plugin, GraphStorage):
    """存储插件"""
    pass
```

### 2. 配置驱动

```yaml
# config.yaml
parsers:
  java:
    class: "src.parsers.java.JavaParser"
    enabled: true
    options:
      exclude_test_files: true
  python:
    class: "src.parsers.python.PythonParser"
    enabled: true

storage:
  backend: "neo4j"  # neo4j, memgraph, arangodb
  neo4j:
    uri: "bolt://localhost:7687"
    user: "neo4j"
    password: "password"
  memgraph:
    uri: "bolt://localhost:7687"
```

### 3. 工厂模式

```python
class ParserFactory:
    """解析器工厂"""
    
    @staticmethod
    def create_parser(language: str, config: Dict) -> CodeParser:
        """根据语言和配置创建解析器"""
        parser_class = config['parsers'][language]['class']
        module_path, class_name = parser_class.rsplit('.', 1)
        module = importlib.import_module(module_path)
        parser_class_obj = getattr(module, class_name)
        return parser_class_obj(config['parsers'][language]['options'])

class StorageFactory:
    """存储工厂"""
    
    @staticmethod
    def create_storage(config: Dict) -> GraphStorage:
        """根据配置创建存储后端"""
        backend = config['storage']['backend']
        backend_config = config['storage'][backend]
        
        if backend == 'neo4j':
            return Neo4jStorage(**backend_config)
        elif backend == 'memgraph':
            return MemgraphStorage(**backend_config)
        elif backend == 'arangodb':
            return ArangoDBStorage(**backend_config)
        else:
            raise ValueError(f"不支持的存储后端: {backend}")
```

---

## 数据模型设计

### 实体类型层次

```
Project
  └── Package/Module
        └── Type (Class/Interface/Enum)
              ├── Method/Function
              │     ├── Parameter
              │     └── Variable
              └── Field
```

### 关系类型

- **结构关系**：CONTAINS, HAS_PARAMETER
- **依赖关系**：DEPENDS_ON, IMPORTS
- **调用关系**：CALLS, INVOKES
- **继承关系**：EXTENDS, IMPLEMENTS
- **注解关系**：ANNOTATED_BY

### 图数据库 Schema

#### Neo4j Schema

```cypher
// 节点标签
(:Project)
(:Package)
(:Type)
(:Method)
(:Field)
(:Variable)

// 关系类型
(:Project)-[:CONTAINS]->(:Package)
(:Package)-[:CONTAINS]->(:Type)
(:Type)-[:CONTAINS]->(:Method)
(:Type)-[:CONTAINS]->(:Field)
(:Method)-[:HAS_PARAMETER]->(:Parameter)
(:Type)-[:EXTENDS]->(:Type)
(:Type)-[:IMPLEMENTS]->(:Type)
(:Method)-[:CALLS]->(:Method)
(:Type)-[:DEPENDS_ON]->(:Type)
```

---

## 接口规范

### 扫描服务接口

```python
class ScanService:
    """扫描服务"""
    
    def __init__(
        self,
        input_source: CodeInput,
        parser: CodeParser,
        storage: GraphStorage
    ):
        self.input_source = input_source
        self.parser = parser
        self.storage = storage
    
    def scan_project(
        self,
        project_name: str,
        project_path: str,
        force_rescan: bool = False
    ) -> Dict:
        """
        扫描项目并构建知识图谱
        
        Args:
            project_name: 项目名称
            project_path: 项目路径
            force_rescan: 是否强制全量重新扫描
        
        Returns:
            {
                'success': bool,
                'entities_count': int,
                'relationships_count': int,
                'errors': List[str]
            }
        """
        # 1. 获取项目信息
        project_info = self.input_source.get_project_info()
        
        # 2. 解析代码
        parse_result = self.parser.parse_project(self.input_source, project_info)
        
        # 3. 存储到图数据库
        self.storage.begin_transaction()
        try:
            entities_count = self.storage.create_entities(parse_result.entities)
            relationships_count = self.storage.create_relationships(parse_result.relationships)
            self.storage.commit_transaction()
        except Exception as e:
            self.storage.rollback_transaction()
            raise
        
        return {
            'success': True,
            'entities_count': entities_count,
            'relationships_count': relationships_count,
            'errors': parse_result.errors or []
        }
    
    def update_project(
        self,
        project_name: str,
        project_path: str,
        incremental: bool = True
    ) -> Dict:
        """
        更新项目（支持增量更新）
        
        Args:
            project_name: 项目名称
            project_path: 项目路径
            incremental: 是否使用增量更新（True）或全量扫描（False）
        
        Returns:
            更新结果
        """
        if incremental:
            # 使用增量更新服务
            from .incremental_update import IncrementalUpdateService
            update_service = IncrementalUpdateService(
                change_detector=self._create_change_detector(project_path),
                parser=self.parser,
                storage=self.storage
            )
            return update_service.update_project(project_name, project_path)
        else:
            # 全量扫描
            return self.scan_project(project_name, project_path, force_rescan=True)
    
    def _create_change_detector(self, project_path: str):
        """创建变更检测器"""
        # 优先使用 Git 检测器
        if self._is_git_repo(project_path):
            from .change_detection import GitChangeDetector
            return GitChangeDetector(project_path)
        else:
            from .change_detection import FileHashChangeDetector
            return FileHashChangeDetector(project_path)
    
    def _is_git_repo(self, path: str) -> bool:
        """判断是否为 Git 仓库"""
        return Path(path) / '.git' / 'HEAD' exists()
```

---

## 实现指南

### 添加新语言解析器

1. 实现 `CodeParser` 接口
2. 在 `ParserRegistry` 中注册
3. 在配置文件中添加配置

### 添加新存储后端

1. 实现 `GraphStorage` 接口
2. 在 `StorageFactory` 中添加创建逻辑
3. 在配置文件中添加配置

### 添加新查询功能

1. 在 `GraphQuerier` 接口中添加方法
2. 在各存储实现中实现该方法

---

## 参考项目

### 1. GraphGen4Code
- **特点**：大规模代码知识图谱生成
- **架构**：RDF/JSON 输出，支持多语言
- **参考点**：统一的知识图谱模型设计

### 2. Code-Graph-RAG
- **特点**：基于 Tree-sitter 的多语言解析
- **架构**：Memgraph 存储，Cypher 查询
- **参考点**：可插拔的解析器设计

### 3. Sourcegraph
- **特点**：企业级代码智能平台
- **架构**：分层服务架构，多种索引器
- **参考点**：服务化架构设计

### 4. CodeQL
- **特点**：代码分析查询语言
- **架构**：语言提取器 + 中间表示 + 查询系统
- **参考点**：统一的代码表示模型

---

## 增量更新机制

### 概述

当 Git 项目更新后，系统支持**增量更新**，只处理变更的文件，而不是全量重新扫描。

### 核心组件

1. **变更检测器** (`ChangeDetector`)
   - `GitChangeDetector`：基于 Git Diff 检测变更
   - `FileHashChangeDetector`：基于文件哈希检测变更

2. **增量更新服务** (`IncrementalUpdateService`)
   - 检测文件变更（新增、修改、删除、重命名）
   - 只处理变更的文件
   - 自动清理已删除文件的实体
   - 更新项目版本信息

### 使用方式

```python
# 自动增量更新（推荐）
result = scan_service.update_project(
    project_name='my-project',
    project_path='/path/to/repo',
    incremental=True  # 使用增量更新
)

# 全量扫描
result = scan_service.update_project(
    project_name='my-project',
    project_path='/path/to/repo',
    incremental=False  # 全量扫描
)
```

详细设计请参考：[增量更新机制设计](INCREMENTAL_UPDATE.md)

---

## 配置管理

### 配置层级

系统采用**三层配置架构**：

1. **全局配置** (`config/global.yaml`)：应用级别配置
2. **模块配置** (`config/modules/*.yaml`)：各模块的配置
3. **项目配置** (`.code-ast-graph.yaml`)：项目特定配置

### 配置优先级

```
命令行参数 > 环境变量 > 项目配置 > 模块配置 > 全局配置 > 默认值
```

### 配置来源

- ✅ YAML 配置文件
- ✅ 环境变量
- ✅ 命令行参数
- ✅ 项目级配置文件

详细设计请参考：[配置管理系统设计](CONFIG_MANAGEMENT.md)

---

## 总结

本架构设计遵循以下原则：

1. **分层清晰**：输入 → 解析 → 存储 → 查询
2. **接口抽象**：每层都有明确的接口定义
3. **可插拔**：解析器、存储后端均可替换
4. **可扩展**：易于添加新语言、新存储后端
5. **标准化**：统一的数据模型和接口规范
6. **高效性**：支持增量更新，大幅提升性能
7. **配置清晰**：分层配置管理，优先级明确

通过这个架构，Code AST Graph 可以：
- 支持任意编程语言（只需实现解析器接口）
- 支持任意图数据库（只需实现存储接口）
- 支持增量更新（Git 或文件哈希检测）
- 清晰的配置管理（全局、模块、项目三级配置）
- 保持核心逻辑稳定，扩展功能不影响现有代码
- 便于测试和维护
