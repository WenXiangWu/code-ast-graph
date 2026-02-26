#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查项目构建状态"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查所有项目的构建状态")
print("=" * 100)

# 查询所有项目
result = storage.execute_query("""
    MATCH (p:Project)
    RETURN p.name as name, 
           p.scanned_commit_id as commit_id,
           p.scanned_at as scanned_at
    ORDER BY p.name
""")

if result:
    for r in result:
        print(f"\n项目: {r['name']}")
        print(f"  Commit ID: {r['commit_id']}")
        print(f"  扫描时间: {r['scanned_at']}")
        
        if r['commit_id']:
            print(f"  状态: ✅ 已构建")
        else:
            print(f"  状态: ❌ 未构建")
else:
    print("未找到任何项目")

print("\n" + "=" * 100)
