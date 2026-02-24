# Code AST Graph - 后端 API

## 技术栈

- **FastAPI** - Web 框架
- **Uvicorn** - ASGI 服务器
- **Neo4j** - 图数据库
- **Pydantic** - 数据验证

## 快速开始

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 启动服务

```bash
python main.py
```

或者使用 uvicorn：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API 文档将在 http://localhost:8000/docs 可用

## API 端点

### 健康检查
- `GET /api/health` - 检查服务状态

### 项目管理
- `GET /api/projects` - 获取所有项目列表
- `POST /api/projects/{project_name}/scan` - 扫描项目
- `GET /api/projects/{project_name}/stats` - 获取项目统计

### 图谱查询
- `GET /api/projects/{project_name}/graph` - 获取调用图

## 环境变量

确保设置了 Neo4j 连接信息（通过 `.env` 文件或环境变量）：
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
