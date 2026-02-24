"""
Code AST Graph MCP Server (集成 jQAssistant)
提供知识图谱架构分析的统一接口

注意：此项目专注于知识图谱分析，不包含代码搜索功能
如需代码搜索，请使用 code-index-demo 项目
"""

import asyncio
import logging
from mcp.server import Server
from mcp.types import Tool, TextContent

# 导入 jQAssistant 插件
from ..jqassistant.mcp_tools import get_jqassistant_tools

# 注意：代码搜索功能已移除，因为这是知识图谱项目，不包含代码搜索功能
# 如果需要代码搜索，请使用 code-index-demo 项目

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 MCP Server
app = Server("code-ast-graph")

# 初始化工具实例
jqa_tools = None

def ensure_jqa_tools():
    """确保 jQAssistant 工具已初始化"""
    global jqa_tools
    if jqa_tools is None:
        try:
            # 直接初始化 jQAssistant 工具
            jqa_tools = get_jqassistant_tools()
            logger.info("✅ jQAssistant 工具已加载")
        except Exception as e:
            logger.error(f"❌ 初始化 jQAssistant 工具失败: {e}")
    return jqa_tools


# ============================================
# 代码搜索工具 (已移除)
# ============================================
# 注意：代码搜索功能已移除，因为这是知识图谱项目
# 如需代码搜索功能，请使用 code-index-demo 项目
#
# 以下函数已注释，保留供参考：
#
# @app.tool()
# async def codebase_search(...) -> list:
#     """语义搜索代码库"""
#     pass
#
# @app.tool()
# async def grep_search(...) -> list:
#     """关键词搜索代码"""
#     pass
#
# @app.tool()
# async def read_file(...) -> dict:
#     """读取文件内容"""
#     pass


# ============================================
# jQAssistant 架构分析工具 (新增)
# ============================================

