#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 NobleRemoteService 的实现情况"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 NobleRemoteService 的实现情况")
print("=" * 100)

# 1. 查找 NobleRemoteService 接口
print("\n1. 查找 NobleRemoteService 接口:")
result = storage.execute_query("""
    MATCH (iface:INTERFACE)
    WHERE iface.name = 'NobleRemoteService'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(iface)
    RETURN 
        iface.fqn as fqn,
        p.name as project
""")

if result:
    for r in result:
        print(f"  FQN: {r['fqn']}")
        print(f"  项目: {r['project'] or 'Unknown'}")
        print()
else:
    print("  未找到")

# 2. 查找实现类
print("\n2. 查找 NobleRemoteService 的实现类:")
result = storage.execute_query("""
    MATCH (impl)-[:IMPLEMENTS]->(iface:INTERFACE)
    WHERE iface.name = 'NobleRemoteService'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(impl)
    RETURN 
        iface.fqn as interface_fqn,
        impl.fqn as impl_fqn,
        labels(impl) as impl_labels,
        p.name as project
""")

if result:
    print(f"  找到 {len(result)} 个实现类:")
    for r in result:
        print(f"    接口: {r['interface_fqn']}")
        print(f"    实现: {r['impl_fqn']} ({r['impl_labels'][0]})")
        print(f"    项目: {r['project'] or 'Unknown'}")
        print()
else:
    print("  未找到实现类")

# 3. 检查 openNoble 方法
print("\n3. 检查 NobleRemoteService.openNoble 方法:")
result = storage.execute_query("""
    MATCH (iface:INTERFACE)-[:DECLARES]->(m:Method)
    WHERE iface.name = 'NobleRemoteService' AND m.name = 'openNoble'
    RETURN 
        iface.fqn as interface_fqn,
        m.signature as signature
""")

if result:
    for r in result:
        print(f"  接口: {r['interface_fqn']}")
        print(f"  签名: {r['signature']}")
        print()
else:
    print("  未找到")

# 4. 检查实现类的 openNoble 方法
print("\n4. 检查实现类的 openNoble 方法:")
result = storage.execute_query("""
    MATCH (iface:INTERFACE {name: 'NobleRemoteService'})<-[:IMPLEMENTS]-(impl)
    MATCH (impl)-[:DECLARES]->(m:Method {name: 'openNoble'})
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(impl)
    RETURN 
        impl.fqn as impl_fqn,
        m.signature as signature,
        p.name as project
""")

if result:
    print(f"  找到 {len(result)} 个实现方法:")
    for r in result:
        print(f"    类: {r['impl_fqn']}")
        print(f"    项目: {r['project'] or 'Unknown'}")
        print(f"    签名: {r['signature']}")
        print()
else:
    print("  未找到实现方法")

# 5. 检查 yuer-chatroom-service 的 NobleController
print("\n5. 检查 yuer-chatroom-service 的 NobleController:")
result = storage.execute_query("""
    MATCH (c)-[:DECLARES]->(m:Method)
    WHERE c.name = 'NobleController' AND m.name = 'openNoble'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    WHERE p.name = 'yuer-chatroom-service'
    RETURN 
        c.fqn as class_fqn,
        m.signature as signature,
        labels(c) as labels
""")

if result:
    for r in result:
        print(f"  类: {r['class_fqn']} ({r['labels'][0]})")
        print(f"  签名: {r['signature']}")
        print()
else:
    print("  未找到")

# 6. 检查是否实现了 NobleRemoteService
print("\n6. 检查 NobleController 是否实现了 NobleRemoteService:")
result = storage.execute_query("""
    MATCH (impl {name: 'NobleController'})-[:IMPLEMENTS]->(iface)
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(impl)
    WHERE p.name = 'yuer-chatroom-service'
    RETURN 
        impl.fqn as impl_fqn,
        iface.fqn as interface_fqn
""")

if result:
    print(f"  找到 {len(result)} 个实现关系:")
    for r in result:
        print(f"    {r['impl_fqn']} implements {r['interface_fqn']}")
else:
    print("  NobleController 没有实现任何接口")

print("\n" + "=" * 100)
