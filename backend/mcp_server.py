"""
Code-AST-Graph MCP Server

提供代码知识图谱查询与源码检索工具：

图谱查询：
- ast_list_projects     ：列出已扫描项目
- ast_query_call_chain  ：查询完整调用链路（含 Dubbo/MQ/DB）
- ast_query_call_stats  ：查询调用统计摘要
- ast_get_call_graph    ：获取调用关系图

源码检索：
- ast_grep_search       ：关键字搜索代码（类似 grep）
- ast_glob_files        ：glob 模式匹配文件并返回内容
- ast_read_class_file   ：按项目+类名读取源文件
- ast_read_file         ：按路径读取文件
- ast_list_files        ：列出项目目录文件

启动方式：
  HTTP: python -m backend.mcp_server --port 18086
  stdio: python -m backend.mcp_server
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
from src.git_tools import GitTool

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
    """列出 Neo4j 中已扫描的项目。

    Returns:
        JSON: {"projects": [{"name", "path", "scanned_at"}], "total"}"""
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
    """查询指定方法的完整调用链路，包含 Dubbo/MQ/DB/HTTP 入口。

    Args:
        project: 项目名称（如 "user-service"）
        class_fqn: 类全限定名（如 "com.example.UserService"）
        method: 方法名（如 "createUser"）
        max_depth: 最大追踪深度，默认 10
    
    Returns:
        JSON: {"success", "call_tree", "dubbo_calls", "tables", "mq_info", "endpoints"}"""
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
    """查询调用统计摘要，轻量版不含完整调用树。

    Args:
        project: 项目名称
        class_fqn: 类全限定名
        method: 方法名
        max_depth: 最大追踪深度，默认 10
    
    Returns:
        JSON: {"success", "class_stats", "tables", "mq_list", "frontend_entries"}"""
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
    """获取项目调用关系图（节点+边）。

    Args:
        project: 项目名称（必填）
        start_class: 起始类名（空则返回整个项目图）
        max_depth: 最大深度，默认 3
        filter_mode: 过滤模式（none/loose/moderate/strict）
    
    Returns:
        JSON: {"nodes": [{"id", "type"}], "edges": [{"from", "to"}]}"""
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
# 工具 5：关键字搜索代码（grep）
# =========================================================

def _check_ripgrep_available() -> bool:
    """检查 ripgrep 是否可用"""
    import subprocess
    try:
        result = subprocess.run(
            ['rg', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _search_with_ripgrep(
    pattern: str,
    search_dir: Path,
    repos_base: Path,
    file_pattern: str = "",
    context_lines: int = 3,
    max_results: int = 50
) -> dict:
    """使用 ripgrep 进行高性能搜索"""
    import subprocess
    
    cmd = ['rg', '--json', '--no-heading', '--ignore-case']
    
    if context_lines > 0:
        cmd.extend(['-C', str(context_lines)])
    
    # 添加文件模式过滤
    if file_pattern and file_pattern.strip():
        cmd.extend(['-g', file_pattern.strip()])
    
    # 添加搜索模式和路径
    cmd.append(pattern)
    cmd.append(str(search_dir))
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='replace'
        )
        
        # ripgrep 返回 1 表示未找到匹配，这是正常的
        if process.returncode not in (0, 1):
            return {"success": False, "error": f"ripgrep 执行失败: {process.stderr}"}
        
        results = []
        file_matches = {}  # {file_path: {matches: [], lines: set()}}
        total_matches = 0
        truncated = False
        
        for line in process.stdout.strip().split('\n'):
            if not line or total_matches >= max_results:
                if total_matches >= max_results:
                    truncated = True
                break
            
            try:
                match_data = json.loads(line)
                if match_data.get('type') != 'match':
                    continue
                
                data = match_data.get('data', {})
                file_path_str = data.get('path', {}).get('text', '')
                line_number = data.get('line_number', 0)
                line_text = data.get('lines', {}).get('text', '').rstrip()
                
                if not file_path_str:
                    continue
                
                file_path = Path(file_path_str)
                try:
                    relative_path = file_path.relative_to(repos_base)
                    path_parts = relative_path.parts
                    proj_name = path_parts[0] if path_parts else ""
                    file_relative = str(Path(*path_parts[1:])) if len(path_parts) > 1 else file_path.name
                except ValueError:
                    proj_name = ""
                    file_relative = str(file_path)
                
                if file_path_str not in file_matches:
                    file_matches[file_path_str] = {
                        "file": file_relative,
                        "project": proj_name,
                        "absolute_path": file_path_str,
                        "matches": [],
                        "full_content": None,
                        "total_lines": 0
                    }
                
                file_matches[file_path_str]["matches"].append({
                    "line_number": line_number,
                    "line_content": line_text,
                    "context_before": [],
                    "context_after": []
                })
                total_matches += 1
                
            except json.JSONDecodeError:
                continue
        
        # 读取完整文件内容（对于小文件）
        for file_path_str, file_info in file_matches.items():
            try:
                with open(file_path_str, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                file_info["total_lines"] = len(lines)
                if len(lines) <= 500:
                    file_info["full_content"] = ''.join(lines)
                
                # 为每个匹配添加上下文
                for match in file_info["matches"]:
                    ln = match["line_number"] - 1
                    start = max(0, ln - context_lines)
                    end = min(len(lines), ln + context_lines + 1)
                    match["context_before"] = [l.rstrip() for l in lines[start:ln]]
                    match["context_after"] = [l.rstrip() for l in lines[ln+1:end]]
            except Exception:
                pass
        
        results = list(file_matches.values())
        
        return {
            "success": True,
            "results": results,
            "total_matches": total_matches,
            "total_files": len(results),
            "truncated": truncated,
            "search_engine": "ripgrep"
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "ripgrep 搜索超时"}
    except Exception as e:
        return {"success": False, "error": f"ripgrep 搜索失败: {str(e)}"}


def _search_with_python(
    pattern: str,
    search_dir: Path,
    repos_base: Path,
    file_pattern: str = "",
    context_lines: int = 3,
    max_results: int = 50
) -> dict:
    """使用 Python 实现搜索（ripgrep 不可用时的回退方案）"""
    import re
    
    results = []
    total_matches = 0
    truncated = False
    
    try:
        pattern_regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return {"success": False, "error": f"正则表达式无效: {e}"}
    
    file_ext_pattern = None
    if file_pattern and file_pattern.strip():
        fp = file_pattern.strip().replace('.', r'\.').replace('*', '.*')
        try:
            file_ext_pattern = re.compile(fp + '$', re.IGNORECASE)
        except re.error:
            pass
    
    for root, dirs, files in os.walk(search_dir):
        dirs[:] = [d for d in dirs if d != '.git' and not d.startswith('.')]
        
        for filename in files:
            if total_matches >= max_results:
                truncated = True
                break
            
            if file_ext_pattern and not file_ext_pattern.search(filename):
                continue
            
            file_path = Path(root) / filename
            
            try:
                relative_path = file_path.relative_to(repos_base)
                path_parts = relative_path.parts
                proj_name = path_parts[0] if path_parts else ""
                file_relative = str(Path(*path_parts[1:])) if len(path_parts) > 1 else filename
            except ValueError:
                proj_name = ""
                file_relative = str(file_path)
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                matches = []
                for i, line in enumerate(lines):
                    if pattern_regex.search(line):
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        
                        matches.append({
                            "line_number": i + 1,
                            "line_content": line.rstrip(),
                            "context_before": [l.rstrip() for l in lines[start:i]],
                            "context_after": [l.rstrip() for l in lines[i+1:end]]
                        })
                        total_matches += 1
                        
                        if total_matches >= max_results:
                            truncated = True
                            break
                
                if matches:
                    full_content = None
                    if len(lines) <= 500:
                        full_content = ''.join(lines)
                    
                    results.append({
                        "file": file_relative,
                        "project": proj_name,
                        "absolute_path": str(file_path),
                        "matches": matches,
                        "full_content": full_content,
                        "total_lines": len(lines)
                    })
                    
            except Exception:
                continue
        
        if truncated:
            break
    
    return {
        "success": True,
        "results": results,
        "total_matches": total_matches,
        "total_files": len(results),
        "truncated": truncated,
        "search_engine": "python"
    }


@mcp.tool()
async def ast_grep_search(
    pattern: str,
    project: str = "",
    file_pattern: str = "",
    max_results: int = 50,
    context_lines: int = 3,
) -> str:
    """关键字搜索代码，类似 grep，返回匹配的代码片段和完整文件。

    Args:
        pattern: 搜索关键字或正则（必填，如 "UserService"、"@Autowired"）
        project: 项目名称（空则搜索全部项目）
        file_pattern: 文件名匹配（如 "*.java"）
        max_results: 最大结果数，默认 50
        context_lines: 上下文行数，默认 3
    
    Returns:
        JSON: {"success", "results": [{"file", "project", "matches", "full_content"}], "total_matches", "truncated"}
    """
    import asyncio
    
    if not pattern or not pattern.strip():
        return json.dumps({"success": False, "error": "pattern 为必填参数"}, ensure_ascii=False)
    
    try:
        git_tool = GitTool()
        repos_base = git_tool.repos_base
        
        if not repos_base.exists():
            return json.dumps({"success": False, "error": f"git-repos 目录不存在: {repos_base}"}, ensure_ascii=False)
        
        # 确定搜索目录
        if project and project.strip():
            search_dir = repos_base / project.strip()
            if not search_dir.exists():
                return json.dumps({"success": False, "error": f"项目 '{project}' 不存在"}, ensure_ascii=False)
        else:
            search_dir = repos_base
        
        # 使用线程池执行搜索（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        
        # 优先使用 ripgrep
        if _check_ripgrep_available():
            result = await loop.run_in_executor(
                None,
                lambda: _search_with_ripgrep(
                    pattern, search_dir, repos_base,
                    file_pattern, context_lines, max_results
                )
            )
        else:
            result = await loop.run_in_executor(
                None,
                lambda: _search_with_python(
                    pattern, search_dir, repos_base,
                    file_pattern, context_lines, max_results
                )
            )
        
        result["search_dir"] = str(search_dir)
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error("ast_grep_search 失败: %s", e)
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# =========================================================
# 工具 6：glob 模式匹配文件并返回内容
# =========================================================

@mcp.tool()
async def ast_glob_files(
    pattern: str,
    project: str = "",
    max_files: int = 20,
    max_lines_per_file: int = 500,
    include_content: bool = True,
) -> str:
    """glob 模式匹配文件并返回内容。

    Args:
        pattern: glob 模式（必填，如 "**/UserService.java"、"src/**/*.java"）
        project: 项目名称（空则搜索全部项目）
        max_files: 最大返回文件数，默认 20
        max_lines_per_file: 每个文件最大行数，默认 500
        include_content: 是否包含文件内容，默认 True
    
    Returns:
        JSON: {"success", "files": [{"path", "relative_path", "project", "content", "total_lines"}], "total", "truncated"}
    """
    import glob as glob_module
    
    if not pattern or not pattern.strip():
        return json.dumps({"success": False, "error": "pattern 为必填参数"}, ensure_ascii=False)
    
    try:
        git_tool = GitTool()
        repos_base = git_tool.repos_base
        
        if not repos_base.exists():
            return json.dumps({"success": False, "error": f"git-repos 目录不存在: {repos_base}"}, ensure_ascii=False)
        
        # 确定搜索目录
        if project and project.strip():
            search_dir = repos_base / project.strip()
            if not search_dir.exists():
                return json.dumps({"success": False, "error": f"项目 '{project}' 不存在"}, ensure_ascii=False)
        else:
            search_dir = repos_base
        
        pattern = pattern.strip()
        
        # 使用 pathlib 的 glob 进行匹配
        matched_files = []
        truncated = False
        
        # 支持递归 glob (**)
        if '**' in pattern:
            matches = list(search_dir.glob(pattern))
        else:
            matches = list(search_dir.glob(pattern))
        
        # 过滤文件（排除目录和隐藏文件）
        file_matches = [
            p for p in matches 
            if p.is_file() and not any(part.startswith('.') for part in p.parts)
        ]
        
        # 按文件名排序
        file_matches.sort(key=lambda p: p.name)
        
        # 限制数量
        if len(file_matches) > max_files:
            truncated = True
            file_matches = file_matches[:max_files]
        
        for file_path in file_matches:
            try:
                relative_path = file_path.relative_to(repos_base)
                path_parts = relative_path.parts
                proj_name = path_parts[0] if path_parts else ""
                file_relative = str(Path(*path_parts[1:])) if len(path_parts) > 1 else file_path.name
            except ValueError:
                proj_name = ""
                file_relative = str(file_path)
            
            file_info = {
                "path": str(file_path),
                "relative_path": file_relative,
                "project": proj_name,
                "total_lines": 0,
                "truncated": False,
            }
            
            if include_content:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    file_info["total_lines"] = len(lines)
                    
                    if len(lines) > max_lines_per_file:
                        lines = lines[:max_lines_per_file]
                        file_info["truncated"] = True
                    
                    file_info["content"] = ''.join(lines)
                except Exception as e:
                    file_info["content"] = ""
                    file_info["error"] = str(e)
            else:
                # 不含内容时，仍然获取行数
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_info["total_lines"] = sum(1 for _ in f)
                except Exception:
                    pass
            
            matched_files.append(file_info)
        
        return json.dumps({
            "success": True,
            "pattern": pattern,
            "search_dir": str(search_dir),
            "files": matched_files,
            "total": len(matched_files),
            "truncated": truncated
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error("ast_glob_files 失败: %s", e)
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# =========================================================
# 工具 7：按类名读取完整源文件（从 code-index-demo 迁移）
# =========================================================

def _fqcn_to_relative_path(fqcn: str, ext: str = ".java") -> str:
    """将全限定类名转换为相对文件路径"""
    if not fqcn or not fqcn.strip():
        return ""
    q = fqcn.strip().replace(".", "/")
    if ext and not ext.startswith("."):
        ext = "." + ext
    return f"src/main/java/{q}{ext}"


def _path_to_fqcn(file_path: Path) -> str:
    """从文件路径提取全限定类名"""
    path_str = file_path.as_posix()
    marker = "src/main/java/"
    if marker in path_str:
        rest = path_str.split(marker, 1)[1]
        for ext in (".java", ".kt", ".py", ".ts", ".js"):
            if rest.endswith(ext):
                return rest[: -len(ext)].replace("/", ".")
        return rest.replace("/", ".")
    return ""


def _resolve_class_file(project_name: str, fqcn: str, repos_base: Path):
    """
    根据项目名和类名解析文件路径
    返回 (absolute_path, relative_path) 或 (None, None)
    """
    if not project_name or not fqcn:
        return None, None

    raw = fqcn.strip()
    is_full = "." in raw  # 是否为全限定类名
    simple = raw.split(".")[-1] if is_full else raw  # 简单类名

    def match(p: Path) -> bool:
        return p.is_file() and (not is_full or _path_to_fqcn(p) == raw)

    git_root = repos_base / project_name

    # 1. 在 git-repos/{project} 下搜索
    if git_root.exists():
        for ext in (".java", ".kt", ".py", ".scala"):
            for p in git_root.rglob(simple + ext):
                if match(p):
                    try:
                        return p.resolve(), str(p.relative_to(git_root))
                    except ValueError:
                        return p.resolve(), str(p)

    # 2. 使用 FQCN 拼路径兜底（标准 Maven 目录结构）
    if is_full:
        for ext in (".java", ".kt", ".py"):
            rel = _fqcn_to_relative_path(raw, ext)
            if not rel:
                continue
            # 尝试在项目根目录下查找
            p = git_root / rel
            if p.is_file():
                return p.resolve(), rel
            # 尝试在子模块目录下查找
            if git_root.exists():
                for subdir in git_root.iterdir():
                    if subdir.is_dir():
                        p = subdir / rel
                        if p.is_file():
                            try:
                                return p.resolve(), str(p.relative_to(git_root))
                            except ValueError:
                                return p.resolve(), str(p)

    return None, None


@mcp.tool()
async def ast_read_class_file(
    project: str,
    class_name: str,
    max_lines: int = 800,
) -> str:
    """按项目+类名读取完整源文件，智能查找支持全限定名或简单类名。

    Args:
        project: 项目名称（必填，如 "user-service"）
        class_name: 类名（全限定如 "com.example.UserService" 或简单如 "UserService"）
        max_lines: 最大读取行数，默认 800
    
    Returns:
        JSON: {"success", "project", "class_name", "file_path", "content", "total_lines", "truncated"}
    """
    if not class_name or not class_name.strip():
        return json.dumps({"success": False, "error": "请输入类名"}, ensure_ascii=False)
    if not project or not project.strip():
        return json.dumps({"success": False, "error": "请提供项目名称"}, ensure_ascii=False)
    
    try:
        git_tool = GitTool()
        repos_base = git_tool.repos_base
        
        project = project.strip()
        class_name = class_name.strip()
        
        # 解析文件路径
        abs_path, rel_path = _resolve_class_file(project, class_name, repos_base)
        
        if not abs_path:
            return json.dumps({
                "success": False,
                "error": f"未找到类文件: {class_name}",
                "project": project,
                "class_name": class_name,
                "search_dir": str(repos_base / project)
            }, ensure_ascii=False)
        
        # 读取文件内容
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        truncated = total_lines > max_lines
        
        # 限制行数
        if truncated:
            lines = lines[:max_lines]
        
        content = ''.join(lines)
        
        return json.dumps({
            "success": True,
            "project": project,
            "class_name": class_name,
            "file_path": str(abs_path),
            "relative_path": rel_path or "",
            "total_lines": total_lines,
            "start_line": 1,
            "end_line": len(lines),
            "truncated": truncated,
            "content": content
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error("ast_read_class_file 失败: %s", e)
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# =========================================================
# 工具 8：按文件路径读取文件内容
# =========================================================

@mcp.tool()
async def ast_read_file(
    file_path: str,
    start_line: int = 0,
    end_line: int = 0,
) -> str:
    """按路径读取文件内容，支持行范围限定。

    Args:
        file_path: 文件路径（相对 git-repos 如 "project/src/Main.java"，或绝对路径）
        start_line: 起始行号（1-based，0=从头）
        end_line: 结束行号（1-based，0=到末尾）
    
    Returns:
        JSON: {"success", "file_path", "content", "total_lines", "range"}
    """
    if not file_path or not file_path.strip():
        return json.dumps({"success": False, "error": "file_path 为必填参数"}, ensure_ascii=False)
    
    try:
        git_tool = GitTool()
        repos_base = git_tool.repos_base
        
        # 处理路径
        file_path = file_path.strip()
        target_path = Path(file_path)
        
        # 如果不是绝对路径，则相对于 git-repos
        if not target_path.is_absolute():
            target_path = repos_base / file_path
        
        # 安全检查：确保在 git-repos 目录内
        try:
            target_path = target_path.resolve()
            if not str(target_path).startswith(str(repos_base.resolve())):
                return json.dumps({"success": False, "error": "只能读取 git-repos 目录内的文件"}, ensure_ascii=False)
        except Exception:
            return json.dumps({"success": False, "error": "路径解析失败"}, ensure_ascii=False)
        
        if not target_path.exists():
            return json.dumps({"success": False, "error": f"文件不存在: {file_path}"}, ensure_ascii=False)
        
        if not target_path.is_file():
            return json.dumps({"success": False, "error": f"路径不是文件: {file_path}"}, ensure_ascii=False)
        
        # 读取文件
        with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # 处理行范围
        actual_start = max(1, start_line) if start_line > 0 else 1
        actual_end = min(total_lines, end_line) if end_line > 0 else total_lines
        
        # 提取指定范围的内容
        selected_lines = lines[actual_start - 1:actual_end]
        content = ''.join(selected_lines)
        
        return json.dumps({
            "success": True,
            "file_path": str(target_path),
            "relative_path": str(target_path.relative_to(repos_base)),
            "content": content,
            "total_lines": total_lines,
            "range": {
                "start": actual_start,
                "end": actual_end
            }
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error("ast_read_file 失败: %s", e)
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool()
async def ast_list_files(
    project: str,
    path: str = "",
    file_pattern: str = "",
) -> str:
    """列出项目目录下的文件列表。

    Args:
        project: 项目名称（必填）
        path: 子目录路径（可选，相对项目根）
        file_pattern: 文件名匹配（可选，如 "*.java"）
    
    Returns:
        JSON: {"success", "project", "path", "items": [{"name", "type", "size"}], "total"}
    """
    import re
    
    if not project or not project.strip():
        return json.dumps({"success": False, "error": "project 为必填参数"}, ensure_ascii=False)
    
    try:
        git_tool = GitTool()
        repos_base = git_tool.repos_base
        
        project = project.strip()
        project_dir = repos_base / project
        
        if not project_dir.exists():
            return json.dumps({"success": False, "error": f"项目 '{project}' 不存在"}, ensure_ascii=False)
        
        # 处理子目录
        target_dir = project_dir
        if path and path.strip():
            target_dir = project_dir / path.strip()
        
        # 安全检查
        try:
            target_dir = target_dir.resolve()
            if not str(target_dir).startswith(str(repos_base.resolve())):
                return json.dumps({"success": False, "error": "路径越界"}, ensure_ascii=False)
        except Exception:
            return json.dumps({"success": False, "error": "路径解析失败"}, ensure_ascii=False)
        
        if not target_dir.exists():
            return json.dumps({"success": False, "error": f"目录不存在: {path}"}, ensure_ascii=False)
        
        if not target_dir.is_dir():
            return json.dumps({"success": False, "error": f"路径不是目录: {path}"}, ensure_ascii=False)
        
        # 文件名模式
        file_ext_pattern = None
        if file_pattern and file_pattern.strip():
            fp = file_pattern.strip().replace('.', '\\.').replace('*', '.*')
            file_ext_pattern = re.compile(fp + '$', re.IGNORECASE)
        
        items = []
        for item in sorted(target_dir.iterdir()):
            # 跳过隐藏文件和 .git
            if item.name.startswith('.'):
                continue
            
            item_type = "directory" if item.is_dir() else "file"
            
            # 文件类型过滤（只对文件生效）
            if file_ext_pattern and item.is_file():
                if not file_ext_pattern.search(item.name):
                    continue
            
            size = 0
            if item.is_file():
                try:
                    size = item.stat().st_size
                except Exception:
                    pass
            
            items.append({
                "name": item.name,
                "type": item_type,
                "size": size
            })
        
        return json.dumps({
            "success": True,
            "project": project,
            "path": str(target_dir.relative_to(project_dir)) if target_dir != project_dir else "",
            "absolute_path": str(target_dir),
            "items": items,
            "total": len(items)
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error("ast_list_files 失败: %s", e)
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


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
