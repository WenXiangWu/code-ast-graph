#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清空Neo4j数据库
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


def main():
    """主函数"""
    # 检查Neo4j连接
    try:
        # 尝试使用默认配置
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
        logger.info("✅ Neo4j连接成功")
        
        # 清空所有数据
        logger.warning("⚠️  准备清空Neo4j数据库...")
        logger.warning("这将删除所有节点和关系！")
        
        try:
            # 删除所有关系
            logger.info("删除所有关系...")
            result = client.execute_write("""
                MATCH ()-[r]->()
                DELETE r
            """)
            logger.info("✅ 关系删除完成")
            
            # 删除所有节点
            logger.info("删除所有节点...")
            result = client.execute_write("""
                MATCH (n)
                DELETE n
            """)
            logger.info("✅ 节点删除完成")
            
            logger.info("=" * 60)
            logger.info("✅ Neo4j数据库已清空！")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"清空数据失败: {e}", exc_info=True)
            
    except Exception as e:
        logger.error(f"操作失败: {e}", exc_info=True)
    finally:
        if client.is_connected():
            client.close()


if __name__ == "__main__":
    main()
