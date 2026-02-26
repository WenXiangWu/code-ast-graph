# 从 Scanner V1 迁移到 V2

> 技术方案导向的图模型迁移指南

---

## 一、为什么要迁移

### 1.1 V1 的问题

| 问题 | 影响 |
|------|------|
| **噪音节点多** | Util、DTO、Request 等非业务类占比 70%+ |
| **调用关系泛滥** | 所有方法调用都建 DEPENDS_ON 边,包括 `Objects.isNull()` |
| **无法区分调用类型** | Dubbo 调用和内部调用都是 DEPENDS_ON |
| **查询效率低** | 需要在查询时过滤噪音,性能差 |
| **无入口标识** | 无法快速定位 RPC/HTTP 入口 |
| **无架构视图** | 无法按 Controller/Service/Manager 分层查询 |

### 1.2 V2 的优势

| 优势 | 效果 |
|------|------|
| **节点数减少 70-80%** | 仅保留业务核心类 |
| **调用边精确** | Method→Method, 可追踪到具体方法 |
| **调用类型区分** | DUBBO_CALLS (Type→Type) vs CALLS (Method→Method) |
| **查询效率提升 5-10 倍** | 无需过滤噪音 |
| **快速定位入口** | RpcEndpoint 节点 + EXPOSES 边 |
| **架构分层视图** | arch_layer (Controller/Service/Manager/DAO/Mapper/Entity) |

---

## 二、迁移步骤

### 2.1 准备工作

#### 1. 备份现有图数据

```cypher
// 导出现有数据 (可选)
CALL apoc.export.cypher.all("backup_v1.cypher", {
    format: "cypher-shell"
})
```

#### 2. 清空图数据库 (或使用新数据库)

```cypher
// 方式1: 清空现有数据库
MATCH (n) DETACH DELETE n;

// 方式2: 创建新数据库 (Neo4j Enterprise)
CREATE DATABASE code_ast_v2;
:use code_ast_v2;
```

#### 3. 更新代码

```bash
cd d:\cursor\code-ast-graph
git pull  # 或手动复制新文件
```

### 2.2 代码修改

#### 1. 更新 import

**V1 (旧代码)**:
```python
from src.parsers.java.scanner import JavaASTScanner
```

**V2 (新代码)**:
```python
from src.parsers.java.scanner_v2 import JavaASTScannerV2
```

#### 2. 更新初始化

**V1**:
```python
scanner = JavaASTScanner(config=config, client=client)
```

**V2**:
```python
scanner = JavaASTScannerV2(config=config, client=client)
```

#### 3. 更新调用 (API 不变)

```python
# API 完全兼容,无需修改
result = scanner.scan_project(
    project_name="yuer-chatroom-service",
    project_path="...",
    force_rescan=True
)
```

### 2.3 重新扫描项目

```python
# test_scanner_v2.py
python test_scanner_v2.py --test multiple
```

或手动扫描:

```python
from src.parsers.java.scanner_v2 import JavaASTScannerV2
from src.parsers.java.config import get_java_parser_config
from src.storage.neo4j.storage import Neo4jStorage

config = get_java_parser_config()
client = Neo4jStorage(uri="bolt://localhost:7687", user="neo4j", password="password")
scanner = JavaASTScannerV2(config=config, client=client)

projects = [
    {'name': 'yuer-chatroom-service', 'path': '...'},
    {'name': 'official-room-pro-web', 'path': '...'},
    {'name': 'official-room-pro-service', 'path': '...'}
]

for proj in projects:
    result = scanner.scan_project(proj['name'], proj['path'], force_rescan=True)
    print(f"{proj['name']}: {result['success']}")
```

### 2.4 更新查询

#### V1 查询 (需要修改)

```cypher
// V1: 从类扩散 (含噪音)
MATCH (start:Type {name: 'NobleController'})
MATCH path = (start)-[:DEPENDS_ON*1..5]->(end:Type)
WHERE NOT end.name IN ['Objects', 'StringUtils', 'Response']  // 手动过滤
RETURN path
```

#### V2 查询 (更简洁)

```cypher
// V2: 从方法扩散 (无噪音)
MATCH (start:Type {name: 'NobleController', has_injection: true})
MATCH (start)-[:DECLARES]->(m:Method)
MATCH path = (m)-[:CALLS*0..10]->(end:Method)
RETURN path
```

---

## 三、查询迁移对照表

### 3.1 基础查询

