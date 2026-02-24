#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
删除 Neo4j 中的指定项目及其所有相关数据
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


def delete_project(client, project_name: str):
    """删除指定项目及其所有相关数据"""
    logger.info(f"开始删除项目: {project_name}")
    
    try:
        # 先查询项目包含的数据量
        count_query = """
        MATCH (p:Project {name: $project_name})
        OPTIONAL MATCH (p)-[:CONTAINS*]->(entity)
        RETURN 
          count(DISTINCT entity) AS entity_count,
          count(DISTINCT (p)-[:CONTAINS*]->(entity)) AS relationship_count
        """
        result = client.execute_query(count_query, {"project_name": project_name})
        if result and result[0]['entity_count']:
            logger.info(f"  项目包含 {result[0]['entity_count']} 个实体节点")
        
        # 删除项目及其所有相关数据
        delete_query = """
        MATCH (p:Project {name: $project_name})
        OPTIONAL MATCH (p)-[r1:CONTAINS*]->(entity)
        OPTIONAL MATCH (entity)-[r2]->()
        WITH p, collect(DISTINCT entity) AS entities, collect(DISTINCT r1) AS rels1, collect(DISTINCT r2) AS rels2
        FOREACH (r IN rels1 | DELETE r)
        FOREACH (r IN rels2 | DELETE r)
        FOREACH (e IN entities | DETACH DELETE e)
        DELETE p
        RETURN count(p) AS deleted_count
        """
        
        # 使用更安全的方式删除：先删除关系，再删除节点
        delete_query_safe = """
        MATCH (p:Project {name: $project_name})
        OPTIONAL MATCH (p)-[:CONTAINS*]->(entity)
        WITH p, collect(DISTINCT entity) AS entities
        // 删除所有连接到实体的关系
        FOREACH (e IN entities |
          FOREACH (r IN [(e)-[r]->() | r] | DELETE r)
          FOREACH (r IN [()-[r]->(e) | r] | DELETE r)
        )
        // 删除所有实体节点
        FOREACH (e IN entities | DELETE e)
        // 删除项目节点
        DELETE p
        RETURN count(p) AS deleted_count
        """
        
        # 使用更简单直接的方式
        delete_query_simple = """
        MATCH (p:Project {name: $project_name})
        OPTIONAL MATCH (p)-[:CONTAINS*]->(entity)
        DETACH DELETE entity
        DETACH DELETE p
        RETURN count(p) AS deleted_count
        """
        
        result = client.execute_write(delete_query_simple, {"project_name": project_name})
        logger.info(f"✅ 项目 {project_name} 删除成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ 删除项目 {project_name} 失败: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    # 要删除的项目列表
    projects_to_delete = [
        "chatroom-router-service-router-api",
        "chatroom-router-service-router-gateway-api",
        "chatroom-router-service-router-service"
    ]
    
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
    
    # 删除项目
    logger.info("=" * 60)
    logger.info("开始删除项目")
    logger.info("=" * 60)
    
    success_count = 0
    for project_name in projects_to_delete:
        if delete_project(client, project_name):
            success_count += 1
        logger.info("")
    
    logger.info("=" * 60)
    logger.info(f"删除完成！成功删除 {success_count}/{len(projects_to_delete)} 个项目")
    logger.info("=" * 60)
    
    # 查询剩余项目
    try:
        logger.info("\n剩余项目列表:")
        result = client.execute_query("""
            MATCH (p:Project)
            RETURN p.name AS project_name
            ORDER BY p.name
        """)
        for record in result:
            logger.info(f"  - {record['project_name']}")
    except Exception as e:
        logger.warning(f"查询剩余项目失败: {e}")
    
    # 关闭连接
    client.close()


if __name__ == "__main__":
    main()