@app.tool()
async def jqa_scan_project(
    project_name: str,
    project_path: str,
    force_rescan: bool = False
) -> dict:
    """
    扫描 Java 项目并构建架构知识图谱
    
    使用 jQAssistant 分析项目代码，提取类、方法、依赖等信息存储到 Neo4j。
    
    Args:
        project_name: 项目名称
        project_path: 项目路径(必须是 Maven/Gradle 项目)
        force_rescan: 是否强制重新扫描(默认 false)
    
    Returns:
        {
            "success": true,
            "message": "扫描成功",
            "method": "maven"
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {
            "success": False,
            "error": "jQAssistant 插件未初始化"
        }
    
    return await tools.scan_project(project_name, project_path, force_rescan)


@app.tool()
async def jqa_list_projects() -> dict:
    """
    列出所有已扫描的项目
    
    Returns:
        {
            "projects": [
                {"name": "user-service", "path": "/path/to/user-service", "type_count": 150}
            ],
            "total": 1
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {"projects": [], "total": 0, "error": "插件未初始化"}
    
    return await tools.list_scanned_projects()


@app.tool()
async def jqa_get_call_graph(
    project: str,
    start_class: str = None,
    max_depth: int = 3
) -> dict:
    """
    获取服务调用关系图
    
    用于理解服务间的调用关系，生成调用链路图。
    
    Args:
        project: 项目名称
        start_class: 起始类名(可选),例如"UserService"或"UserController"
        max_depth: 最大追踪深度(1-5)
    
    Returns:
        {
            "nodes": [{"id": "com.example.UserService", "type": "Class"}],
            "edges": [{"from": "UserController", "to": "UserService", "depth": 1}],
            "total_nodes": 10,
            "total_edges": 15
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {"nodes": [], "edges": [], "error": "插件未初始化"}
    
    return await tools.get_service_call_graph(project, start_class, max_depth)


@app.tool()
async def jqa_get_database_schema(project: str) -> dict:
    """
    获取数据库表结构信息
    
    从 JPA 实体类(@Entity, @Table)中提取数据库表信息。
    
    Args:
        project: 项目名称
    
    Returns:
        {
            "tables": [
                {
                    "table_name": "user_info",
                    "entity_class": "com.example.entity.UserInfo",
                    "field_count": 10
                }
            ],
            "total": 1
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {"tables": [], "total": 0, "error": "插件未初始化"}
    
    return await tools.get_database_schema(project)


@app.tool()
async def jqa_get_table_accessors(
    project: str,
    table_name: str
) -> dict:
    """
    查询哪些类访问了指定的数据库表
    
    Args:
        project: 项目名称
        table_name: 表名(如"user_info"或"UserInfo")
    
    Returns:
        {
            "table_name": "user_info",
            "accessors": [
                {"class": "com.example.service.UserService", "name": "UserService"}
            ]
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {"table_name": table_name, "accessors": [], "error": "插件未初始化"}
    
    return await tools.get_table_access_info(project, table_name)


@app.tool()
async def jqa_get_dependencies(
    project: str,
    class_name: str,
    direction: str = "outgoing"
) -> dict:
    """
    查询类的依赖关系
    
    Args:
        project: 项目名称
        class_name: 类名(支持简单类名或全限定名)
        direction: 方向 - "outgoing"(依赖哪些类) 或 "incoming"(被哪些类依赖)
    
    Returns:
        {
            "class": "UserService",
            "dependencies": [
                {"class": "com.example.dao.UserDAO", "name": "UserDAO"}
            ]
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {"class": class_name, "dependencies": [], "error": "插件未初始化"}
    
    return await tools.get_class_dependencies(project, class_name, direction)


@app.tool()
async def jqa_analyze_impact(
    project: str,
    class_name: str,
    max_depth: int = 5
) -> dict:
    """
    影响面分析 - 评估修改某个类的影响范围
    
    用于技术方案设计时评估变更风险。
    
    Args:
        project: 项目名称
        class_name: 类名
        max_depth: 最大追踪深度(1-10)
    
    Returns:
        {
            "target_class": "UserService",
            "total_affected": 15,
            "risk_level": "high",
            "impact_by_level": {
                "1": [{"class": "UserController"}],
                "2": [{"class": "OrderService"}]
            }
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {
            "target_class": class_name,
            "total_affected": 0,
            "risk_level": "unknown",
            "error": "插件未初始化"
        }
    
    return await tools.analyze_impact(project, class_name, max_depth)


@app.tool()
async def jqa_find_similar_classes(
    project: str,
    reference_class: str,
    top_k: int = 5
) -> dict:
    """
    查找相似的类 - 基于依赖模式查找架构相似的类
    
    用于查找现有的实现模式，辅助技术方案设计。
    
    Args:
        project: 项目名称
        reference_class: 参考类名(如"UserService")
        top_k: 返回数量(1-20)
    
    Returns:
        {
            "reference_class": "UserService",
            "similar_classes": [
                {
                    "class": "OrderService",
                    "similarity_score": 8
                }
            ]
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {"reference_class": reference_class, "similar_classes": [], "error": "插件未初始化"}
    
    return await tools.find_similar_classes(project, reference_class, top_k)


@app.tool()
async def jqa_detect_cycles(project: str) -> dict:
    """
    检测循环依赖
    
    用于代码质量检查，识别不合理的循环依赖。
    
    Args:
        project: 项目名称
    
    Returns:
        {
            "cycles": [
                {"class1": "ServiceA", "class2": "ServiceB"}
            ],
            "total": 5
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {"cycles": [], "total": 0, "error": "插件未初始化"}
    
    return await tools.detect_circular_dependencies(project)


@app.tool()
async def jqa_get_package_structure(project: str) -> dict:
    """
    获取项目的包结构
    
    Args:
        project: 项目名称
    
    Returns:
        {
            "packages": [
                {"name": "com.example.service", "type_count": 20}
            ]
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {"packages": [], "error": "插件未初始化"}
    
    return await tools.get_package_structure(project)


@app.tool()
async def jqa_get_complexity_metrics(project: str) -> dict:
    """
    获取代码复杂度指标
    
    返回方法数和依赖数最多的类，用于识别过度复杂的代码。
    
    Args:
        project: 项目名称
    
    Returns:
        {
            "top_complex_classes": [
                {
                    "class": "UserService",
                    "method_count": 50,
                    "dependency_count": 15,
                    "complexity_score": 65
                }
            ]
        }
    """
    tools = ensure_jqa_tools()
    if tools is None:
        return {"top_complex_classes": [], "error": "插件未初始化"}
    
    return await tools.get_complexity_metrics(project)


# ============================================
# Server 信息
# ============================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用的工具"""
    tools_list = [
        # 代码搜索工具已移除（这是知识图谱项目，不包含代码搜索功能）
        # 如需代码搜索，请使用 code-index-demo 项目
    ]
    
    # 如果 jQAssistant 可用，添加架构分析工具
    if ensure_jqa_tools():
        tools_list.extend([
            Tool(
                name="jqa_scan_project",
                description="扫描 Java 项目构建架构图谱",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string"},
                        "project_path": {"type": "string"},
                        "force_rescan": {"type": "boolean", "default": False}
                    },
                    "required": ["project_name", "project_path"]
                }
            ),
            Tool(
                name="jqa_get_call_graph",
                description="获取服务调用关系图",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"},
                        "start_class": {"type": "string"},
                        "max_depth": {"type": "integer", "default": 3}
                    },
                    "required": ["project"]
                }
            ),
            Tool(
                name="jqa_get_database_schema",
                description="获取数据库表结构信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"}
                    },
                    "required": ["project"]
                }
            ),
            Tool(
                name="jqa_analyze_impact",
                description="影响面分析",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"},
                        "class_name": {"type": "string"},
                        "max_depth": {"type": "integer", "default": 5}
                    },
                    "required": ["project", "class_name"]
                }
            ),
            Tool(
                name="jqa_find_similar_classes",
                description="查找相似的类",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"},
                        "reference_class": {"type": "string"},
                        "top_k": {"type": "integer", "default": 5}
                    },
                    "required": ["project", "reference_class"]
                }
            ),
        ])
    
    return tools_list


if __name__ == "__main__":
    # 启动服务器
    logger.info("🚀 Code AST Graph MCP Server 启动中...")
    logger.info("📦 功能: jQAssistant 架构分析")
    app.run()
