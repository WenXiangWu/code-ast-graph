# Code AST Graph - 快速开始

## 架构说明

项目现在采用前后端分离架构：

- **前端**: React + TypeScript + Vite + Ant Design
- **后端**: FastAPI + Neo4j
- **旧 UI**: Gradio（保留，可逐步迁移）

## 快速启动

### 1. 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端将在 http://localhost:8000 启动
API 文档: http://localhost:8000/docs

### 2. 启动前端服务

```bash
cd frontend
npm install
npm run dev
```

前端将在 http://localhost:3000 启动

### 3. 配置 Neo4j

确保 Neo4j 已启动并配置了连接信息（`.env` 文件或环境变量）：

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
```

## 功能说明

### 新前端功能

1. **项目管理** (`/`)
   - 查看项目列表
   - 扫描项目构建知识图谱
   - 查看项目统计信息

2. **图谱查询** (`/query`)
   - 查询项目的调用关系
   - 设置查询深度和起始类

3. **可视化** (`/visualization`)
   - 图形化展示知识图谱
   - 交互式探索

### 旧 UI（Gradio）

旧 UI 仍然可用，位于 `src/ui/app.py`：

```bash
python -m src.ui.app
```

## 开发说明

### 前端开发

- 使用 TypeScript 确保类型安全
- 使用 TanStack Query 管理数据获取
- 使用 Ant Design 组件库
- 使用 Vis Network 进行图形可视化

### 后端开发

- 使用 FastAPI 构建 RESTful API
- 使用 Pydantic 进行数据验证
- 集成 Neo4j 图数据库
- 支持 CORS 跨域请求

## 下一步

1. 完善可视化功能
2. 添加更多查询功能
3. 优化性能
4. 添加用户认证（如需要）
