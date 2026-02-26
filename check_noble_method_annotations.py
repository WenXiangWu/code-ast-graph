#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 NobleRemoteService 方法的注解"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 NobleRemoteService 方法的注解")
print("=" * 100)

# 查询 NobleRemoteService 的所有方法
result = storage.execute_query("""
    MATCH (i:INTERFACE {fqn: 'com.yupaopao.yuer.chatroom.official.api.NobleRemoteService'})
    MATCH (i)-[:DECLARES]->(m:Method)
    RETURN m.name as name, 
           m.signature as signature,
           m.annotations as annotations
    ORDER BY m.name
    LIMIT 20
""")

if result:
    print(f"\n找到 {len(result)} 个方法:")
    for r in result:
        print(f"\n  方法: {r['name']}")
        print(f"    签名: {r['signature']}")
        print(f"    注解: {r['annotations']}")
        
        if r['name'] == 'openNoble':
            print(f"    ⭐ 这是 openNoble 方法")
            if not r['annotations'] or r['annotations'] == 'None':
                print(f"    ❌ 注解为空！")
else:
    print("\n未找到任何方法")

print("\n" + "=" * 100)