| 查询目标 | V1 | V2 |
|----------|----|----|
| **查找类** | `MATCH (t:Type {name: 'NobleController'})` | `MATCH (t:Type {name: 'NobleController', has_injection: true})` |
| **查找方法** | `MATCH (m:Method {name: 'openNoble'})` | `MATCH (m:Method {signature: '...openNoble(...)'})` |
| **查找入口** | 无 (需要通过注解过滤) | `MATCH (ep:RpcEndpoint {path: '/official/open/noble'})` |

### 3.2 调用链查询

#### 从类扩散

**V1**:
```cypher
MATCH (start:Type {name: 'NobleController'})
MATCH path = (start)-[:DEPENDS_ON*1..5]->(end:Type)
WHERE NOT end.name IN ['Objects', 'StringUtils', 'Response', 'ExceptionCode']
RETURN path
```

**V2**:
```cypher
MATCH (start:Type {name: 'NobleController', has_injection: true})
MATCH (start)-[:DECLARES]->(m:Method)
MATCH path = (m)-[:CALLS*0..10]->(end:Method)
RETURN path
```

#### 从 RPC 入口扩散

**V1**: 无直接支持,需要多步查询

**V2**:
```cypher
MATCH (endpoint:RpcEndpoint {path: '/official/open/noble'})
MATCH (endpoint)<-[:EXPOSES]-(entry:Method)
MATCH path = (entry)-[:CALLS*0..10]->(end:Method)
RETURN path
```

#### Dubbo 调用链

**V1**:
```cypher
MATCH (caller:Type)-[:DUBBO_CALLS]->(service:Type)
RETURN caller, service
```

**V2** (增强):
```cypher
// Type 级别 (含 method_name)
MATCH (caller:Type)-[r:DUBBO_CALLS]->(service:Type)
RETURN caller.name, r.field_name, r.method_name, service.name

// 扩展到 Method 级别
MATCH (caller:Type)-[:DUBBO_CALLS]->(service:Type)
MATCH (impl:Type)-[:DUBBO_PROVIDES]->(service)
MATCH (impl)-[:DECLARES]->(m:Method)
MATCH path = (m)-[:CALLS*0..10]->(end:Method)
RETURN path
```

### 3.3 表关联查询

**V1**:
```cypher
MATCH (mapper:Type)-[:MAPPER_FOR_TABLE]->(table:Table)
RETURN mapper, table
```

**V2** (不变):
```cypher
MATCH (mapper:Type)-[:MAPPER_FOR_TABLE]->(table:Table)
RETURN mapper, table
```

### 3.4 架构分层查询

**V1**: 无直接支持

**V2**:
```cypher
// 按层次分组
MATCH (t:Type)
WHERE t.has_injection = true
RETURN 
  t.arch_layer AS layer,
  COUNT(t) AS count,
  COLLECT(t.name)[0..10] AS examples
ORDER BY count DESC

// 查询某一层的类
MATCH (t:Type {arch_layer: 'Controller'})
RETURN t.name, t.fqn
```

---

## 四、常见迁移问题

### 4.1 查询结果为空

**问题**: 迁移后查询返回空结果

**原因**: V2 过滤了非业务类

**解决**:
1. 确认查询的类是否为业务类 (有注入字段或被注入)
2. 使用 `has_injection = true` 过滤
3. 检查类是否在 V2 中被保留

```cypher
// 检查类是否存在
MATCH (t:Type {name: 'NobleController'})
RETURN t.has_injection, t.arch_layer
```

### 4.2 调用链不完整

**问题**: 调用链比 V1 短

**原因**: V2 仅追踪注入字段发起的调用

**解决**:
- 这是预期行为,V2 过滤了非业务调用 (如 `Objects.isNull()`)
- 如需查看完整调用,可使用 V1 或查看源码

### 4.3 Util 类找不到

**问题**: StringUtils、Objects 等工具类找不到

**原因**: V2 过滤了无注入字段的工具类

**解决**:
- 工具类不是业务核心,不影响技术方案生成
- 如需查看工具类,使用 V1 或直接查看源码

### 4.4 性能问题

**问题**: 扫描速度慢

**原因**: 
- 第一遍扫描提取注入字段
- 第二遍扫描提取调用关系

**解决**:
- 使用增量扫描 (`force_rescan=False`)
- 并行扫描多个项目
- 排除不必要的目录 (如 test、target)

---

## 五、兼容性说明

