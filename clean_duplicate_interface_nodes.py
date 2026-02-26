#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理与 CLASS 节点 FQN 重复的 INTERFACE 占位符节点"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("清理重复的 INTERFACE 节点")
print("=" * 100)

# 1. 查找重复的节点（同一个 FQN 既有 CLASS 又有 INTERFACE）
print("\n1. 查找重复的节点:")
result = storage.execute_query("""
    MATCH (c:CLASS)
    MATCH (i:INTERFACE {fqn: c.fqn})
    WHERE i.is_external = true
    RETURN c.fqn as fqn, c.name as name
    LIMIT 50
""")

if result:
    print(f"  找到 {len(result)} 个重复的 FQN:")
    for r in result[:10]:  # 只显示前10个
        print(f"    {r['fqn']}")
    if len(result) > 10:
        print(f"    ... 还有 {len(result) - 10} 个")
    
    # 2. 删除这些重复的 INTERFACE 节点
    print("\n2. 删除重复的 INTERFACE 节点...")
    delete_result = storage.execute_query("""
        MATCH (c:CLASS)
        MATCH (i:INTERFACE {fqn: c.fqn})
        WHERE i.is_external = true
        WITH i
        DETACH DELETE i
        RETURN count(i) as deleted_count
    """)
    
    if delete_result:
        print(f"  ✓ 已删除 {delete_result[0]['deleted_count']} 个重复的 INTERFACE 节点")
else:
    print("  未找到重复的节点")

# 3. 查找重复的节点（同一个 FQN 既有 MAPPER 又有 INTERFACE）
print("\n3. 查找 MAPPER 的重复节点:")
result = storage.execute_query("""
    MATCH (m:MAPPER)
    MATCH (i:INTERFACE {fqn: m.fqn})
    WHERE i.is_external = true
    RETURN m.fqn as fqn, m.name as name
    LIMIT 50
""")

if result:
    print(f"  找到 {len(result)} 个重复的 FQN:")
    for r in result[:10]:
        print(f"    {r['fqn']}")
    if len(result) > 10:
        print(f"    ... 还有 {len(result) - 10} 个")
    
    # 删除
    print("\n4. 删除 MAPPER 的重复 INTERFACE 节点...")
    delete_result = storage.execute_query("""
        MATCH (m:MAPPER)
        MATCH (i:INTERFACE {fqn: m.fqn})
        WHERE i.is_external = true
        WITH i
        DETACH DELETE i
        RETURN count(i) as deleted_count
    """)
    
    if delete_result:
        print(f"  ✓ 已删除 {delete_result[0]['deleted_count']} 个重复的 INTERFACE 节点")
else:
    print("  未找到重复的节点")

# 5. 统计清理后的情况
print("\n5. 清理后统计:")
result = storage.execute_query("""
    MATCH (c)
    WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER)
    AND NOT (:Project)-[:CONTAINS]->(c)
    RETURN count(c) as count
""")

if result:
    print(f"  剩余 {result[0]['count']} 个类没有项目关联")

print("\n" + "=" * 100)
print("✓ 清理完成")
print("=" * 100)
