# Neo4j 知识图谱查询示例

本文档提供了三种常见场景的 Cypher 查询示例，可以直接在 Neo4j Browser 中执行，也可以通过 Python 代码执行。

## 场景1: 查询接口定义和实现

### 示例1.1: 查找所有接口及其实现的类

```cypher
MATCH (iface:Type)
WHERE iface.kind = 'INTERFACE' OR iface.is_interface = true
OPTIONAL MATCH (impl:Type)-[:IMPLEMENTS]->(iface)
RETURN
  iface.fqn AS InterfaceFQN,
  iface.name AS InterfaceName,
  iface.file_path AS InterfaceFilePath,
  COLLECT(DISTINCT impl.fqn) AS ImplementingClasses,
  SIZE(COLLECT(DISTINCT impl.fqn)) AS ImplementationCount
ORDER BY ImplementationCount DESC, InterfaceFQN
LIMIT 50
```

**说明**: 
- 查找所有接口节点（`kind='INTERFACE'` 或 `is_interface=true`）
- 使用 `OPTIONAL MATCH` 查找实现类（即使没有实现类也会返回接口）
- 按实现数量降序排列

### 示例1.2: 查找特定接口的所有实现

```cypher
MATCH (iface:Type {fqn: 'com.yupaopao.yuer.chatroom.router.gateway.RoomInfoRemoteService'})
MATCH (impl:Type)-[:IMPLEMENTS]->(iface)
RETURN
  iface.fqn AS InterfaceFQN,
  iface.name AS InterfaceName,
  impl.fqn AS ImplementingClassFQN,
  impl.name AS ImplementingClassName,
  impl.file_path AS ImplementingClassFilePath
```

**说明**: 
- 通过接口的 FQN 精确查找
- 返回所有实现该接口的类

### 示例1.3: 查找接口的所有方法定义

```cypher
MATCH (iface:Type)
WHERE iface.kind = 'INTERFACE'
MATCH (iface)-[:DECLARES]->(m:Method)
RETURN
  iface.fqn AS InterfaceFQN,
  iface.name AS InterfaceName,
  m.name AS MethodName,
  m.signature AS MethodSignature,
  m.return_type AS ReturnType,
  m.parameter_count AS ParameterCount
ORDER BY InterfaceFQN, m.name
```

**说明**: 
- 查找接口声明的所有方法
- 返回方法签名、返回类型、参数数量等信息

### 示例1.4: 查找某个类实现的所有接口

```cypher
MATCH (impl:Type {fqn: 'com.yupaopao.yuer.chatroom.router.core.controller.RoomInfoController'})
MATCH (impl)-[:IMPLEMENTS]->(iface:Type)
RETURN
  impl.name AS ClassName,
  impl.fqn AS ClassFQN,
  iface.name AS InterfaceName,
  iface.fqn AS InterfaceFQN
```

**说明**: 
- 查找特定类实现的所有接口
- 用于了解类的接口契约

---

## 场景2: 追踪 Dubbo 调用关系

### 示例2.1: 查找所有 Dubbo 调用方及其调用的 Dubbo 服务

```cypher
MATCH (caller:Type)-[calls:DUBBO_CALLS]->(service:Type)
RETURN
  caller.fqn AS CallerFQN,
  caller.name AS CallerName,
  calls.field_name AS CalledThroughField,
  service.fqn AS ServiceFQN,
  service.name AS ServiceName,
  service.kind AS ServiceKind
ORDER BY CallerFQN, ServiceFQN
```

**说明**: 
- `DUBBO_CALLS` 关系表示类通过 `@DubboReference` 或 `@Reference` 字段调用Dubbo服务
- `field_name` 属性记录调用使用的字段名

### 示例2.2: 查找特定 Dubbo 服务接口的提供者

```cypher
MATCH (service_interface:Type {fqn: 'com.yupaopao.yuer.chatroom.router.gateway.RoomInfoRemoteService'})
MATCH (provider:Type)-[:DUBBO_PROVIDES]->(service_interface)
RETURN
  service_interface.fqn AS ServiceInterfaceFQN,
  service_interface.name AS ServiceInterfaceName,
  provider.fqn AS ServiceProviderFQN,
  provider.name AS ServiceProviderName,
  provider.file_path AS ServiceProviderFilePath
```

**说明**: 
- `DUBBO_PROVIDES` 关系表示类通过 `@DubboService` 或 `@Service` 注解提供Dubbo服务
- 用于查找服务接口的实现类

### 示例2.3: 查找某个类调用的所有 Dubbo 服务

```cypher
MATCH (caller:Type {fqn: 'com.yupaopao.yuer.chatroom.router.core.controller.RoomInfoController'})
MATCH (caller)-[r:DUBBO_CALLS]->(service:Type)
RETURN
  caller.name AS CallerName,
  r.field_name AS FieldName,
  service.name AS ServiceName,
  service.fqn AS ServiceFQN
ORDER BY r.field_name
```

