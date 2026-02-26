#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析剩余的 Unknown 节点"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("分析剩余的 Unknown 节点")
print("=" * 100)

# 1. 按包名统计
print("\n1. 按包名前缀统计:")
result = storage.execute_query("""
    MATCH (c)
    WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER)
    AND NOT (:Project)-[:CONTAINS]->(c)
    WITH c, split(c.fqn, '.')[0..3] as package_prefix
    RETURN 
        package_prefix[0] + '.' + package_prefix[1] + '.' + package_prefix[2] as prefix,
        count(c) as count,
        collect(DISTINCT labels(c)[0]) as types
    ORDER BY count DESC
    LIMIT 20
""")

if result:
    for r in result:
        print(f"  {r['prefix']}: {r['count']} 个 ({', '.join(r['types'])})")

# 2. 检查是否是外部依赖
print("\n2. 检查是否是外部依赖 (is_external=true):")
result = storage.execute_query("""
    MATCH (c)
    WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER)
    AND NOT (:Project)-[:CONTAINS]->(c)
    AND c.is_external = true
    RETURN count(c) as external_count
""")

if result:
    print(f"  外部依赖: {result[0]['external_count']} 个")

# 3. 检查是否是内部类但没有项目关联
print("\n3. 检查内部类（is_external=false 或 NULL）:")
result = storage.execute_query("""
    MATCH (c)
    WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER)
    AND NOT (:Project)-[:CONTAINS]->(c)
    AND (c.is_external IS NULL OR c.is_external = false)
    RETURN 
        labels(c)[0] as type,
        c.fqn as fqn,
        c.is_external as is_external
    LIMIT 20
""")

if result:
    print(f"  找到 {len(result)} 个内部类没有项目关联:")
    for r in result:
        print(f"    {r['type']}: {r['fqn']} (is_external={r['is_external']})")
else:
    print("  所有内部类都有项目关联")

# 4. 按类型统计
print("\n4. 按节点类型统计:")
result = storage.execute_query("""
    MATCH (c)
    WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER)
    AND NOT (:Project)-[:CONTAINS]->(c)
    RETURN 
        labels(c)[0] as type,
        count(c) as count
    ORDER BY count DESC
""")

if result:
    for r in result:
        print(f"  {r['type']}: {r['count']} 个")

print("\n" + "=" * 100)
