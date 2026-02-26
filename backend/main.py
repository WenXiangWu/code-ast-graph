"""
Code AST Graph - FastAPI 后端服务
提供知识图谱管理的 REST API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import os
import sys
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载 .env 配置文件
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from src.storage.neo4j import Neo4jStorage
from src.parsers.java import JavaParserV2
from src.services.scan_service import ScanService
from src.inputs.filesystem_input import FileSystemCodeInput
from src.query import Neo4jQuerier
from src.queries.mcp_query import MCPQuerier, collect_call_statistics

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Code AST Graph API",
    description="代码知识图谱分析 API",
    version="1.0.0"
)

# 配置 CORS（允许前端跨域）
_frontend_port = os.getenv("FRONTEND_PORT", "3000")
_cors_origins = [
    f"http://localhost:{_frontend_port}",
    f"http://127.0.0.1:{_frontend_port}",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
neo4j_storage = None
querier = None
mcp_querier = None

# 构建任务状态 {task_id: {status, result, error, project_name}}
_scan_tasks: dict = {}

# 后台构建线程池（限制并发，避免资源耗尽）
_scan_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="scan-")


def _ensure_mcp_indexes(storage: Neo4jStorage):
    """确保 MCP 查询索引存在"""
    indexes = [
        ("idx_method_signature", "Method", "signature"),
        ("idx_method_name", "Method", "name"),
        ("idx_class_name", "CLASS", "name"),
        ("idx_class_fqn", "CLASS", "fqn"),
        ("idx_interface_name", "INTERFACE", "name"),
        ("idx_interface_fqn", "INTERFACE", "fqn"),
        ("idx_mapper_name", "MAPPER", "name"),
        ("idx_mapper_fqn", "MAPPER", "fqn"),
        ("idx_project_name", "Project", "name"),
        ("idx_table_name", "Table", "name"),
        ("idx_mq_topic_name", "MQ_TOPIC", "name"),
        ("idx_aries_job_fqn", "ARIES_JOB", "fqn"),
    ]
    
    created_count = 0
    for idx_name, label, prop in indexes:
        try:
            # 检查索引是否已存在
            check_result = storage.execute_query(f"""
                SHOW INDEXES
                YIELD name
                WHERE name = '{idx_name}'
                RETURN count(*) as count
            """)
            
            if check_result and check_result[0]['count'] > 0:
                continue
            
            # 创建索引
            storage.execute_query(f"""
                CREATE INDEX {idx_name} IF NOT EXISTS
                FOR (n:{label})
                ON (n.{prop})
            """)
            created_count += 1
            logger.info(f"✅ 创建索引: {idx_name} ({label}.{prop})")
            
        except Exception as e:
            logger.warning(f"⚠️ 创建索引失败 {idx_name}: {e}")
    
    if created_count > 0:
        logger.info(f"✅ 成功创建 {created_count} 个 MCP 查询索引")
    else:
        logger.info("✅ MCP 查询索引已存在，无需创建")


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global neo4j_storage, querier, mcp_querier
    try:
        neo4j_storage = Neo4jStorage()
        if neo4j_storage.connect():
            logger.info("✅ Neo4j 连接成功")
            
            # 创建 MCP 查询索引（如果不存在）
            _ensure_mcp_indexes(neo4j_storage)
            
            querier = Neo4jQuerier(storage=neo4j_storage)
            mcp_querier = MCPQuerier(storage=neo4j_storage)
        else:
            logger.warning("⚠️ Neo4j 连接失败")
    except Exception as e:
        logger.error(f"⚠️ 初始化失败: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    _scan_executor.shutdown(wait=False)


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "neo4j_connected": neo4j_storage.is_connected() if neo4j_storage else False
    }


@app.get("/api/projects")
async def get_projects():
    """获取 Neo4j 中已构建的项目列表（兼容旧接口）"""
    if not neo4j_storage or not neo4j_storage.is_connected():
        raise HTTPException(status_code=503, detail="Neo4j 未连接")
    
    try:
        result = neo4j_storage.execute_query("""
            MATCH (p:Project)
            RETURN p.name as name, COALESCE(p.path, '') as path,
                   COALESCE(p.scanned_commit_id, '') as scanned_commit_id,
                   p.scanned_at as scanned_at
            ORDER BY p.name ASC
        """)
        
        projects = [
            {
                "name": p.get("name"),
                "path": p.get("path", ""),
                "status": "已构建 ✅",
                "scanned_commit_id": p.get("scanned_commit_id", ""),
                "scanned_at": str(p.get("scanned_at", "")) if p.get("scanned_at") else ""
            }
            for p in result if p.get("name")
        ]
        
        return {"projects": projects}
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/repos")
async def get_repos():
    """
    获取 git-repos 下已克隆的项目列表，并合并 Neo4j 构建信息。
    每个项目包含：当前 commit、commit 时间、构建时的 commit、构建时间。
    """
    try:
        from src.git_tools import GitTool
        git_tool = GitTool()
        loop = asyncio.get_event_loop()
        repos = await loop.run_in_executor(None, git_tool.list_cloned_repos)
        
        # 获取 Neo4j 中已构建项目的 build 信息（按 name 或 path 匹配）
        build_info = {}
        if neo4j_storage and neo4j_storage.is_connected():
            try:
                result = neo4j_storage.execute_query("""
                    MATCH (p:Project)
                    RETURN p.name as name, p.path as path,
                           COALESCE(p.scanned_commit_id, '') as scanned_commit_id,
                           p.scanned_at as scanned_at
                """)
                def _norm(p: str) -> str:
                    return os.path.normpath(p).replace("\\", "/").rstrip("/") if p else ""

                for r in result:
                    name = r.get("name")
                    path = r.get("path", "")
                    info = {
                        "scanned_commit_id": r.get("scanned_commit_id", ""),
                        "scanned_at": str(r.get("scanned_at", "")) if r.get("scanned_at") else ""
                    }
                    if name:
                        build_info[name] = info
                    if path:
                        build_info[_norm(path)] = build_info.get(_norm(path)) or info
            except Exception as e:
                logger.warning(f"查询 Neo4j 构建信息失败: {e}")
        
        # 合并数据
        def _norm_path(p: str) -> str:
            return os.path.normpath(p).replace("\\", "/").rstrip("/") if p else ""

        items = []
        for repo in repos:
            name = repo.get("name", "")
            path = repo.get("path", "")
            current_commit = repo.get("commit_hash", "")
            current_commit_time = repo.get("commit_date", "") or repo.get("commit_date_relative", "")
            
            info = build_info.get(name) or build_info.get(_norm_path(path)) or {}
            scanned_commit = info.get("scanned_commit_id", "")
            scanned_at = info.get("scanned_at", "") if scanned_commit else ""
            
            # 构建按钮可点击：当前 commit 与构建 commit 不一致
            can_build = bool(current_commit and current_commit != scanned_commit)
            
            items.append({
                "name": name,
                "path": path,
                "git_url": repo.get("git_url", ""),
                "branch": repo.get("branch", ""),
                "current_commit_id": current_commit,
                "current_commit_time": current_commit_time,
                "scanned_commit_id": scanned_commit,
                "scanned_at": scanned_at,
                "can_build": can_build,
            })
        
        return {"repos": items}
    except Exception as e:
        logger.error(f"获取仓库列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class CloneRequest(BaseModel):
    git_url: str
    branch: str = "master"


@app.post("/api/repos/clone")
async def clone_repo(request: CloneRequest):
    """克隆 Git 仓库到 git-repos 目录"""
    try:
        from src.git_tools import GitTool
        git_tool = GitTool()
        result = git_tool.clone_repository(
            git_url=request.git_url,
            branch=request.branch or "master"
        )
        if result.get("success"):
            return {"success": True, "message": "克隆成功", "repo_name": result.get("repo_name"), "path": result.get("local_path")}
        return {"success": False, "message": result.get("error", "克隆失败")}
    except Exception as e:
        logger.error(f"克隆失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/repos/{repo_name}")
async def delete_repo(repo_name: str):
    """删除 git-repos 下的本地仓库"""
    try:
        from src.git_tools import GitTool
        git_tool = GitTool()
        result = git_tool.delete_repo(repo_name)
        if result.get("success"):
            return {"success": True, "message": result.get("message", "删除成功")}
        return {"success": False, "message": result.get("error", "删除失败")}
    except Exception as e:
        logger.error(f"删除仓库失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_name}")
async def delete_project_graph(project_name: str):
    """删除 Neo4j 中的项目知识图谱"""
    if not neo4j_storage or not neo4j_storage.is_connected():
        raise HTTPException(status_code=503, detail="Neo4j 未连接")
    try:
        if not neo4j_storage.project_exists(project_name):
            return {"success": False, "message": f"项目 '{project_name}' 不存在"}
        neo4j_storage.delete_project(project_name)
        return {"success": True, "message": f"项目 '{project_name}' 图谱已删除"}
    except Exception as e:
        logger.error(f"删除项目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class ScanRequest(BaseModel):
    project_path: str
    force: bool = False


def _run_scan_task(task_id: str, project_name: str, project_path: str, force: bool):
    """后台执行扫描任务"""
    try:
        _scan_tasks[task_id]["status"] = "running"
        
        # 获取当前 commit ID
        from src.git_tools import GitTool
        git_tool = GitTool()
        commit_id = ""
        try:
            repo_info = git_tool.get_repo_info(project_path)
            if repo_info:
                commit_id = repo_info.get("commit_hash", "")
        except Exception as e:
            logger.warning(f"获取 commit ID 失败: {e}")
        
        # 直接使用 Scanner V2 (不通过 ScanService)
        from src.parsers.java.scanner_v2 import JavaASTScannerV2
        from src.parsers.java.config import get_java_parser_config
        
        config = get_java_parser_config()
        scanner = JavaASTScannerV2(config=config, client=neo4j_storage)
        
        logger.info(f"[Task {task_id}] 开始扫描项目: {project_name} (commit: {commit_id[:8] if commit_id else 'unknown'})")
        result = scanner.scan_project(
            project_name=project_name,
            project_path=project_path,
            force_rescan=force,
            commit_id=commit_id
        )
        
        if result.get('success'):
            _scan_tasks[task_id]["status"] = "completed"
            stats = result.get('stats', {})
            _scan_tasks[task_id]["result"] = {
                "entities_created": stats.get('classes', 0) + stats.get('methods', 0) + stats.get('fields', 0),
                "relationships_created": stats.get('calls', 0),
                "stats": stats,
                "message": result.get('message', '')
            }
            logger.info(f"[Task {task_id}] ✓ 扫描完成: {stats}")
        else:
            _scan_tasks[task_id]["status"] = "failed"
            _scan_tasks[task_id]["error"] = result.get('error', '未知错误')
            logger.error(f"[Task {task_id}] ✗ 扫描失败: {result.get('error')}")
    
    except Exception as e:
        logger.error(f"[Task {task_id}] 扫描任务异常: {e}", exc_info=True)
        _scan_tasks[task_id]["status"] = "failed"
        _scan_tasks[task_id]["error"] = str(e)


@app.post("/api/projects/{project_name}/scan")
async def scan_project(project_name: str, request: ScanRequest):
    """
    扫描项目并构建知识图谱（异步）
    立即返回 202 和 task_id，前端轮询 GET /api/scan/tasks/{task_id} 获取进度
    """
    if not neo4j_storage or not neo4j_storage.is_connected():
        raise HTTPException(status_code=503, detail="Neo4j 未连接")

    if not request.force and neo4j_storage.project_exists(project_name):
        return {
            "success": False,
            "message": f"项目 '{project_name}' 已存在，使用 force=true 强制重建"
        }

    task_id = str(uuid.uuid4())
    _scan_tasks[task_id] = {
        "status": "pending",
        "project_name": project_name,
        "result": None,
        "error": None,
    }

    _scan_executor.submit(
        _run_scan_task,
        task_id,
        project_name,
        request.project_path,
        request.force,
    )

    return JSONResponse(
        status_code=202,
        content={
            "success": True,
            "message": "构建已启动，请稍后查询进度",
            "task_id": task_id,
            "status": "pending",
        },
    )


@app.get("/api/scan/tasks/{task_id}")
async def get_scan_task_status(task_id: str):
    """轮询构建任务状态"""
    if task_id not in _scan_tasks:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    t = _scan_tasks[task_id]
    return {
        "task_id": task_id,
        "status": t["status"],
        "project_name": t.get("project_name"),
        "result": t.get("result"),
        "error": t.get("error"),
    }


@app.get("/api/projects/{project_name}/graph")
async def get_project_graph(
    project_name: str, 
    start_class: str = None, 
    max_depth: int = 3,
    filter_mode: str = 'moderate'
):
    """
    获取项目的调用图
    start_class 可选；filter_mode: none/loose/moderate/strict
    """
    if not querier:
        raise HTTPException(status_code=503, detail="查询器未初始化")
    
    try:
        result = await querier.get_call_graph(
            project=project_name,
            start_class=start_class,
            max_depth=max_depth,
            filter_mode=filter_mode,
        )
        return result
    except Exception as e:
        logger.error(f"获取调用图失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_name}/stats")
async def get_project_stats(project_name: str):
    """获取项目统计信息"""
    if not neo4j_storage or not neo4j_storage.is_connected():
        raise HTTPException(status_code=503, detail="Neo4j 未连接")
    
    try:
        # 查询 Project 节点 (Scanner V2 统一使用 Project)
        stats_query = """
        MATCH (p:Project {name: $project_name})
        OPTIONAL MATCH (p)-[:CONTAINS]->(t:Type)
        OPTIONAL MATCH (t)-[:DECLARES]->(m:Method)
        OPTIONAL MATCH (t)-[:DECLARES]->(f:Field)
        OPTIONAL MATCH (t1:Type)-[c:CALLS]->(t2:Type)
        WHERE (p)-[:CONTAINS]->(t1) AND (p)-[:CONTAINS]->(t2)
        RETURN 
            count(DISTINCT t) as types,
            count(DISTINCT m) as methods,
            count(DISTINCT f) as fields,
            count(DISTINCT c) as total_calls
        """
        
        result = neo4j_storage.execute_query(stats_query, {"project_name": project_name})
        
        if result:
            return {
                "types": result[0].get("types", 0),
                "methods": result[0].get("methods", 0),
                "fields": result[0].get("fields", 0),
                "total_dependencies": result[0].get("total_dependencies", 0)
            }
        else:
            return {"types": 0, "methods": 0, "fields": 0, "total_dependencies": 0}
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class MCPQueryRequest(BaseModel):
    project: str
    class_fqn: str
    method: str
    max_depth: int = 10


@app.get("/api/graph/stats")
async def get_graph_stats(project: str = None):
    """获取知识图谱统计信息
    
    Args:
        project: 可选，项目名称。如果提供，则只统计该项目的节点和关系
    """
    if not neo4j_storage or not neo4j_storage.is_connected():
        raise HTTPException(status_code=503, detail="Neo4j 未连接")
    
    try:
        # 根据是否筛选项目，构建不同的查询
        if project:
            # 筛选特定项目的节点
            node_count_result = neo4j_storage.execute_query("""
                MATCH (p:Project {name: $project})-[:CONTAINS]->(n)
                RETURN count(n) as count
            """, {"project": project})
            total_nodes = node_count_result[0]['count'] if node_count_result else 0
            
            # 筛选特定项目的关系（项目内的节点之间的关系）
            rel_count_result = neo4j_storage.execute_query("""
                MATCH (p:Project {name: $project})-[:CONTAINS]->(n1)
                MATCH (n1)-[r]->(n2)
                WHERE (p)-[:CONTAINS]->(n2) OR NOT exists((:Project)-[:CONTAINS]->(n2))
                RETURN count(r) as count
            """, {"project": project})
            total_relationships = rel_count_result[0]['count'] if rel_count_result else 0
            
            # 节点标签分布（只统计该项目的节点）
            label_result = neo4j_storage.execute_query("""
                MATCH (p:Project {name: $project})-[:CONTAINS]->(n)
                UNWIND labels(n) as label
                WHERE label <> 'Project'
                RETURN label, count(*) as count
                ORDER BY count DESC
            """, {"project": project})
            node_labels = {r['label']: r['count'] for r in label_result}
            
            # 关系类型分布（只统计该项目内的关系）
            rel_type_result = neo4j_storage.execute_query("""
                MATCH (p:Project {name: $project})-[:CONTAINS]->(n1)
                MATCH (n1)-[r]->(n2)
                WHERE (p)-[:CONTAINS]->(n2) OR NOT exists((:Project)-[:CONTAINS]->(n2))
                RETURN type(r) as rel_type, count(r) as count
                ORDER BY count DESC
            """, {"project": project})
            relationship_types = {r['rel_type']: r['count'] for r in rel_type_result}
        else:
            # 全局统计
            node_count_result = neo4j_storage.execute_query("MATCH (n) RETURN count(n) as count")
            total_nodes = node_count_result[0]['count'] if node_count_result else 0
            
            rel_count_result = neo4j_storage.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
            total_relationships = rel_count_result[0]['count'] if rel_count_result else 0
            
            label_result = neo4j_storage.execute_query("""
                MATCH (n)
                UNWIND labels(n) as label
                RETURN label, count(*) as count
                ORDER BY count DESC
            """)
            node_labels = {r['label']: r['count'] for r in label_result}
            
            rel_type_result = neo4j_storage.execute_query("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as count
                ORDER BY count DESC
            """)
            relationship_types = {r['rel_type']: r['count'] for r in rel_type_result}
        
        # 项目列表（始终返回所有项目）
        project_result = neo4j_storage.execute_query("""
            MATCH (p:Project)
            RETURN p.name as name
            ORDER BY name
        """)
        projects = [r['name'] for r in project_result]
        
        return {
            "total_nodes": total_nodes,
            "total_relationships": total_relationships,
            "node_labels": node_labels,
            "relationship_types": relationship_types,
            "projects": projects,
            "selected_project": project
        }
    except Exception as e:
        logger.error(f"获取图谱统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/classes/{project_name}/{class_fqn}/methods")
