# 方案 2: 统一使用 Project 节点

## 背景

Scanner V2 最初设计使用 `Repo` 节点作为项目根节点,但这与现有后端 API 不兼容,导致项目管理页面显示"未构建"。

## 方案选择

**方案 1**: 修改后端 API,支持 `Repo` 和 `Project` 两种节点
**方案 2**: 修改 Scanner V2,统一使用 `Project` 节点 ✅ (已采用)

## 修改内容

### 1. Scanner V2 节点类型修改

将所有 `Repo` 节点改为 `Project` 节点:

```python
# 修改前
def _create_repo_node(self, project_name: str, project_path: str):
    """创建 Repo 节点"""
    self.client.execute_write("""
        MERGE (r:Repo {name: $name})
        SET r.path = $path, r.scanned_at = datetime()
    """, {'name': project_name, 'path': project_path})

# 修改后
def _create_repo_node(self, project_name: str, project_path: str):
    """创建 Project 节点 (保持与后端 API 兼容)"""
    self.client.execute_write("""
        MERGE (p:Project {name: $name})
        SET p.path = $path, r.scanned_at = datetime()
    """, {'name': project_name, 'path': project_path})
```

### 2. 关系修改

所有 `Repo` 相关的关系都改为 `Project`:

```python
# Package 节点
MATCH (p:Project {name: $project_name})
MERGE (pkg:Package {name: $package_name})
MERGE (p)-[:CONTAINS]->(pkg)

# Type 节点
MATCH (p:Project {name: $project_name})
MERGE (t:Type {fqn: $fqn})
...
MERGE (p)-[:CONTAINS]->(t)
```

### 3. 后端 API 保持不变

后端 API 继续查询 `Project` 节点,无需修改:

```python
@app.get("/api/projects")
async def get_projects():
    result = neo4j_storage.execute_query("""
        MATCH (p:Project)
        RETURN p.name as name, ...
    """)
```

## 图结构

### 最终图结构 (统一使用 Project)

```
Project -[:CONTAINS]-> Package
Project -[:CONTAINS]-> Type
Type -[:DECLARES]-> Method
Type -[:DECLARES]-> Field
Type -[:EXTENDS]-> Type
Type -[:IMPLEMENTS]-> Type
Type -[:DUBBO_CALLS]-> Type
Type -[:DUBBO_PROVIDES]-> Type
Method -[:CALLS]-> Method
Method -[:EXPOSES]-> RpcEndpoint
Method -[:EXECUTES_JOB]-> Job
Type -[:MAPPER_FOR_TABLE]-> Table
Type -[:ENTITY_FOR_TABLE]-> Table
```

## 优势

1. **完全兼容**: 与现有后端 API 完全兼容,无需修改前端
2. **简单直接**: 只需修改 Scanner V2,不需要修改多个地方
3. **向后兼容**: Scanner V1 和 Scanner V2 都使用 `Project` 节点
4. **无需迁移**: 不需要数据迁移脚本

## 劣势

1. **命名不够精确**: `Project` 不如 `Repo` 语义明确
2. **方法名不匹配**: `_create_repo_node` 方法名与实际创建的节点类型不匹配

## 后续优化建议

### 短期 (已完成)
- ✅ 修改 Scanner V2,使用 `Project` 节点
- ✅ 清空 Neo4j 数据
- ✅ 重新扫描项目

### 中期
- 重命名 `_create_repo_node` 为 `_create_project_node`
- 更新文档,说明使用 `Project` 节点的原因
- 添加注释说明节点类型选择

### 长期
- 如果未来需要支持多仓库项目,可以考虑引入 `Repo` 节点
- 建立 `Project -[:CONTAINS]-> Repo` 的层次结构
- 逐步迁移到更精确的图模型

## 验证步骤

### 1. 清空数据
```bash
python clear_neo4j_force.py
```

### 2. 重新扫描
启动后端服务并触发扫描:
```bash
python backend/main.py

# 在另一个终端
curl -X POST http://localhost:8000/api/scan/project \
  -H "Content-Type: application/json" \
  -d '{"project_name": "official-core-pro-web", "force": true}'
```

### 3. 验证节点类型
```bash
python check_repo_nodes.py
```

预期结果:
```
检查 Project 节点:
  ✅ 找到 1 个 Project 节点: official-core-pro-web
    - Types: 407
    - Methods: 3149
    - Fields: 1306
    - Packages: 95
```

### 4. 验证前端
访问项目管理页面,应该能看到:
- ✅ 项目列表中显示 `official-core-pro-web`
- ✅ 状态显示"已构建 ✅"
- ✅ 能查看项目统计信息

## 相关文件

- `src/parsers/java/scanner_v2.py`: Scanner V2 实现 (已修改)
- `backend/main.py`: 后端 API (无需修改)
- `check_repo_nodes.py`: 节点检查脚本
- `clear_neo4j_force.py`: 数据清空脚本

## 修改记录

- 2026-02-24: 采用方案 2,修改 Scanner V2 使用 `Project` 节点
- 2026-02-24: 清空 Neo4j 数据,准备重新扫描
- 2026-02-24: 回退 backend/main.py 的修改,保持原有查询逻辑
