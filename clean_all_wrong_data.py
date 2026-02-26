#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""彻底清理所有错误的数据"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("彻底清理所有错误的数据")
print("=" * 100)

# 1. 清理所有包含 'java.util' 的错误接口节点及其关系
print("\n1. 清理包含 'java.util' 的错误接口节点...")
result = storage.execute_query("""
    MATCH (i:INTERFACE)
    WHERE i.fqn CONTAINS 'java.util'
    RETURN count(i) as count
""")
print(f"  找到 {result[0]['count']} 个错误的接口节点")

storage.execute_query("""
    MATCH (i:INTERFACE)
    WHERE i.fqn CONTAINS 'java.util'
    DETACH DELETE i
""")
print("  删除完成")

# 2. 检查 NobleController 的 CONTAINS 关系
print("\n2. 检查 NobleController 的 CONTAINS 关系...")
result = storage.execute_query("""
    MATCH (c:CLASS {name: 'NobleController'})
    WHERE c.fqn = 'com.yupaopao.chatroom.official.room.web.controller.NobleController'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN c.fqn as class_fqn, collect(DISTINCT p.name) as projects
""")

if result:
    for r in result:
        print(f"  类: {r['class_fqn']}")
        print(f"  所属项目: {r['projects']}")
        if len(r['projects']) > 1:
            print(f"  警告: 该类属于多个项目！")
        elif not r['projects'] or r['projects'] == [None]:
            print(f"  警告: 该类不属于任何项目！")

# 3. 验证清理结果
print("\n3. 验证清理结果...")
result = storage.execute_query("""
    MATCH (c:CLASS {name: 'NobleController'})
    WHERE c.fqn = 'com.yupaopao.chatroom.official.room.web.controller.NobleController'
    MATCH (c)-[:IMPLEMENTS]->(i:INTERFACE)
    RETURN i.fqn as interface_fqn
""")

if result:
    print(f"  NobleController 实现的接口:")
    for r in result:
        print(f"    {r['interface_fqn']}")
else:
    print("  未实现任何接口")

print("\n" + "=" * 100)
