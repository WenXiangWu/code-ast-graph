#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 NobleController 的所有 openNoble 方法"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 NobleController 的所有 openNoble 方法")
print("=" * 100)

# 1. yuer-chatroom-service 项目
print("\n1. yuer-chatroom-service.NobleController.openNoble:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'yuer-chatroom-service'})-[:CONTAINS]->(c:CLASS)
    WHERE c.name = 'NobleController'
    MATCH (c)-[:DECLARES]->(m:Method)
    WHERE m.name = 'openNoble'
    RETURN 
        c.fqn as class_fqn,
        m.signature as signature,
        m.parameters as parameters
""")

if result:
    print(f"  找到 {len(result)} 个方法:")
    for r in result:
        print(f"    类: {r['class_fqn']}")
        print(f"    签名: {r['signature']}")
        print(f"    参数: {r['parameters']}")
        print()
else:
    print("  未找到")

# 2. official-room-pro-web 项目
print("\n2. official-room-pro-web.NobleController.openNoble:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS)
    WHERE c.name = 'NobleController'
    MATCH (c)-[:DECLARES]->(m:Method)
    WHERE m.name = 'openNoble'
    RETURN 
        c.fqn as class_fqn,
        m.signature as signature,
        m.parameters as parameters
""")

if result:
    print(f"  找到 {len(result)} 个方法:")
    for r in result:
        print(f"    类: {r['class_fqn']}")
        print(f"    签名: {r['signature']}")
        print(f"    参数: {r['parameters']}")
        print()
else:
    print("  未找到")

# 3. 所有 NobleController 类
print("\n3. 所有 NobleController 类:")
result = storage.execute_query("""
    MATCH (c)
    WHERE c.name = 'NobleController'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN 
        p.name as project,
        c.fqn as class_fqn,
        labels(c) as labels,
        c.arch_layer as arch_layer
""")

if result:
    print(f"  找到 {len(result)} 个 NobleController:")
    for r in result:
        print(f"    项目: {r['project'] or 'Unknown'}")
        print(f"    类: {r['class_fqn']}")
        print(f"    类型: {r['labels']}")
        print(f"    架构层: {r['arch_layer']}")
        print()
else:
    print("  未找到")

# 4. 检查 NobleRemoteService 接口的 openNoble 方法
print("\n4. 检查 NobleRemoteService 接口的 openNoble 方法:")
result = storage.execute_query("""
    MATCH (i:INTERFACE)-[:DECLARES]->(m:Method)
    WHERE i.name = 'NobleRemoteService' AND m.name = 'openNoble'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(i)
    RETURN 
        p.name as project,
        i.fqn as interface_fqn,
        m.signature as signature,
        m.parameters as parameters
""")

if result:
    print(f"  找到 {len(result)} 个接口方法:")
    for r in result:
        print(f"    项目: {r['project'] or 'Unknown'}")
        print(f"    接口: {r['interface_fqn']}")
        print(f"    签名: {r['signature']}")
        print(f"    参数: {r['parameters']}")
        print()
else:
    print("  未找到")

print("\n" + "=" * 100)
