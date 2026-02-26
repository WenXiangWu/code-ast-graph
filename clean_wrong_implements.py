#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理错误的 IMPLEMENTS 关系"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("清理错误的 IMPLEMENTS 关系")
print("=" * 100)

# 1. 查找所有错误的 IMPLEMENTS 关系（接口 FQN 包含 'java.util'）
print("\n1. 查找错误的 IMPLEMENTS 关系...")
result = storage.execute_query("""
    MATCH (c:CLASS)-[r:IMPLEMENTS]->(i:INTERFACE)
    WHERE i.fqn CONTAINS 'java.util'
    RETURN c.fqn as class_fqn, i.fqn as interface_fqn, id(r) as rel_id
""")

if result:
    print(f"  找到 {len(result)} 个错误的关系:")
    for r in result:
        print(f"    {r['class_fqn']} -> {r['interface_fqn']}")
    
    # 2. 删除这些关系
    print("\n2. 删除错误的关系...")
    storage.execute_query("""
        MATCH (c:CLASS)-[r:IMPLEMENTS]->(i:INTERFACE)
        WHERE i.fqn CONTAINS 'java.util'
        DELETE r
    """)
    print("  删除完成")
    
    # 3. 删除错误的接口节点及其所有关系
    print("\n3. 删除错误的接口节点及其所有关系...")
    storage.execute_query("""
        MATCH (i:INTERFACE)
        WHERE i.fqn CONTAINS 'java.util'
        DETACH DELETE i
    """)
    print("  删除完成")
else:
    print("  未找到错误的关系")

# 4. 验证清理结果
print("\n4. 验证清理结果...")
result = storage.execute_query("""
    MATCH (c:CLASS {name: 'NobleController'})-[:IMPLEMENTS]->(i:INTERFACE)
    RETURN c.fqn as class_fqn, i.fqn as interface_fqn
""")

if result:
    print(f"  NobleController 的 IMPLEMENTS 关系:")
    for r in result:
        print(f"    {r['class_fqn']} -> {r['interface_fqn']}")
else:
    print("  未找到 IMPLEMENTS 关系")

print("\n" + "=" * 100)