**说明**: 
- 查找特定类通过哪些字段调用了哪些Dubbo服务
- 用于分析类的Dubbo依赖

### 示例2.4: 完整的Dubbo调用链（调用方 -> 服务接口 -> 服务提供者）

```cypher
MATCH (caller:Type)-[calls:DUBBO_CALLS]->(service_iface:Type)
OPTIONAL MATCH (provider:Type)-[:DUBBO_PROVIDES]->(service_iface)
RETURN
  caller.name AS CallerName,
  caller.fqn AS CallerFQN,
  calls.field_name AS FieldName,
  service_iface.name AS ServiceInterfaceName,
  service_iface.fqn AS ServiceInterfaceFQN,
  provider.name AS ProviderName,
  provider.fqn AS ProviderFQN
ORDER BY CallerName, ServiceInterfaceName
LIMIT 50
```

**说明**: 
- 完整的调用链：调用方 -> 服务接口 -> 服务提供者
- 如果服务提供者不存在，`ProviderName` 和 `ProviderFQN` 为 `null`

### 示例2.5: 统计每个类调用的Dubbo服务数量

```cypher
MATCH (caller:Type)-[:DUBBO_CALLS]->(service:Type)
RETURN
  caller.fqn AS CallerFQN,
  caller.name AS CallerName,
  COUNT(DISTINCT service) AS ServiceCount,
  COLLECT(DISTINCT service.name) AS ServiceNames
ORDER BY ServiceCount DESC
LIMIT 20
```

**说明**: 
- 统计每个类调用的Dubbo服务数量
- 按服务数量降序排列

---

## 场景3: 分析模块间的依赖关系

### 示例3.1: 查找模块之间直接的类型依赖关系

```cypher
MATCH (p1:Project)-[:CONTAINS*]->(t1:Type)
MATCH (p2:Project)-[:CONTAINS*]->(t2:Type)
WHERE p1.name <> p2.name
  AND (t1)-[:DEPENDS_ON]->(t2)
RETURN
  p1.name AS DependentModule,
  t1.fqn AS DependentType,
  t1.name AS DependentTypeName,
  p2.name AS DependencyModule,
  t2.fqn AS DependencyType,
  t2.name AS DependencyTypeName
ORDER BY DependentModule, DependencyModule
LIMIT 50
```

**说明**: 
- `[:CONTAINS*]` 表示可变长度路径（Project -> Package -> Type 或 Project -> Type）
- 查找跨模块的类型依赖关系
- `p1.name <> p2.name` 确保是不同模块间的依赖

### 示例3.2: 聚合模块间的依赖数量（模块耦合度分析）

```cypher
MATCH (p1:Project)-[:CONTAINS*]->(t1:Type)-[:DEPENDS_ON]->(t2:Type)<-[:CONTAINS*]-(p2:Project)
WHERE p1.name <> p2.name
  AND p1.name STARTS WITH 'chatroom-router-service'
  AND p2.name STARTS WITH 'chatroom-router-service'
RETURN
  p1.name AS DependentModule,
  p2.name AS DependencyModule,
  COUNT(DISTINCT t1) AS UniqueDependentTypes,
  COUNT(DISTINCT t2) AS UniqueDependencyTypes,
  COUNT(*) AS TotalDependencies
ORDER BY TotalDependencies DESC
```

**说明**: 
- 统计模块间的依赖数量和类型数量
- `UniqueDependentTypes`: 依赖方模块中参与依赖的唯一类型数
- `UniqueDependencyTypes`: 被依赖模块中被依赖的唯一类型数
- `TotalDependencies`: 总依赖关系数

### 示例3.3: 查找某个模块依赖的所有其他模块

```cypher
MATCH (p1:Project {name: 'chatroom-router-service-router-service'})-[:CONTAINS*]->(t1:Type)
MATCH (t1)-[:DEPENDS_ON]->(t2:Type)<-[:CONTAINS*]-(p2:Project)
WHERE p1.name <> p2.name
RETURN
  p2.name AS DependencyModule,
  COUNT(DISTINCT t1) AS DependentTypesCount,
  COUNT(DISTINCT t2) AS DependencyTypesCount,
  COLLECT(DISTINCT t2.fqn)[0..10] AS SampleDependencyTypes
ORDER BY DependencyTypesCount DESC
```

**说明**: 
- 分析特定模块的依赖情况
- 返回依赖的模块、依赖类型数量、示例依赖类型

### 示例3.4: 查找模块间的继承和实现关系

```cypher
MATCH (p1:Project)-[:CONTAINS*]->(t1:Type)
MATCH (p2:Project)-[:CONTAINS*]->(t2:Type)
WHERE p1.name <> p2.name
  AND (
    (t1)-[:EXTENDS]->(t2) OR
    (t1)-[:IMPLEMENTS]->(t2)
  )
RETURN
  p1.name AS ChildModule,
  t1.name AS ChildType,
  t1.fqn AS ChildFQN,
  CASE 
    WHEN EXISTS((t1)-[:EXTENDS]->(t2)) THEN 'EXTENDS'
    WHEN EXISTS((t1)-[:IMPLEMENTS]->(t2)) THEN 'IMPLEMENTS'
  END AS RelationType,
  p2.name AS ParentModule,
  t2.name AS ParentType,
  t2.fqn AS ParentFQN
ORDER BY ChildModule, ParentModule
LIMIT 30
```

