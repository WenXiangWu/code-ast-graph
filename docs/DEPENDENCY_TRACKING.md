# 依赖追踪和去重机制

## 概述

为了确保知识图谱的完整性和避免重复索引，系统实现了以下机制：

1. **类级别去重**：基于类的FQN（完全限定名）检查类是否已扫描
2. **接口实现类自动追踪**：自动发现并追踪接口的实现类
3. **跨项目依赖追踪**：支持追踪跨项目的依赖关系
4. **Dubbo服务追踪**：追踪Dubbo服务调用链

## 核心组件

### DependencyTracker

`DependencyTracker` 类负责追踪依赖关系：

- `check_class_scanned(class_fqn)`: 检查类是否已扫描
- `mark_class_scanned(class_fqn)`: 标记类为已扫描
- `find_interface_implementations(interface_fqn, project_paths)`: 查找接口的实现类
- `find_dubbo_references(class_fqn)`: 查找类中的Dubbo引用
- `find_facade_calls(class_fqn)`: 查找类中调用的Facade接口
- `get_dependency_chain(start_class_fqn, max_depth)`: 获取完整的依赖链

### 扫描器增强

`PythonASTScanner` 已集成依赖追踪功能：

1. **类级别去重**：在存储类节点前检查是否已扫描
2. **接口追踪**：解析接口时自动查找实现类
3. **标记机制**：使用 `scanned_at` 属性标记已扫描的类

## 使用示例

### 1. 基本扫描（自动去重）

```python
from main.plugins.python_ast.scanner import PythonASTScanner

scanner = PythonASTScanner()

# 扫描项目（自动去重）
result = scanner.scan_project(
    project_name="my-project",
    project_path="/path/to/project",
    force_rescan=False  # False时跳过已扫描的类
)
```

### 2. 追踪接口实现类

```python
from main.plugins.python_ast.dependency_tracker import DependencyTracker
from main.plugins.python_ast.neo4j_client import get_neo4j_client

client = get_neo4j_client()
tracker = DependencyTracker(client)

# 查找接口的实现类
interface_fqn = "com.example.api.UserService"
implementations = tracker.find_interface_implementations(
    interface_fqn,
    project_paths=["/path/to/project1", "/path/to/project2"]
)

for impl in implementations:
    print(f"实现类: {impl['fqn']}, 文件: {impl['file_path']}")
```

### 3. 获取完整依赖链

```python
# 获取从接口到实现类，再到Facade和Dubbo服务的完整依赖链
chain = tracker.get_dependency_chain(
    start_class_fqn="com.example.api.UserService",
    max_depth=5
)

print(f"起始类: {chain['start_class']}")
print(f"实现类数量: {len(chain['implementations'])}")
print(f"Facade调用数量: {len(chain['facades'])}")
print(f"Dubbo服务数量: {len(chain['dubbo_services'])}")
```

### 4. 查找Dubbo引用

```python
# 查找类中的Dubbo引用
class_fqn = "com.example.controller.UserController"
dubbo_refs = tracker.find_dubbo_references(class_fqn)

for ref in dubbo_refs:
    print(f"字段: {ref['field_name']}, 服务接口: {ref['service_interface']}")
```

## 工作流程

### 扫描流程

1. **项目扫描**
   - 扫描项目中的所有Java文件
   - 解析类、接口、方法、字段等信息

2. **类级别去重**
   - 检查类的FQN是否已存在于Neo4j
   - 检查类是否已标记为已扫描（`scanned_at`属性）
   - 如果已扫描，跳过该类的处理

3. **接口追踪**
   - 当解析到接口时，自动查找其实现类
   - 将未扫描的实现类添加到待扫描列表

4. **存储到Neo4j**
   - 使用 `MERGE` 确保节点不重复
   - 设置 `scanned_at` 属性标记扫描时间
   - 创建类之间的关系（继承、实现、依赖等）

### 依赖链追踪流程

```
接口 (GuardInfoRemoteService)
  ↓
实现类 (GuardInfoRemoteServiceImpl)
  ↓
Facade调用 (UserFacade, OrderFacade)
  ↓
Dubbo服务 (UserService, OrderService)
```

## 数据模型

### Type节点属性

- `fqn`: 类的完全限定名（唯一标识）
- `name`: 类名
- `kind`: 类型（CLASS/INTERFACE）
- `scanned_at`: 扫描时间（用于去重）
- `file_path`: 文件路径

### 关系类型

- `IMPLEMENTS`: 类实现接口
- `EXTENDS`: 类继承父类
- `DEPENDS_ON`: 类依赖其他类
- `CALLS`: 方法调用关系
- `ANNOTATED_BY`: 被注解标记

## 最佳实践

1. **增量扫描**：使用 `force_rescan=False` 进行增量扫描，避免重复处理
2. **跨项目追踪**：提供多个项目路径以支持跨项目依赖追踪
3. **定期清理**：定期清理过时的 `scanned_at` 标记以支持重新扫描
4. **监控待扫描列表**：使用 `get_pending_classes()` 查看待扫描的类

## 注意事项

1. **FQN解析**：确保类的FQN正确解析，这是去重的关键
2. **跨项目依赖**：跨项目依赖需要提供正确的项目路径
3. **性能考虑**：大量类的追踪可能影响性能，建议分批处理
4. **Neo4j连接**：确保Neo4j连接正常，否则去重检查会失败

## 故障排查

### 问题：类被重复扫描

**原因**：
- `scanned_at` 属性未正确设置
- FQN解析不一致

**解决**：
- 检查Neo4j中的 `scanned_at` 属性
- 验证FQN解析逻辑

### 问题：接口实现类未找到

**原因**：
- 实现类不在提供的项目路径中
- 实现类还未被扫描

**解决**：
- 扩大项目路径搜索范围
- 先扫描包含实现类的项目

### 问题：Dubbo引用未识别

**原因**：
- `@DubboReference` 注解未正确解析
- 字段类型信息缺失

**解决**：
- 检查注解解析逻辑
- 验证字段类型提取
