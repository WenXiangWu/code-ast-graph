# 图谱查询噪音过滤功能

## 概述

在查询代码依赖图谱时，经常会遇到大量的"噪音"节点，比如：
- JDK 标准库类（String, List, Map 等）
- 工具类（StringUtils, DateUtils 等）
- DTO/VO 数据传输对象
- Entity 实体类

这些类虽然在依赖关系中存在，但对于理解业务逻辑和架构设计帮助不大。因此，我们实现了灵活的过滤机制，帮助您聚焦于核心业务类。

## 过滤模式

### 1. 不过滤 (none)
显示所有依赖关系，包括工具类和DTO。

**适用场景**：
- 需要查看完整的依赖关系
- 排查技术债务和循环依赖
- 分析第三方库的使用情况

### 2. 宽松模式 (loose)
只过滤 JDK 核心类。

**过滤内容**：
- `java.lang.*`（String, Integer, Object 等）
- `java.util.*`（List, Map, Set 等）
- `java.io.*`
- `java.nio.*`
- 其他 JDK 标准库

**适用场景**：
- 需要保留工具类和DTO
- 关注所有业务代码的依赖关系

### 3. 适中模式 (moderate) - **推荐**
过滤 JDK 和常见工具类。

**过滤内容**：
- JDK 标准库
- 常见工具类库（Apache Commons, Spring Utils, Guava 等）
- 工具类（类名以 Utils, Helper, Constants 结尾）

**保留内容**：
- 所有业务类（Service, Manager, Facade, Controller 等）
- DTO/VO
- Entity

**适用场景**：
- **日常使用推荐**
- 理解业务逻辑流程
- 查看服务调用关系

### 4. 严格模式 (strict)
过滤所有噪音类，只保留核心业务类。

**过滤内容**：
- JDK 标准库
- 工具类库
- 工具类
- DTO/VO（Request, Response, DTO, VO 等）
- Entity（Entity, Model, PO 等）

**保留内容**：
- Service
- Manager
- Facade
- Controller
- Handler
- Processor
- 其他核心业务类

**适用场景**：
- 高层架构分析
- 服务分层设计审查
- 核心业务流程梳理

## 使用示例

### 示例 1：查询 GuardPrivilegeComponent 的依赖关系

**不过滤模式**：
```
项目: official-room-pro-service
起始类: GuardPrivilegeComponent
深度: 3
过滤模式: none

结果: 190 个节点, 200 条边
包含: StringUtils, List, DTO, Service 等所有类
```

**适中模式（推荐）**：
```
项目: official-room-pro-service
起始类: GuardPrivilegeComponent
深度: 3
过滤模式: moderate

结果: ~50 个节点, ~60 条边
包含: GuardPrivilegeComponent, BaseInfoQueryFacade, RelationCountServiceFacade, GuardManager, DTO 等
排除: StringUtils, List, Map 等工具类
```

**严格模式**：
```
项目: official-room-pro-service
起始类: GuardPrivilegeComponent
深度: 3
过滤模式: strict

结果: ~20 个节点, ~25 条边
包含: GuardPrivilegeComponent, BaseInfoQueryFacade, RelationCountServiceFacade, GuardManager 等核心业务类
排除: StringUtils, List, DTO, Entity 等
```

## 自定义过滤规则

如果默认的过滤规则不满足需求，可以修改配置文件：

```python
# config/noise_filter.py

# 添加自定义包前缀
CUSTOM_PACKAGES = [
    'com.mycompany.utils.',
    'com.mycompany.common.',
]

# 添加自定义后缀
CUSTOM_SUFFIXES = [
    'Config',
    'Properties',
]
```

## 技术实现

### 后端实现
1. **配置定义**：`config/noise_filter.py` 定义过滤规则
2. **查询服务**：`src/query/neo4j_querier.py` 的 `get_call_graph` 方法支持 `filter_mode` 参数
3. **API 接口**：`backend/main.py` 的 `/api/projects/{project_name}/graph` 接口接收 `filter_mode` 参数

### 前端实现
1. **UI 组件**：在图谱查询页面添加了过滤模式选择器（Radio Button）
2. **API 调用**：`frontend/src/api/graph.ts` 的 `getProjectGraph` 函数支持 `filterMode` 参数
3. **结果展示**：显示过滤掉的关系数量

## 最佳实践

1. **日常查询**：使用"适中模式"，可以看到主要的业务逻辑流程
2. **架构设计**：使用"严格模式"，聚焦于核心业务类之间的关系
3. **问题排查**：使用"不过滤"或"宽松模式"，查看完整的依赖关系
4. **性能优化**：查询大型项目时，建议先使用"严格模式"，再根据需要放宽

## 注意事项

1. **过滤是在查询结果中应用的**，不影响 Neo4j 数据库中的数据
2. **过滤会影响边的数量**：如果一条边的起点或终点被过滤掉，这条边也会被过滤
3. **深度参数与过滤独立**：深度控制查询范围，过滤控制显示内容
4. **业务关键词保护**：包含 Service、Manager、Facade 等关键词的类不会被过滤

## 未来增强

1. **自定义过滤规则 UI**：在前端添加可视化的规则配置界面
2. **保存过滤配置**：支持保存常用的过滤配置
3. **智能过滤建议**：根据项目特点自动推荐过滤模式
4. **数据导入优化**：在扫描阶段就标记节点类型，提高查询效率
