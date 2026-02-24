# 图谱查询功能更新说明

## 更新内容

本次更新解决了图谱查询中的两个关键问题：

### 1. 修复查询深度bug
**问题**：之前查询深度1层和3层的结果完全一致
**原因**：缺少了执行 Neo4j 查询的代码行
**修复**：在 `src/query/neo4j_querier.py` 中添加了 `results = self.storage.execute_query(query, params)`

### 2. 添加噪音过滤功能
**问题**：图谱中包含太多噪音节点（JDK类、工具类、DTO等），难以聚焦业务逻辑
**解决方案**：实现了灵活的四级过滤机制

## 新功能：噪音过滤

### 过滤模式

| 模式 | 说明 | 过滤内容 | 适用场景 |
|------|------|----------|----------|
| none | 不过滤 | 无 | 完整依赖分析 |
| loose | 宽松 | JDK核心类 | 保留所有业务代码 |
| **moderate** | 适中（推荐） | JDK + 工具类 | 日常业务逻辑分析 |
| strict | 严格 | JDK + 工具类 + DTO/Entity | 核心架构分析 |

### 使用方法

#### 前端界面
在"图谱查询"页面中：
1. 选择项目
2. 输入起始类（可选）
3. 选择查询深度
4. **选择过滤模式**（新增）
5. 点击查询

#### API 调用
```bash
GET /api/projects/{project_name}/graph?start_class=XXX&max_depth=3&filter_mode=moderate
```

参数：
- `filter_mode`: none | loose | moderate | strict（默认：moderate）

### 过滤效果示例

以 `GuardPrivilegeComponent` 为例：

```
不过滤 (none):
- 节点数: 190
- 边数: 200
- 包含: 所有依赖（含 StringUtils, List, DTO 等）

适中模式 (moderate) - 推荐:
- 节点数: ~50
- 边数: ~60
- 包含: BaseInfoQueryFacade, RelationCountServiceFacade, GuardManager, DTO
- 过滤: StringUtils, List, Map 等工具类

严格模式 (strict):
- 节点数: ~20
- 边数: ~25
- 包含: BaseInfoQueryFacade, RelationCountServiceFacade, GuardManager 等核心类
- 过滤: 工具类 + DTO + Entity
```

## 技术实现

### 文件变更

1. **新增文件**
   - `config/noise_filter.py` - 过滤规则配置
   - `docs/NOISE_FILTER_GUIDE.md` - 使用指南

2. **修改文件**
   - `src/query/neo4j_querier.py` - 添加过滤逻辑
   - `backend/main.py` - API 支持 filter_mode 参数
   - `frontend/src/pages/GraphQuery.tsx` - UI 添加过滤模式选择器
   - `frontend/src/api/graph.ts` - API 调用支持 filter_mode

### 核心逻辑

#### 过滤规则定义
```python
# config/noise_filter.py

# JDK 标准库
JDK_PACKAGES = ['java.lang.', 'java.util.', ...]

# 工具类库
COMMON_UTIL_PACKAGES = ['org.apache.commons.', ...]

# DTO 后缀
DTO_SUFFIXES = ['DTO', 'VO', 'Request', 'Response', ...]

# 业务类关键词（保护）
BUSINESS_KEYWORDS = ['Service', 'Manager', 'Facade', ...]
```

#### 过滤函数
```python
def is_noise_class(fqn: str, class_name: str, filter_mode: str) -> bool:
    """判断是否为噪音类"""
    # 1. JDK 类（所有模式过滤）
    # 2. 工具类（moderate、strict 过滤）
    # 3. DTO/Entity（strict 过滤）
    # 4. 业务类（保留）
```

## 配置说明

### 自定义过滤规则

修改 `config/noise_filter.py`：

```python
# 添加自定义包前缀
CUSTOM_UTIL_PACKAGES = [
    'com.yourcompany.utils.',
    'com.yourcompany.common.',
]

# 添加自定义后缀
CUSTOM_SUFFIXES = [
    'Config',
    'Properties',
]
```

### 修改业务类关键词

```python
BUSINESS_KEYWORDS = [
    'Service',
    'Manager',
    'Facade',
    'Controller',
    'Handler',
    'Processor',
    # 添加您的业务类关键词
    'YourCustomKeyword',
]
```

## 启动服务

### 后端
```bash
cd d:\cursor\code-ast-graph
.\venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

### 前端
```bash
cd d:\cursor\code-ast-graph\frontend
npm run dev
```

访问：http://localhost:3000

## 测试验证

1. 打开图谱查询页面
2. 选择项目：`official-room-pro-service`
3. 输入起始类：`GuardPrivilegeComponent`
4. 设置深度：3
5. 尝试不同的过滤模式：
   - none - 查看所有依赖
   - moderate - 查看业务依赖（推荐）
   - strict - 查看核心业务类

观察：
- 节点数和边数的变化
- 过滤掉的关系数量
- 图谱的清晰度提升

## 最佳实践

1. **日常使用**：使用"适中模式"（moderate），可以清晰看到业务逻辑流程
2. **架构分析**：使用"严格模式"（strict），聚焦核心业务类
3. **问题排查**：使用"不过滤"（none）或"宽松模式"（loose），查看完整依赖
4. **大型项目**：建议先使用严格模式，再根据需要放宽

## 未来优化建议

1. **数据导入阶段优化**
   - 在扫描代码时就标记节点类型（Business/Util/DTO/JDK）
   - 在 Neo4j 中存储节点类型标签
   - 在 Cypher 查询中直接过滤，提高性能

2. **UI 增强**
   - 可视化规则配置界面
   - 保存常用过滤配置
   - 过滤规则预览和测试

3. **智能推荐**
   - 根据项目特点自动推荐过滤模式
   - 学习用户的过滤偏好

4. **高级过滤**
   - 支持正则表达式
   - 支持包路径过滤
   - 支持注解过滤（如 @Component, @Service）

## 注意事项

1. 过滤只影响查询结果，不影响 Neo4j 数据库中的数据
2. 过滤会同时过滤节点和边
3. 深度参数和过滤模式是独立的两个维度
4. 包含业务关键词的类永远不会被过滤

## 问题反馈

如果遇到问题或有改进建议，请反馈：
- 哪些类应该被过滤但没有被过滤
- 哪些类不应该被过滤但被过滤了
- 新的过滤规则建议