async def get_class_methods(project_name: str, class_fqn: str):
    """
    获取指定类的所有方法列表
    """
    if not neo4j_storage:
        raise HTTPException(status_code=503, detail="Neo4j 未初始化")
    
    try:
        # 解码 URL 编码的类名
        from urllib.parse import unquote
        class_fqn = unquote(class_fqn)
        
        result = neo4j_storage.execute_query("""
            MATCH (p:Project {name: $project_name})-[:CONTAINS]->(c)
            WHERE c.fqn = $class_fqn
            MATCH (c)-[:DECLARES]->(m:Method)
            RETURN 
                m.name as method_name,
                m.signature as method_signature,
                m.parameters as parameters,
                m.return_type as return_type
            ORDER BY m.name
        """, {
            'project_name': project_name,
            'class_fqn': class_fqn
        })
        
        methods = []
        for r in result:
            methods.append({
                'name': r['method_name'],
                'signature': r['method_signature'],
                'parameters': r['parameters'],
                'return_type': r['return_type']
            })
        
        return {
            'project': project_name,
            'class_fqn': class_fqn,
            'methods': methods
        }
    except Exception as e:
        logger.error(f"获取类方法失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mcp/query")
async def mcp_query(request: MCPQueryRequest):
    """
    MCP 标准化查询接口
    查询完整调用链路，返回结构化结果
    """
    if not mcp_querier:
        raise HTTPException(status_code=503, detail="MCP 查询器未初始化")
    
    if not request.project or not request.class_fqn or not request.method:
        raise HTTPException(status_code=400, detail="project、class_fqn、method 都是必填项")
    
    try:
        result = mcp_querier.query_full_chain(
            project=request.project,
            class_fqn=request.class_fqn,
            method=request.method,
            max_depth=request.max_depth
        )
        return result.to_dict()
    except Exception as e:
        logger.error(f"MCP 查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mcp/query/stats")
async def mcp_query_stats(request: MCPQueryRequest):
    """
    仅返回「调用统计」JSON，不返回完整 call_tree 等。
    入参与 /api/mcp/query 相同；返回 class_stats、tables、mq_list、frontend_entries。
    """
    if not mcp_querier:
        raise HTTPException(status_code=503, detail="MCP 查询器未初始化")
    if not request.project or not request.class_fqn or not request.method:
        raise HTTPException(status_code=400, detail="project、class_fqn、method 都是必填项")
    try:
        result = mcp_querier.query_full_chain(
            project=request.project,
            class_fqn=request.class_fqn,
            method=request.method,
            max_depth=request.max_depth,
        )
        if not result.success:
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "message": result.message,
                    "class_stats": [],
                    "tables": [],
                    "mq_list": [],
                    "frontend_entries": [],
                },
            )
        stats = collect_call_statistics(result)
        return {"success": True, **stats}
    except Exception as e:
        logger.error(f"MCP 调用统计查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
