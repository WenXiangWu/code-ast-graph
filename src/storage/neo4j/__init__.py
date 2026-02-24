"""
Neo4j 存储实现
"""

from .storage import Neo4jStorage

# 保留旧名称以兼容
Neo4jClient = Neo4jStorage

__all__ = [
    'Neo4jStorage',
    # 兼容性导出
    'Neo4jClient'
]