### 5.1 保留的功能

| 功能 | V1 | V2 | 说明 |
|------|----|----|------|
| **Dubbo 调用** | ✓ | ✓ | V2 增强 (添加 method_name) |
| **Mapper-Table** | ✓ | ✓ | 完全兼容 |
| **MQ 监听/发送** | ✓ | ✓ | 完全兼容 (保留现有逻辑) |
| **继承/实现** | ✓ | ✓ | 完全兼容 |

### 5.2 移除的功能

| 功能 | V1 | V2 | 替代方案 |
|------|----|----|----------|
| **DEPENDS_ON 边** | ✓ | ✗ | 使用 CALLS 或 DUBBO_CALLS |
| **所有类节点** | ✓ | ✗ | 仅保留业务类 |
| **所有字段节点** | ✓ | ✗ | 仅保留注入字段 |

### 5.3 新增的功能

| 功能 | V1 | V2 | 说明 |
|------|----|----|------|
| **RpcEndpoint 节点** | ✗ | ✓ | RPC/HTTP 入口 |
| **Job 节点** | ✗ | ✓ | 定时/延时任务 |
| **arch_layer 属性** | ✗ | ✓ | 架构分层 |
| **has_injection 属性** | ✗ | ✓ | 是否有注入字段 |
| **is_entry 属性** | ✗ | ✓ | 是否为入口方法 |
| **Method-[:CALLS]->Method** | ✗ | ✓ | 方法级调用边 |

---

## 六、回滚方案

如果迁移后遇到问题,可以回滚到 V1:

### 6.1 恢复代码

```python
# 使用 V1
from src.parsers.java.scanner import JavaASTScanner
scanner = JavaASTScanner(config=config, client=client)
```

### 6.2 恢复数据

```cypher
// 从备份恢复 (如果有备份)
CALL apoc.cypher.runFile("backup_v1.cypher")
```

### 6.3 重新扫描

```python
result = scanner.scan_project(
    project_name="yuer-chatroom-service",
    project_path="...",
    force_rescan=True
)
```

---

## 七、最佳实践

### 7.1 渐进式迁移

1. **阶段1**: 在新数据库中测试 V2
2. **阶段2**: 对比 V1 和 V2 的查询结果
3. **阶段3**: 更新所有查询为 V2 格式
4. **阶段4**: 切换到 V2,停用 V1

### 7.2 并行运行

在迁移期间,可以同时运行 V1 和 V2:

```python
# V1 数据库
client_v1 = Neo4jStorage(uri="bolt://localhost:7687", database="code_ast_v1")
scanner_v1 = JavaASTScanner(client=client_v1)

# V2 数据库
client_v2 = Neo4jStorage(uri="bolt://localhost:7687", database="code_ast_v2")
scanner_v2 = JavaASTScannerV2(client=client_v2)

# 对比结果
result_v1 = scanner_v1.scan_project(...)
result_v2 = scanner_v2.scan_project(...)
```

### 7.3 验证数据

```cypher
// 验证 V2 数据完整性

// 1. 检查节点数
MATCH (n) RETURN labels(n)[0] AS label, COUNT(n) AS count ORDER BY count DESC

// 2. 检查边数
MATCH ()-[r]->() RETURN type(r) AS type, COUNT(r) AS count ORDER BY count DESC

// 3. 检查业务类
MATCH (t:Type {has_injection: true}) RETURN COUNT(t)

// 4. 检查 RPC 入口
MATCH (ep:RpcEndpoint) RETURN COUNT(ep)

// 5. 检查调用链
MATCH path = (m:Method)-[:CALLS*1..5]->(end:Method) RETURN COUNT(path)
```

---

## 八、总结

迁移到 Scanner V2 可以获得:

- ✅ **70-80% 节点数减少**: 仅保留业务核心类
- ✅ **5-10 倍查询性能提升**: 无需过滤噪音
- ✅ **精确到方法的调用链**: Method→Method
- ✅ **快速定位 RPC 入口**: RpcEndpoint 节点
- ✅ **架构分层视图**: arch_layer 属性
- ✅ **支持 Job 和 MQ**: 完整的技术方案信息

**迁移成本**:

- ⚠️ 需要重新扫描项目 (一次性)
- ⚠️ 需要更新查询语句 (一次性)
- ⚠️ 工具类不再保留 (预期行为)

**推荐**: 对于技术方案生成场景,强烈推荐迁移到 V2!
