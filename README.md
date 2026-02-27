# Code AST Graph - 代码知识图谱分析工具

> 基于 Neo4j 的代码架构知识图谱构建与分析系统

## 📖 项目简介

Code AST Graph 是一个独立的代码知识图谱分析工具，专注于代码架构分析、依赖关系追踪和知识图谱可视化。

## ✨ 核心功能

### 1. Java 代码解析
- ✅ **代码扫描**：解析 Java 代码，提取类、方法、依赖关系
- ✅ **依赖追踪**：深度追踪类之间的依赖关系
- ✅ **知识图谱构建**：将代码结构存储到 Neo4j 图数据库

### 2. 知识图谱查询与可视化
- ✅ **REST API**：提供完整的后端 API 服务
- ✅ **现代前端**：基于 React + TypeScript 的 Web UI
- ✅ **图形可视化**：使用 Vis Network 进行知识图谱可视化

### 3. jQAssistant 集成（可选）
- ✅ **Java 架构分析**：基于 jQAssistant 的 Java 代码架构分析
- ✅ **服务调用图谱**：分析类之间的调用关系
- ✅ **数据库表结构**：从 JPA 实体提取表信息
- ✅ **影响面评估**：评估代码变更的影响范围

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+ (用于前端)
- Neo4j 5.0+ (Docker 推荐)

### 安装

```bash
# 克隆仓库
git clone https://github.com/WenXiangWu/code-ast-graph.git
cd code-ast-graph

# 安装后端依赖
pip install -r requirements.txt
pip install -r backend/requirements.txt

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 配置

复制 `.env.example` 为 `.env` 并配置：

```env
# 服务端口（可选，默认 8000/3000）
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Java 解析器配置
JAVA_PARSER_EXCLUDE_DIRS=target,build,.git,node_modules
```

### 启动 Neo4j

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest
```

### 运行

**方式一：一键启动（推荐）**
```bash
# 使用 npm（需先执行 npm install）
npm run dev

# 或使用脚本
# Windows PowerShell:
.\start.ps1

# Linux / Mac / Git Bash:
./start.sh
```

**方式二：分别启动**
```bash
# 终端 1 - 后端
python run.py

# 终端 2 - 前端
cd frontend && npm run dev
```

访问：
- **前端应用**: http://localhost:3000
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

## 📁 项目结构

```
code-ast-graph/
├── backend/              # FastAPI 后端服务
│   ├── main.py          # API 入口
│   └── requirements.txt # 后端依赖
├── frontend/            # React + TypeScript 前端
│   ├── src/
│   │   ├── pages/      # 页面组件
│   │   ├── components/ # UI 组件
│   │   └── api/        # API 客户端
│   └── package.json
├── src/                 # 源代码
│   ├── core/           # 核心层：接口和模型
│   ├── inputs/         # 输入层：代码输入源
│   ├── parsers/        # 解析器层：Java 解析器
│   ├── storage/        # 存储层：Neo4j 存储
│   ├── query/          # 查询层：知识图谱查询
│   └── services/       # 服务层：业务逻辑
├── scripts/            # 工具脚本
├── tests/              # 测试
└── docs/               # 文档
```

## 💻 使用示例

### 使用后端 API

```python
from src.storage.neo4j import Neo4jStorage
from src.parsers.java import JavaParser
from src.services.scan_service import ScanService
from src.inputs.filesystem_input import FileSystemCodeInput

# 创建扫描服务
input_source = FileSystemCodeInput()
parser = JavaParser()
storage = Neo4jStorage()
service = ScanService(input_source, parser, storage)

# 扫描项目
result = service.scan_project(
    project_path="/path/to/project",
    project_name="my-project"
)

print(f"扫描完成: {result.total_files} 个文件")
```

### 查询知识图谱

```python
from src.query import Neo4jQuerier
from src.storage.neo4j import Neo4jStorage

storage = Neo4jStorage()
querier = Neo4jQuerier(storage)

# 查询类的依赖关系
results = querier.find_type_dependencies("UserService")
```

## 📚 文档

- [快速开始指南](docs/QUICK_START.md)
- [架构设计](docs/ARCHITECTURE.md)
- [配置管理](docs/CONFIG_MANAGEMENT.md)
- [MCP 标准化查询接口](docs/MCP接口说明.md)
- [增量更新与扫描说明](docs/INCREMENTAL_UPDATE.md)
- [Neo4j 故障排查](docs/NEO4J_TROUBLESHOOTING.md)
- [前端文档](README_FRONTEND.md)
- [后端文档](README_BACKEND.md)

## 🧠 MCP 标准化查询接口简介

Code AST Graph 提供标准化的 MCP 查询接口，统一封装调用链、表、MQ 等架构信息，默认通过 FastAPI 暴露为 `POST /api/mcp/query`，详细参数与返回结构见 [MCP 标准化查询接口](docs/MCP接口说明.md)。

在技术方案生成场景中，可以直接从前端页面或其他 Agent 调用该接口，获取某个项目中某个类/方法的完整上下游调用关系、涉及表、Dubbo 调用、MQ topic 等信息。

## 🔗 与 code-index-demo 的关系

本项目只负责**代码知识图谱的构建与查询**（Neo4j），**不包含代码向量搜索/语义检索能力**。如果需要根据自然语言需求在代码仓库中做语义搜索，请使用配套项目 `code-index-demo`。

典型的技术方案生成流程是：先由 `code-index-demo` 做语义搜索定位候选类/方法，再调用本项目的 MCP 接口（或图谱查询 API）做全链路分析，两者组合可以产出更完整的“现状分析 + 调用链 + 数据流”信息。

## 🔧 开发

### 运行测试

```bash
# 测试 Neo4j 连接
python scripts/test_neo4j_connection.py

# 测试导入
python scripts/test_imports.py
```

## 📄 License

MIT License

## 🙏 致谢

- [Neo4j](https://neo4j.com/) - 图数据库
- [jQAssistant](https://jqassistant.org/) - Java 架构分析工具
- [React](https://react.dev/) - 前端框架
- [FastAPI](https://fastapi.tiangolo.com/) - 后端框架
