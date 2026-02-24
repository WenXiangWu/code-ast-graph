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
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载 .env 配置文件
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from src.storage.neo4j import Neo4jStorage
from src.parsers.java import JavaParser
from src.services.scan_service import ScanService
from src.inputs.filesystem_input import FileSystemCodeInput
from src.query import Neo4jQuerier

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


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global neo4j_storage, querier
    try:
        neo4j_storage = Neo4jStorage()
        if neo4j_storage.connect():
            logger.info("✅ Neo4j 连接成功")
            querier = Neo4jQuerier(storage=neo4j_storage)
        else:
            logger.warning("⚠️ Neo4j 连接失败")
    except Exception as e:
        logger.error(f"⚠️ 初始化失败: {e}")


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
        repos = git_tool.list_cloned_repos()
        
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
            scanned_at = info.get("scanned_at", "")
            
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


class ScanRequest(BaseModel):
    project_path: str
    force: bool = False


@app.post("/api/projects/{project_name}/scan")
async def scan_project(
    project_name: str,
    request: ScanRequest
):
    """扫描项目并构建知识图谱"""
    if not neo4j_storage or not neo4j_storage.is_connected():
        raise HTTPException(status_code=503, detail="Neo4j 未连接")
    
    try:
        # 检查项目是否已存在
        if not request.force and neo4j_storage.project_exists(project_name):
            return {
                "success": False,
                "message": f"项目 '{project_name}' 已存在，使用 force=true 强制重建"
            }
        
        # 创建输入源
        input_source = FileSystemCodeInput(request.project_path)
        
        # 创建解析器
        parser = JavaParser()
        
        # 创建扫描服务
        scan_service = ScanService(
            input_source=input_source,
            parser=parser,
            storage=neo4j_storage
        )
        
        # 执行扫描
        result = scan_service.scan_project(project_name)
        
        return {
            "success": True,
            "message": f"项目 '{project_name}' 扫描完成",
            "result": {
                "entities_created": result.get("entities_created", 0) if isinstance(result, dict) else 0,
                "relationships_created": result.get("relationships_created", 0) if isinstance(result, dict) else 0
            }
        }
    except Exception as e:
        logger.error(f"扫描项目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_name}/graph")
async def get_project_graph(
    project_name: str, 
    start_class: str = None, 
    max_depth: int = 3,
    filter_mode: str = 'moderate'
):
    """
    获取项目的调用图
    
    Args:
        project_name: 项目名称
        start_class: 起始类名（可选）
        max_depth: 最大查询深度
        filter_mode: 过滤模式
            - 'none': 不过滤
            - 'loose': 宽松模式，只过滤JDK核心类
            - 'moderate': 适中模式，过滤JDK和工具类（默认）
            - 'strict': 严格模式，过滤所有噪音（包括DTO、Entity）
    """
    if not querier:
        raise HTTPException(status_code=503, detail="查询器未初始化")
    
    try:
        result = await querier.get_call_graph(
            project=project_name,
            start_class=start_class,
            max_depth=max_depth,
            filter_mode=filter_mode
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
        stats_query = """
        MATCH (p:Project {name: $project_name})
        OPTIONAL MATCH (p)-[:CONTAINS]->(t:Type)
        OPTIONAL MATCH (p)-[:CONTAINS]->(m:Method)
        OPTIONAL MATCH (p)-[:CONTAINS]->(f:Field)
        OPTIONAL MATCH (t1:Type)-[d:DEPENDS_ON]->(t2:Type)
        WHERE (t1.project = $project_name OR (p)-[:CONTAINS]->(t1))
          AND ((t2.project = $project_name OR (p)-[:CONTAINS]->(t2)) OR t2.project IS NULL)
        RETURN 
            count(DISTINCT t) as types,
            count(DISTINCT m) as methods,
            count(DISTINCT f) as fields,
            count(DISTINCT d) as total_dependencies
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


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
