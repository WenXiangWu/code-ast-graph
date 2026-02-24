#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
演示 Neo4j 中如何区分和查询项目
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.neo4j import Neo4jStorage
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demonstrate_project_distinction():
    """演示项目区分机制"""
    # 检查Neo4j连接
    try:
        if not os.getenv('NEO4J_URI'):
            os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
        if not os.getenv('NEO4J_USER'):
            os.environ['NEO4J_USER'] = 'neo4j'
        if not os.getenv('NEO4J_PASSWORD'):
            os.environ['NEO4J_PASSWORD'] = 'jqassistant123'
        
        client = Neo4jStorage()
        if not client.is_connected():
            logger.info("正在连接Neo4j...")
            if not client.connect():
                logger.error("无法连接到Neo4j")
                return
        logger.info("✅ Neo4j连接成功\n")
    except Exception as e:
        logger.error(f"Neo4j连接失败: {e}")
        return
    
    try:
        # 1. 查询所有项目（展示项目区分）
        logger.info("=" * 80)
        logger.info("1. 查询所有项目（展示项目区分机制）")
        logger.info("=" * 80)
        query1 = """
        MATCH (p:Project)
        RETURN p.name AS project_name, 
               p.path AS project_path,
               p.scanned_at AS scanned_at,
               p.scanner AS scanner
        ORDER BY p.name
        """
        
        results = client.execute_query(query1)
        logger.info(f"\n找到 {len(results)} 个项目:\n")
        for i, record in enumerate(results, 1):
            logger.info(f"{i}. 项目名称: {record['project_name']}")
            logger.info(f"   路径: {record['project_path']}")
            logger.info(f"   扫描时间: {record['scanned_at']}")
            logger.info(f"   扫描器: {record['scanner']}")
            logger.info("")
        
        # 2. 查询每个项目的统计信息
        logger.info("\n" + "=" * 80)
        logger.info("2. 查询每个项目的统计信息")
        logger.info("=" * 80)
        query2 = """
        MATCH (p:Project)
        OPTIONAL MATCH (p)-[:CONTAINS*]->(t:Type)
        OPTIONAL MATCH (t)-[:DECLARES]->(m:Method)
        OPTIONAL MATCH (t)-[:DECLARES]->(f:Field)
        OPTIONAL MATCH (p)-[:CONTAINS]->(pkg:Package)
        RETURN 
          p.name AS project_name,
          p.scanned_at AS scanned_at,
          count(DISTINCT pkg) AS package_count,
          count(DISTINCT t) AS type_count,
          count(DISTINCT m) AS method_count,
          count(DISTINCT f) AS field_count
        ORDER BY p.name
        """
        
        results = client.execute_query(query2)
        logger.info(f"\n项目统计信息:\n")
        logger.info(f"{'项目名称':<50} {'包数':<8} {'类型数':<10} {'方法数':<10} {'字段数':<10}")
        logger.info("-" * 100)
        for record in results:
            logger.info(f"{record['project_name']:<50} "
                      f"{record['package_count']:<8} "
                      f"{record['type_count']:<10} "
                      f"{record['method_count']:<10} "
                      f"{record['field_count']:<10}")
        
        # 3. 查询特定项目的详细信息
        logger.info("\n" + "=" * 80)
        logger.info("3. 查询特定项目的详细信息（以 official-room-pro-service 为例）")
        logger.info("=" * 80)
        query3 = """
        MATCH (p:Project {name: 'official-room-pro-service'})
        OPTIONAL MATCH (p)-[:CONTAINS*]->(t:Type)
        OPTIONAL MATCH (t)-[:DECLARES]->(m:Method)
        OPTIONAL MATCH (t)-[:DECLARES]->(f:Field)
        OPTIONAL MATCH (p)-[:CONTAINS]->(pkg:Package)
        RETURN 
          p.name AS project_name,
          p.path AS project_path,
          p.scanned_at AS scanned_at,
          p.scanner AS scanner,
          count(DISTINCT pkg) AS package_count,
          count(DISTINCT t) AS type_count,
          count(DISTINCT m) AS method_count,
          count(DISTINCT f) AS field_count
        """
        
        results = client.execute_query(query3)
        if results:
            record = results[0]
            logger.info(f"\n项目名称: {record['project_name']}")
            logger.info(f"项目路径: {record['project_path']}")
            logger.info(f"扫描时间: {record['scanned_at']}")
            logger.info(f"扫描器: {record['scanner']}")
            logger.info(f"\n统计信息:")
            logger.info(f"  - 包数量: {record['package_count']}")
            logger.info(f"  - 类型数量: {record['type_count']}")
            logger.info(f"  - 方法数量: {record['method_count']}")
            logger.info(f"  - 字段数量: {record['field_count']}")
        else:
            logger.info("项目 'official-room-pro-service' 尚未扫描或不存在")
        
        # 4. 展示项目隔离性：查询不同项目的包
        logger.info("\n" + "=" * 80)
        logger.info("4. 展示项目隔离性：查询不同项目的包")
        logger.info("=" * 80)
        query4 = """
        MATCH (p:Project)-[:CONTAINS]->(pkg:Package)
        WHERE p.name IN ['official-room-pro-service', 'chatroom-router-service-router-api']
        RETURN 
          p.name AS project_name,
          pkg.fqn AS package_name
        ORDER BY p.name, pkg.fqn
        LIMIT 20
        """
        
        results = client.execute_query(query4)
        logger.info(f"\n不同项目的包（展示项目隔离）:\n")
        current_project = None
        for record in results:
            if current_project != record['project_name']:
                current_project = record['project_name']
                logger.info(f"\n项目: {current_project}")
            logger.info(f"  - {record['package_name']}")
        
        # 5. 查询项目间的依赖关系
        logger.info("\n" + "=" * 80)
        logger.info("5. 查询项目间的依赖关系")
        logger.info("=" * 80)
        query5 = """
        MATCH (p1:Project)-[:CONTAINS*]->(t1:Type)
        MATCH (p2:Project)-[:CONTAINS*]->(t2:Type)
        WHERE p1.name <> p2.name
          AND (t1)-[:DEPENDS_ON]->(t2)
        RETURN 
          p1.name AS dependent_project,
          p2.name AS dependency_project,
          count(*) AS dependency_count
        ORDER BY dependency_count DESC
        LIMIT 10
        """
        
        results = client.execute_query(query5)
        if results:
            logger.info(f"\n项目间依赖关系:\n")
            logger.info(f"{'依赖项目':<50} {'被依赖项目':<50} {'依赖数':<10}")
            logger.info("-" * 110)
            for record in results:
                logger.info(f"{record['dependent_project']:<50} "
                          f"{record['dependency_project']:<50} "
                          f"{record['dependency_count']:<10}")
        else:
            logger.info("未找到项目间依赖关系")
        
        # 6. 展示项目节点的结构
        logger.info("\n" + "=" * 80)
        logger.info("6. 展示项目节点的属性结构")
        logger.info("=" * 80)
        query6 = """
        MATCH (p:Project)
        RETURN p
        LIMIT 1
        """
        
        results = client.execute_query(query6)
        if results:
            logger.info("\n项目节点的属性结构:")
            logger.info("  - 节点标签: Project")
            logger.info("  - 属性:")
            logger.info("    * name: 项目唯一标识符（用于区分项目）")
            logger.info("    * path: 项目文件系统路径")
            logger.info("    * scanned_at: 扫描时间")
            logger.info("    * scanner: 使用的扫描器类型")
            logger.info("\n关键点: 'name' 属性是项目的唯一标识符，用于区分不同项目")
        
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
    finally:
        if client.is_connected():
            client.close()


if __name__ == "__main__":
    demonstrate_project_distinction()
