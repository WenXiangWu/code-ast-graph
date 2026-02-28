# ============================================================
# code-ast-graph 后端镜像
# 同时启动 FastAPI（BACKEND_PORT）+ MCP Server（MCP_PORT）
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（git 用于 GitPython 克隆仓库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 层缓存
COPY requirements.txt ./
COPY backend/requirements.txt ./backend/requirements.txt

# 安装 Python 依赖（合并两个 requirements）
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir -r backend/requirements.txt \
 && pip install --no-cache-dir mcp fastmcp uvicorn[standard]

# 复制项目源码
COPY . .

# git-repos 目录通过 volume 挂载，此处只确保目录存在
RUN mkdir -p git-repos

# 暴露后端 API 端口 + MCP Server 端口
EXPOSE 18001 18086

# 启动：python run.py 会同时拉起 MCP server 子进程
CMD ["python", "run.py"]
