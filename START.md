# 项目启动指南

## 🚀 快速启动

### 1. 准备环境

```bash
# 确保已创建 .env 文件
cp .env.example .env
# 编辑 .env 文件，配置 Neo4j 连接信息
```

### 2. 安装依赖

```bash
# 后端依赖（如果未安装）
pip install -r requirements.txt
pip install -r backend/requirements.txt

# 前端依赖（如果未安装）
cd frontend
npm install
cd ..
```

### 3. 启动 Neo4j（如果未运行）

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

### 4. 启动服务

#### 方式一：使用 run.py（推荐）

```bash
# 启动后端（终端 1）
python run.py
```

```bash
# 启动前端（终端 2）
cd frontend
npm run dev
```

#### 方式二：分别启动

```bash
# 启动后端（终端 1）
cd backend
python main.py
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# 启动前端（终端 2）
cd frontend
npm run dev
```

## 📍 访问地址

- **前端应用**: http://localhost:3000
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474

## ⚠️ 注意事项

1. 确保 Neo4j 服务已启动
2. 确保 `.env` 文件中的 Neo4j 配置正确
3. 后端和前端需要在不同的终端窗口运行
4. 如果端口被占用，请修改相应的配置文件

## 🔧 故障排查

### 后端无法启动
- 检查 Python 依赖是否安装完整
- 检查 `.env` 文件是否存在
- 检查端口 8000 是否被占用

### 前端无法启动
- 检查 Node.js 版本（需要 18+）
- 检查 `node_modules` 是否存在
- 运行 `npm install` 安装依赖

### Neo4j 连接失败
- 检查 Neo4j 服务是否运行
- 检查 `.env` 中的连接信息
- 检查防火墙设置
