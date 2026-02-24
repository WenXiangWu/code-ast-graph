# 项目扫描和知识图谱维护指南

## 概述

Python AST 插件已经实现了完整的项目扫描功能，可以将整个Java项目的代码结构、关系和依赖存储到Neo4j知识图谱中。

## ✅ 已实现的功能

### 1. 完整的项目扫描

**核心方法**: `PythonASTScanner.scan_project()`

**功能**:
- ✅ 扫描项目目录下的所有Java文件
- ✅ 解析Java源码（使用javalang库）
- ✅ 提取类、接口、方法、字段等结构信息
- ✅ 识别包结构
- ✅ 支持项目去重（避免重复扫描）
- ✅ 支持强制重新扫描

### 2. 知识图谱节点类型

| 节点类型 | 标签 | 主要属性 | 说明 |
|---------|------|---------|------|
| 项目 | `Project` | `name`, `path`, `scanned_at`, `scanner` | 项目根节点 |
| 包 | `Package` | `fqn`, `name` | 包节点 |
| 类型 | `Type` | `fqn`, `name`, `kind`, `visibility`, `is_abstract`, `is_final`, `super_class`, `file_path`, `scanned_at` | 类/接口节点 |
| 方法 | `Method` | `signature`, `name`, `return_type`, `visibility`, `is_static`, `is_abstract`, `parameter_count`, `line_number` | 方法节点 |
| 字段 | `Field` | `signature`, `name`, `type`, `visibility`, `is_static`, `is_final` | 字段节点 |
| 参数 | `Parameter` | `signature`, `name`, `type`, `position` | 方法参数节点 |
| 注解 | `Annotation` | `fqn`, `name` | 注解节点 |
| MQ主题 | `MQTopic` | `name`, `mq_type`, `group_id` | MQ主题/队列节点 |
| 数据表 | `Table` | `name`, `entity_fqn` | 数据库表节点 |

### 3. 知识图谱关系类型

| 关系类型 | 说明 | 方向 | 属性 |
|---------|------|------|------|
| `CONTAINS` | 包含关系 | `Project` → `Package`/`Type`, `Package` → `Type` | - |
| `DECLARES` | 声明关系 | `Type` → `Method`/`Field` | - |
| `HAS_PARAMETER` | 参数关系 | `Method` → `Parameter` | - |
| `EXTENDS` | 继承关系 | `Type` → `Type` | - |
| `IMPLEMENTS` | 实现关系 | `Type` → `Type` | - |
| `DEPENDS_ON` | 依赖关系 | `Type` → `Type` | - |
| `ANNOTATED_BY` | 注解关系 | `Type`/`Method`/`Field` → `Annotation` | - |
| `DUBBO_CALLS` | Dubbo调用 | `Type` → `Type` | `field_name` |
| `DUBBO_PROVIDES` | Dubbo服务提供 | `Type` → `Type` | - |
| `LISTENS_TO_MQ` | MQ监听 | `Method` → `MQTopic` | - |
| `SENDS_TO_MQ` | MQ发送 | `Method` → `MQTopic` | - |
| `MAPPER_FOR_TABLE` | Mapper和表的关系 | `Type` → `Table` | - |

### 4. 特殊关系识别

✅ **Dubbo调用关系**
- 识别 `@DubboReference` 和 `@Reference` 注解
- 识别 `@DubboService` 和 `@Service` 注解

✅ **MQ监听和发送**
- Kafka: `@KafkaListener` 和 `KafkaTemplate.send()`
- RabbitMQ: `@RabbitListener` 和 `RabbitTemplate.send()`
- RocketMQ: `@RocketMQMessageListener` 和 `RocketMQTemplate.send()`

✅ **Mapper和表的关系**
- 识别 `@Mapper` 注解的接口
- 识别接口名以 `Mapper` 结尾的接口
- 从接口名或实体类推断表名

## 使用方法

### 1. 基本使用

```python
from main.plugins.python_ast import PythonASTScanner, get_neo4j_client

# 创建扫描器
scanner = PythonASTScanner()

# 扫描项目
result = scanner.scan_project(
    project_name="my-project",
    project_path="/path/to/project",
    force_rescan=False  # 是否强制重新扫描
)

print(result)
# {
#     "success": True,
#     "message": "Python AST 扫描成功",
#     "method": "python-ast",
#     "stats": {
#         "packages": 10,
#         "classes": 50,
#         "methods": 200,
#         "fields": 150,
#         "calls": 300,
#         "imports": 100
#     }
# }
```

### 2. 配置Neo4j连接

通过环境变量配置：

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password
```

或在代码中配置：

```python
from main.plugins.python_ast import Neo4jClient, PythonASTScanner

# 创建Neo4j客户端
client = Neo4jClient(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="your_password"
)

