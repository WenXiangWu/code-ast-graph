#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 NobleController 实现的接口"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 NobleController 实现的接口")
print("=" * 100)

# 1. official-room-pro-web.NobleController
print("\n1. official-room-pro-web.NobleController 实现的接口:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS {name: 'NobleController'})
    MATCH (c)-[:IMPLEMENTS]->(i:INTERFACE)
    RETURN c.fqn as class_fqn, i.fqn as interface_fqn, i.name as interface_name
""")

if result:
    for r in result:
        print(f"  类: {r['class_fqn']}")
        print(f"  实现接口: {r['interface_fqn']}")
else:
    print("  未找到")

# 2. official-room-pro-web.NobleController 的 openNoble 方法调用了谁
print("\n2. official-room-pro-web.NobleController.openNoble 调用了谁:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS {name: 'NobleController'})
    MATCH (c)-[:DECLARES]->(m:Method {name: 'openNoble'})
    MATCH (m)-[r:DUBBO_CALLS]->(target:Method)
    MATCH (target_class)-[:DECLARES]->(target)
    RETURN m.signature as caller,
           r.via_field as via_field,
           target.signature as callee,
           target_class.fqn as callee_class
""")

if result:
    for r in result:
        print(f"  调用方: {r['caller']}")
        print(f"  通过字段: {r['via_field']}")
        print(f"  被调用方: {r['callee']}")
        print(f"  被调用类: {r['callee_class']}")
else:
    print("  未找到")

# 3. official-room-pro-web 项目有哪些 NobleRemoteService 接口
print("\n3. official-room-pro-web 项目的 NobleRemoteService 接口:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(i:INTERFACE)
    WHERE i.name CONTAINS 'NobleRemoteService'
    RETURN i.fqn as fqn, i.file_path as file_path
""")

if result:
    for r in result:
        print(f"  接口: {r['fqn']}")
        print(f"  文件: {r['file_path']}")
else:
    print("  未找到")

# 4. 检查 official-room-pro-web.NobleController 是否实现了 official.api.NobleRemoteService
print("\n4. 检查 official-room-pro-web.NobleController 是否实现了 official.api.NobleRemoteService:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS {name: 'NobleController'})
    MATCH (c)-[:IMPLEMENTS]->(i:INTERFACE)
    WHERE i.fqn = 'com.yupaopao.yuer.chatroom.official.api.NobleRemoteService'
    RETURN c.fqn as class_fqn, i.fqn as interface_fqn
""")

if result:
    print(f"  是的，实现了该接口")
    for r in result:
        print(f"    类: {r['class_fqn']}")
        print(f"    接口: {r['interface_fqn']}")
else:
    print(f"  没有实现该接口")

print("\n" + "=" * 100)
