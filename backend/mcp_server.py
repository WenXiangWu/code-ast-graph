"""
Code AST Graph MCP Server（基于 FastMCP + Streamable HTTP）

提供知识图谱查询工具：
- ast_list_projects        ：列出所有已扫描项目
- ast_query_call_chain     ：查询完整调用链路（含 Dubbo/MQ/DB/前端入口）
- ast_query_call_stats     ：仅返回调用统计摘要（轻量）
- ast_get_call_graph       ：获取项目调用关系图（节点 + 边）

启动方式：
  HTTP Streamable（推荐）：
      python -m backend.mcp_server --port 18086
    访问入口：http://<host>:18086/mcp

  stdio（默认）：
      python -m backend.mcp_server
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# ---------- 路径修复（允许 python -m backend.mcp_server 调用）----------
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from src.storage.neo4j.storage import Neo4jStorage
from src.query.neo4j_querier import Neo4jQuerier
from src.queries.mcp_query import MCPQuerier, collect_call_statistics

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# =========================================================
# 创建 FastMCP 实例
# stateless_http=True：每次 POST 独立无状态，无需 session ID
# enable_dns_rebinding_protection=False：允许任意外部 IP 访问
# =========================================================

mcp = FastMCP(
    "code-ast-graph",
    stateless_http=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# =========================================================
# 全局懒初始化（首次调用工具时连接 Neo4j）
# =========================================================

_storage: Optional[Neo4jStorage] = None
_querier: Optional[Neo4jQuerier] = None
_mcp_querier: Optional[MCPQuerier] = None


def _ensure_connected() -> bool:
    """确保 Neo4j 已连接，返回是否成功"""
    global _storage, _querier, _mcp_querier
    if _storage and _storage.is_connected():
        return True
    try:
        _storage = Neo4jStorage()
        if not _storage.connect():
            logger.error("Neo4j 连接失败")
            return False
        _querier = Neo4jQuerier(storage=_storage)
        _mcp_querier = MCPQuerier(storage=_storage)
        logger.info("✅ Neo4j 连接成功")
        return True
    except Exception as e:
        logger.error("Neo4j 初始化异常: %s", e)
        return False


# =========================================================
# 工具 1：列出已扫描项目
# =========================================================

@mcp.tool()
async def ast_list_projects() -> str:
    """列出 Neo4j 中所有已扫描的项目，返回 JSON 字符串。

    返回格式：
        {"projects": [{"name": "xxx", "path": "...", "scanned_at": "..."}], "total": 3}
    """
    if not _ensure_connected():
        return json.dumps({"projects": [], "total": 0, "error": "Neo4j 未连接"}, ensure_ascii=False)
    try:
        result = _storage.execute_query("""
            MATCH (p:Project)
            RETURN p.name AS name,
                   COALESCE(p.path, '') AS path,
                   COALESCE(p.scanned_commit_id, '') AS scanned_commit_id,
                   toString(p.scanned_at) AS scanned_at
            ORDER BY p.name ASC
        """)
        projects = [
            {
                "name": r.get("name"),
                "path": r.get("path", ""),
                "scanned_commit_id": r.get("scanned_commit_id", ""),
                "scanned_at": r.get("scanned_at") or "",
            }
            for r in result if r.get("name")
        ]
        return json.dumps({"projects": projects, "total": len(projects)}, ensure_ascii=False)
    except Exception as e:
        logger.error("ast_list_projects 失败: %s", e)
        return json.dumps({"projects": [], "total": 0, "error": str(e)}, ensure_ascii=False)


# =========================================================
# 工具 2：查询完整调用链路
# =========================================================

@mcp.tool()
async def ast_query_call_chain(
    project: str,
    class_fqn: str,
    method: str,
    max_depth: int = 10,
) -> str:
    """查询指定方法的完整调用链路，返回 JSON 字符串。

    包含：调用树、Dubbo 跨服务调用、数据库表操作、MQ 消息、前端 HTTP 入口。

    Args:
        project:   项目名称（如 "user-service"）
        class_fqn: 类全限定名（如 "com.example.service.UserService"）
        method:    方法名（如 "createUser"）
        max_depth: 最大追踪深度，默认 10
    """
    if not _ensure_connected():
        return json.dumps({"success": False, "error": "Neo4j 未连接"}, ensure_ascii=False)
    if not project or not class_fqn or not method:
        return json.dumps({"success": False, "error": "project、class_fqn、method 均为必填"}, ensure_ascii=False)
    try:
        result = _mcp_querier.query_full_chain(
            project=project,
            class_fqn=class_fqn,
            method=method,
            max_depth=max_depth,
        )
        return json.dumps(result.to_dict(), ensure_ascii=False, default=str)
    except Exception as e:
        logger.error("ast_query_call_chain 失败: %s", e)
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# =========================================================
# 工具 3：调用统计摘要（轻量版）
# =========================================================

@mcp.tool()
async def ast_query_call_stats(
    project: str,
    class_fqn: str,
    method: str,
    max_depth: int = 10,
) -> str:
    """查询调用统计摘要（不含完整调用树，适合快速分析），返回 JSON 字符串。

    包含：涉及的类列表、数据库表、MQ topic、前端入口路径。

    Args:
        project:   项目名称
        class_fqn: 类全限定名
        method:    方法名
        max_depth: 最大追踪深度，默认 10
    """
    if not _ensure_connected():
        return json.dumps({"success": False, "error": "Neo4j 未连接"}, ensure_ascii=False)
    if not project or not class_fqn or not method:
        return json.dumps({"success": False, "error": "project、class_fqn、method 均为必填"}, ensure_ascii=False)
    try:
        result = _mcp_querier.query_full_chain(
            project=project,
            class_fqn=class_fqn,
            method=method,
            max_depth=max_depth,
        )
        if not result.success:
            return json.dumps({"success": False, "message": result.message,
                               "class_stats": [], "tables": [], "mq_list": [],
                               "frontend_entries": []}, ensure_ascii=False)
        stats = collect_call_statistics(result)
        return json.dumps({"success": True, **stats}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error("ast_query_call_stats 失败: %s", e)
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# =========================================================
# 工具 4：获取调用关系图（节点 + 边）
# =========================================================

@mcp.tool()
async def ast_get_call_graph(
    project: str,
    start_class: str = "",
    max_depth: int = 3,
    filter_mode: str = "moderate",
) -> str:
    """获取项目的调用关系图（节点列表 + 边列表），返回 JSON 字符串。

    Args:
        project:     项目名称
        start_class: 起始类名（可选，空则返回整个项目图）
        max_depth:   最大追踪深度，默认 3
        filter_mode: 节点过滤模式，可选 none / loose / moderate / strict
    """
    if not _ensure_connected():
        return json.dumps({"nodes": [], "edges": [], "error": "Neo4j 未连接"}, ensure_ascii=False)
    if not project:
        return json.dumps({"nodes": [], "edges": [], "error": "project 为必填"}, ensure_ascii=False)
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _querier.get_call_graph_sync(
                project=project,
                start_class=start_class or None,
                max_depth=max_depth,
                filter_mode=filter_mode,
            )
        )
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error("ast_get_call_graph 失败: %s", e)
        return json.dumps({"nodes": [], "edges": [], "error": str(e)}, ensure_ascii=False)


# =========================================================
# 启动入口
# =========================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("code-ast-graph MCP server")
    parser.add_argument("--port", type=int, default=0,
                        help="HTTP 端口（>0 则以 Streamable HTTP 模式启动，0 则用 stdio）")
    args = parser.parse_args()

    if args.port > 0:
        import uvicorn
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request as StarletteRequest

        class DebugLogMiddleware(BaseHTTPMiddleware):
            """打印每条请求的关键信息，方便排查"""
            async def dispatch(self, request: StarletteRequest, call_next):
                body = await request.body()
                logger.info(
                    "[REQ] %s %s | body=%s",
                    request.method, request.url.path,
                    body[:300].decode(errors="replace"),
                )
                response = await call_next(request)
                logger.info("[RESP] status=%s", response.status_code)
                return response

        logger.info("🚀 Code AST Graph MCP Server 启动（HTTP 模式，端口 %s）...", args.port)
        logger.info("📡 MCP 入口：http://0.0.0.0:%s/mcp", args.port)

        # 预连接 Neo4j
        _ensure_connected()

        http_app = mcp.streamable_http_app()
        http_app.add_middleware(DebugLogMiddleware)
        uvicorn.run(http_app, host="0.0.0.0", port=args.port)
    else:
        logger.info("🚀 Code AST Graph MCP Server 启动（stdio 模式）...")
        _ensure_connected()
        mcp.run()