**说明**: 
- 查找跨模块的继承和实现关系
- 用于分析模块间的架构依赖

### 示例3.5: 模块依赖关系可视化（用于Neo4j Browser）

```cypher
MATCH (p1:Project)-[:CONTAINS*]->(t1:Type)-[:DEPENDS_ON]->(t2:Type)<-[:CONTAINS*]-(p2:Project)
WHERE p1.name <> p2.name
  AND p1.name STARTS WITH 'chatroom-router-service'
  AND p2.name STARTS WITH 'chatroom-router-service'
WITH p1, p2, COUNT(*) AS depCount
WHERE depCount > 0
RETURN p1, p2, depCount
```

**说明**: 
- 返回模块节点和依赖关系，适合在Neo4j Browser中可视化
- 可以直观看到模块间的依赖图

### 示例3.6: 查找模块间的循环依赖

```cypher
MATCH path = (p1:Project)-[:CONTAINS*]->(t1:Type)-[:DEPENDS_ON*2..10]->(t2:Type)<-[:CONTAINS*]-(p1)
WHERE p1.name STARTS WITH 'chatroom-router-service'
RETURN
  p1.name AS Module,
  [n IN NODES(path) WHERE n:Type | n.fqn] AS DependencyChain,
  LENGTH(path) AS ChainLength
ORDER BY ChainLength
LIMIT 20
```

**说明**: 
- 查找可能的循环依赖
- `[:DEPENDS_ON*2..10]` 表示2到10步的依赖路径

---

## Python 代码示例

### 在Python中执行查询

```python
from main.plugins.python_ast import get_neo4j_client

client = get_neo4j_client()
client.connect()

# 执行查询
query = """
MATCH (iface:Type)
WHERE iface.kind = 'INTERFACE'
OPTIONAL MATCH (impl:Type)-[:IMPLEMENTS]->(iface)
RETURN iface.fqn, COLLECT(impl.fqn) AS implementations
LIMIT 10
"""

results = client.execute_query(query)
for record in results:
    print(f"接口: {record['iface.fqn']}")
    print(f"实现类: {record['implementations']}")
    print()
```

---

## 实用查询技巧

### 1. 查找特定包下的所有类型

```cypher
MATCH (pkg:Package {fqn: 'com.yupaopao.yuer.chatroom.router.gateway'})
MATCH (pkg)-[:CONTAINS]->(t:Type)
RETURN t.fqn, t.name, t.kind
```

### 2. 查找某个类型的所有依赖

```cypher
MATCH (t:Type {fqn: 'com.yupaopao.yuer.chatroom.router.core.controller.RoomInfoController'})
MATCH (t)-[:DEPENDS_ON]->(dep:Type)
RETURN dep.fqn, dep.name
```

### 3. 查找某个类型的所有被依赖

```cypher
MATCH (t:Type {fqn: 'com.yupaopao.yuer.chatroom.router.gateway.RoomInfoRemoteService'})
MATCH (caller:Type)-[:DEPENDS_ON]->(t)
RETURN caller.fqn, caller.name
```

### 4. 统计项目中的节点和关系数量

```cypher
MATCH (p:Project {name: 'chatroom-router-service-router-service'})
OPTIONAL MATCH (p)-[:CONTAINS*]->(t:Type)
OPTIONAL MATCH (t)-[:DECLARES]->(m:Method)
OPTIONAL MATCH (t)-[:DECLARES]->(f:Field)
RETURN 
  p.name AS ProjectName,
  COUNT(DISTINCT t) AS TypeCount,
  COUNT(DISTINCT m) AS MethodCount,
  COUNT(DISTINCT f) AS FieldCount
```

### 5. 查找没有实现的接口

```cypher
MATCH (iface:Type)
WHERE iface.kind = 'INTERFACE'
  AND NOT EXISTS((impl:Type)-[:IMPLEMENTS]->(iface))
RETURN iface.fqn, iface.name
LIMIT 20
```

---

## 注意事项

1. **性能优化**: 
   - 对于大型查询，使用 `LIMIT` 限制结果数量
   - 使用索引：确保 `fqn`、`name` 等常用属性有索引

2. **查询优化**:
   - `[:CONTAINS*]` 可变长度路径可能较慢，如果知道具体路径深度，可以指定具体长度
   - 使用 `WHERE` 子句尽早过滤数据

3. **数据完整性**:
   - 跨项目依赖可能创建占位节点（如果依赖的类不在已扫描的项目中）
   - 接口的实现类可能在其他未扫描的模块中
