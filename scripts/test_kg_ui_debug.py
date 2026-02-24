"""
测试知识图谱UI相关问题的调试脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_neo4j_connection():
    """测试 Neo4j 连接"""
    logger.info("=" * 80)
    logger.info("测试 1: Neo4j 连接")
    logger.info("=" * 80)
    
    from src.storage.neo4j import Neo4jStorage
    
    client = Neo4jStorage()
    
    if not client.is_connected():
        logger.info("尝试连接到 Neo4j...")
        success = client.connect()
        if not success:
            logger.error("❌ Neo4j 连接失败")
            return False
    
    logger.info("✅ Neo4j 已连接")
    return True


def test_get_projects():
    """测试获取项目列表"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 2: 获取已扫描项目列表")
    logger.info("=" * 80)
    
    from src.storage.neo4j import Neo4jStorage
    
    # 使用新架构：直接查询 Neo4j
    client = Neo4jStorage()
    if not client.is_connected():
        client.connect()
    
    # 模拟 ui_manager 的功能
    class UIManager:
        def __init__(self, client):
            self.client = client
        def is_initialized(self):
            return self.client.is_connected()
        def get_scanned_projects_list(self):
            result = self.client.execute_query("MATCH (p:Project) RETURN p.name as name ORDER BY p.name")
            return [r['name'] for r in result if r.get('name')]
    
    ui_manager = UIManager(client)
    
    if not ui_manager.is_initialized():
        logger.error("❌ UI Manager 未初始化")
        return False
    
    projects = ui_manager.get_scanned_projects_list()
    
    logger.info(f"获取到 {len(projects)} 个已扫描项目:")
    for i, project in enumerate(projects, 1):
        logger.info(f"  {i}. {project}")
    
    if not projects:
        logger.warning("⚠️ 没有找到已扫描的项目")
        logger.info("\n提示:")
        logger.info("  1. 检查 Neo4j 中是否有项目数据")
        logger.info("  2. 尝试在知识图谱管理页面扫描项目")
    
    return True


def test_get_unscanned_projects():
    """测试获取未扫描项目列表"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 3: 获取未扫描项目列表")
    logger.info("=" * 80)
    
    from src.storage.neo4j import Neo4jStorage
    
    # 使用新架构：直接查询 Neo4j
    client = Neo4jStorage()
    if not client.is_connected():
        client.connect()
    
    # 模拟 ui_manager 的功能
    class UIManager:
        def __init__(self, client):
            self.client = client
        def is_initialized(self):
            return self.client.is_connected()
        def get_scanned_projects_list(self):
            result = self.client.execute_query("MATCH (p:Project) RETURN p.name as name ORDER BY p.name")
            return [r['name'] for r in result if r.get('name')]
    
    ui_manager = UIManager(client)
    
    if not ui_manager.is_initialized():
        logger.error("❌ UI Manager 未初始化")
        return False
    
    # 使用新架构：直接查询 Neo4j
    result = client.execute_query("""
        MATCH (p:Project)
        RETURN p.name as name, COALESCE(p.path, '') as path
        ORDER BY p.name ASC
    """)
    
    import pandas as pd
    df = pd.DataFrame([
        {
            "项目名称": r.get('name'),
            "项目路径": r.get('path', ''),
            "状态": "已构建 ✅"
        }
        for r in result if r.get('name')
    ])
    
    logger.info(f"获取到 {len(df)} 个项目:")
    if not df.empty:
        logger.info(f"\n{df.to_string()}")
    
    if df.empty:
        logger.warning("⚠️ 没有找到项目")
        logger.info("\n提示:")
        logger.info("  1. 检查 Neo4j 中是否有项目数据")
        logger.info("  2. 尝试使用后端 API 扫描项目")
    
    return True


def test_neo4j_data():
    """测试 Neo4j 中的数据"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 4: 检查 Neo4j 中的数据")
    logger.info("=" * 80)
    
    from src.storage.neo4j import Neo4jStorage
    
    client = Neo4jStorage()
    if not client.is_connected():
        if not client.connect():
            logger.error("❌ Neo4j 未连接")
            return False
    
    # 检查标签
    logger.info("\n--- 检查标签 ---")
    labels_result = client.execute_query("CALL db.labels() YIELD label RETURN label")
    logger.info(f"找到 {len(labels_result)} 个标签:")
    for label in labels_result:
        logger.info(f"  - {label['label']}")
    
    # 检查项目节点
    logger.info("\n--- 检查 Project 节点 ---")
    project_result = client.execute_query("""
        MATCH (p:Project)
        RETURN p.name as name, p.scanned_at as scanned_at
    """)
    logger.info(f"找到 {len(project_result)} 个项目:")
    for proj in project_result:
        logger.info(f"  - {proj['name']} (扫描时间: {proj.get('scanned_at', 'N/A')})")
    
    # 检查类型节点
    logger.info("\n--- 检查 Type 节点 ---")
    type_result = client.execute_query("""
        MATCH (t:Type)
        RETURN t.project as project, count(t) as count
        ORDER BY count DESC
    """)
    logger.info(f"各项目的类型数量:")
    for row in type_result:
        logger.info(f"  - {row['project']}: {row['count']}")
    
    # 检查依赖关系
    logger.info("\n--- 检查依赖关系 ---")
    dep_result = client.execute_query("""
        MATCH ()-[r:DEPENDS_ON]->()
        RETURN count(r) as count
    """)
    if dep_result:
        logger.info(f"依赖关系总数: {dep_result[0]['count']}")
    
    return True


def main():
    """主函数"""
    logger.info("开始知识图谱 UI 调试测试...\n")
    
    # 测试 1: Neo4j 连接
    if not test_neo4j_connection():
        logger.error("\n❌ Neo4j 连接失败，无法继续测试")
        return
    
    # 测试 2: 获取已扫描项目列表
    test_get_projects()
    
    # 测试 3: 获取未扫描项目列表
    test_get_unscanned_projects()
    
    # 测试 4: 检查 Neo4j 数据
    test_neo4j_data()
    
    logger.info("\n" + "=" * 80)
    logger.info("测试完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