# 创建扫描器
scanner = PythonASTScanner(client=client)
```

### 3. 查询知识图谱

```python
from main.plugins.python_ast import get_neo4j_client

client = get_neo4j_client()

# 查询项目信息
result = client.execute_query("""
    MATCH (p:Project {name: $project_name})
    OPTIONAL MATCH (p)-[:CONTAINS]->(t:Type)
    RETURN p.name, count(t) as class_count
""", {"project_name": "my-project"})

# 查询Dubbo调用关系
result = client.execute_query("""
    MATCH (caller:Type)-[r:DUBBO_CALLS]->(service:Type)
    RETURN caller.name, r.field_name, service.name
""")

# 查询MQ监听关系
result = client.execute_query("""
    MATCH (m:Method)-[:LISTENS_TO_MQ]->(topic:MQTopic)
    RETURN m.signature, topic.name, topic.mq_type
""")

# 查询Mapper和表的关系
result = client.execute_query("""
    MATCH (mapper:Type)-[:MAPPER_FOR_TABLE]->(table:Table)
    RETURN mapper.fqn, table.name
""")
```

## 知识图谱维护机制

### 1. 去重机制

- **项目级别**: 通过 `check_project_exists()` 检查项目是否已扫描
- **类级别**: 通过 `DependencyTracker.check_class_scanned()` 检查类是否已扫描
- **时间戳**: 使用 `scanned_at` 属性标记扫描时间

### 2. 增量更新

- 如果项目已存在且未设置 `force_rescan=True`，会跳过扫描
- 如果类已扫描，会跳过该类的重复扫描
- 支持强制重新扫描整个项目

### 3. 关系维护

- **继承关系**: 自动创建 `EXTENDS` 关系
- **实现关系**: 自动创建 `IMPLEMENTS` 关系
- **依赖关系**: 基于导入和方法调用创建 `DEPENDS_ON` 关系
- **特殊关系**: 自动识别和创建Dubbo、MQ、Mapper等特殊关系

## 扫描流程

```
1. 检查项目是否已扫描
   ├─ 已扫描且未强制 → 跳过
   └─ 未扫描或强制 → 继续

2. 查找所有Java文件
   ├─ 遍历项目目录
   ├─ 过滤排除目录（target, build, .git等）
   └─ 过滤排除文件（*Test.java等）

3. 解析每个Java文件
   ├─ 解析包名
   ├─ 解析导入
   ├─ 解析类型声明（类/接口）
   │   ├─ 提取类信息
   │   ├─ 提取字段
   │   ├─ 提取方法
   │   └─ 提取方法调用
   └─ 识别特殊关系（Dubbo、MQ、Mapper）

4. 存储到Neo4j
   ├─ 创建项目节点
   ├─ 创建包节点
   ├─ 创建类型节点（去重）
   ├─ 创建方法节点
   ├─ 创建字段节点
   ├─ 创建参数节点
   ├─ 创建关系（继承、实现、依赖等）
   └─ 创建特殊关系（Dubbo、MQ、Mapper）

5. 返回扫描结果
```

## 配置选项

### 排除目录

```python
from main.plugins.python_ast import PythonASTConfig

config = PythonASTConfig(
    exclude_dirs=['target', 'build', '.git', 'node_modules', 'out', 'bin', 'test']
)
```

### 排除文件模式

```python
config = PythonASTConfig(
    exclude_file_patterns=['*Test.java', '*Tests.java', '*Mock.java']
)
```

### 排除注解

```python
config = PythonASTConfig(
    exclude_annotations=['Test', 'Mock'],
    exclude_annotation_patterns=['*.Test', '*.Mock']
)
```

## 性能考虑

1. **批量处理**: 所有数据先收集，然后批量存储到Neo4j
2. **去重优化**: 类级别去重避免重复扫描
3. **连接复用**: Neo4j客户端使用单例模式
4. **错误处理**: 单个文件解析失败不影响整体扫描

## 限制和注意事项

1. **Java语法**: 依赖javalang库，对于复杂或非标准Java语法可能无法解析
2. **表名推断**: 基于命名约定，可能不完全准确
3. **MQ Topic提取**: 主要基于正则匹配，复杂表达式可能无法识别
4. **跨项目依赖**: 如果依赖的类不在当前项目中，会创建占位节点

## 总结

✅ **当前实现已经可以**:
- 完整扫描Java项目
- 提取代码结构和关系
- 识别Dubbo、MQ、Mapper等特殊关系
- 存储到Neo4j知识图谱
- 维护知识图谱的完整性和一致性

✅ **知识图谱包含**:
- 项目、包、类、方法、字段的层次结构
- 继承、实现、依赖关系
- Dubbo调用和服务提供关系
- MQ监听和发送关系
- Mapper和数据库表的映射关系

✅ **可以用于**:
- 代码依赖分析
- 接口调用链追踪
- 技术方案生成
- 代码影响范围分析
- 架构可视化
