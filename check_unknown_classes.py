#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 Unknown 项目的类"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 Unknown 项目的类")
print("=" * 100)

# 1. 查找没有 CONTAINS 关系的类
print("\n1. 查找没有 CONTAINS 关系的类（前20个）:")
result = storage.execute_query("""
    MATCH (c)
    WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER)
    AND NOT (:Project)-[:CONTAINS]->(c)
    RETURN c.fqn as class_fqn, c.name as class_name, labels(c) as labels
    LIMIT 20
""")

if result:
    print(f"  找到 {len(result)} 个类没有项目关联:")
    for r in result:
        print(f"    {r['labels'][0]}: {r['class_fqn']}")
else:
    print("  所有类都有项目关联")

# 2. 检查 NobleManager 的项目关联
print("\n2. 检查 NobleManager 的项目关联:")
result = storage.execute_query("""
    MATCH (c)
    WHERE c.name = 'NobleManager'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN c.fqn as class_fqn, labels(c) as labels, collect(p.name) as projects
""")

if result:
    for r in result:
        print(f"  类: {r['class_fqn']}")
        print(f"  类型: {r['labels']}")
        print(f"  项目: {r['projects']}")
else:
    print("  未找到 NobleManager")

# 3. 统计没有项目关联的类数量
print("\n3. 统计没有项目关联的类:")
result = storage.execute_query("""
    MATCH (c)
    WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER)
    AND NOT (:Project)-[:CONTAINS]->(c)
    RETURN count(c) as count
""")

if result:
    print(f"  总共 {result[0]['count']} 个类没有项目关联")

print("\n" + "=" * 100)
