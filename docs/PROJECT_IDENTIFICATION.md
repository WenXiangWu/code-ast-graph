# Neo4j 中项目的区分机制

## 概述

在 Neo4j 知识图谱中，项目通过 **`Project` 节点**进行标识和区分。每个项目都有唯一的标识符和属性，所有与该项目相关的代码实体（包、类、方法等）都通过 `CONTAINS` 关系连接到项目节点。

## 项目节点的结构

### 节点标签
- **`Project`**: 项目节点的标签

### 节点属性

| 属性名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `name` | String | **唯一标识符**，用于区分不同项目 | `"official-room-pro-service"` |
| `path` | String | 项目在文件系统中的路径 | `"D:\cursor\code-index-demo\git-repos\official-room-pro-service"` |
| `scanned_at` | DateTime | 项目扫描时间 | `2026-01-27T19:30:00Z` |
| `scanner` | String | 使用的扫描器类型 | `"python-ast"` |

### 关键点：`name` 属性是唯一标识

**`name` 属性是项目的唯一标识符**，用于：
- 查询特定项目
- 检查项目是否存在
- 区分不同的项目

## 项目节点的创建

在 `scanner.py` 中的 `_create_project_node` 方法：

```python
def _create_project_node(self, project_name: str, project_path: str):
    """创建或更新项目节点"""
    self.client.execute_write("""
        MERGE (p:Project {name: $name})
        SET p.path = $path,
            p.scanned_at = datetime(),
            p.scanner = 'python-ast'
    """, {
        "name": project_name,
        "path": project_path
    })
```

**说明**：
- 使用 `MERGE` 确保项目节点唯一（基于 `name` 属性）
- 如果项目已存在，则更新 `path`、`scanned_at`、`scanner` 属性
- 如果项目不存在，则创建新节点

## 项目与代码实体的关系

所有代码实体都通过 `CONTAINS` 关系连接到项目节点：

```
Project --[:CONTAINS]--> Package --[:CONTAINS]--> Type --[:DECLARES]--> Method
                                                      --[:DECLARES]--> Field
```

### 关系路径示例

```
(official-room-pro-service:Project)
  -[:CONTAINS]->
(com.yupaopao.yuer.official.room:Package)
  -[:CONTAINS]->
(ChatroomInteractionSwitchMapper:Type)
  -[:DECLARES]->
(selectById:Method)
```

## 查询项目

### 1. 查询所有项目

```cypher
MATCH (p:Project)
RETURN p.name AS project_name, 
       p.path AS project_path,
       p.scanned_at AS scanned_at
ORDER BY p.name
```

### 2. 查询特定项目

```cypher
MATCH (p:Project {name: 'official-room-pro-service'})
RETURN p.name, p.path, p.scanned_at
```

### 3. 检查项目是否存在

```cypher
MATCH (p:Project {name: 'official-room-pro-service'})
RETURN count(p) > 0 AS exists
```

### 4. 查询项目包含的所有类型

```cypher
MATCH (p:Project {name: 'official-room-pro-service'})-[:CONTAINS*]->(t:Type)
RETURN count(DISTINCT t) AS type_count
```

### 5. 查询项目包含的所有包

```cypher
MATCH (p:Project {name: 'official-room-pro-service'})-[:CONTAINS]->(pkg:Package)
RETURN pkg.fqn AS package_name
ORDER BY pkg.fqn
```

## 项目区分示例

### 场景1: 多个项目共存

假设 Neo4j 中有以下项目：
- `official-room-pro-service`
- `chatroom-router-service-router-api`
- `chatroom-router-service-router-service`
- `yuer-chatroom-service`

每个项目都有独立的 `Project` 节点，通过 `name` 属性区分。

### 场景2: 查询特定项目的所有代码

```cypher
MATCH (p:Project {name: 'official-room-pro-service'})-[:CONTAINS*]->(entity)
RETURN labels(entity) AS entity_type, 
       count(*) AS count
ORDER BY entity_type
```

### 场景3: 跨项目依赖查询

```cypher
MATCH (p1:Project {name: 'official-room-pro-service'})-[:CONTAINS*]->(t1:Type)
MATCH (p2:Project {name: 'chatroom-router-service-router-api'})-[:CONTAINS*]->(t2:Type)
WHERE (t1)-[:DEPENDS_ON]->(t2)
RETURN t1.fqn AS dependent_type, 
       t2.fqn AS dependency_type
```

## 项目命名规范

### 推荐命名方式

1. **单一项目**: 使用项目名称
   - `official-room-pro-service`
   - `yuer-chatroom-service`

2. **多模块项目**: 使用 `项目名-模块名` 格式
   - `chatroom-router-service-router-api`
   - `chatroom-router-service-router-service`
   - `chatroom-router-service-router-gateway-api`

### 命名注意事项

- **唯一性**: 确保每个项目的 `name` 在 Neo4j 中是唯一的
- **可读性**: 使用有意义的名称，便于识别
- **一致性**: 保持命名规范的一致性

## 项目统计查询

### 查询所有项目的统计信息

```cypher
MATCH (p:Project)
OPTIONAL MATCH (p)-[:CONTAINS*]->(t:Type)
OPTIONAL MATCH (t)-[:DECLARES]->(m:Method)
OPTIONAL MATCH (t)-[:DECLARES]->(f:Field)
RETURN 
  p.name AS project_name,
  p.scanned_at AS scanned_at,
  count(DISTINCT t) AS type_count,
  count(DISTINCT m) AS method_count,
  count(DISTINCT f) AS field_count
ORDER BY p.name
```

### 查询项目的模块结构（适用于多模块项目）

```cypher
MATCH (p:Project)
WHERE p.name STARTS WITH 'chatroom-router-service'
RETURN p.name AS project_name, 
       p.path AS project_path
ORDER BY p.name
```

## 项目管理最佳实践

### 1. 项目扫描前检查

```python
if not force_rescan and client.check_project_exists(project_name):
    logger.info(f"项目 {project_name} 已存在，跳过扫描")
    return {"success": True, "skipped": True}
```

### 2. 强制重新扫描

```python
scanner.scan_project(
    project_name="official-room-pro-service",
    project_path="/path/to/project",
    force_rescan=True  # 强制重新扫描，更新项目信息
)
```

### 3. 项目信息查询

```python
project_info = client.get_project_info(project_name)
if project_info:
    print(f"项目名称: {project_info['name']}")
    print(f"项目路径: {project_info['path']}")
    print(f"扫描时间: {project_info['scanned_at']}")
```

## 总结

Neo4j 中项目的区分机制：

1. **唯一标识**: `Project` 节点的 `name` 属性是唯一标识符
2. **节点结构**: 每个项目有一个 `Project` 节点，包含 `name`、`path`、`scanned_at`、`scanner` 属性
3. **关系连接**: 所有代码实体通过 `CONTAINS` 关系连接到项目节点
4. **查询方式**: 通过 `MATCH (p:Project {name: 'project-name'})` 查询特定项目
5. **隔离性**: 不同项目的代码实体通过项目节点进行隔离，互不干扰

这种设计使得：
- ✅ 多个项目可以共存于同一个 Neo4j 数据库
- ✅ 可以轻松查询特定项目的代码
- ✅ 可以分析跨项目的依赖关系
- ✅ 可以追踪项目的扫描历史
