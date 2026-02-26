#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 NobleController 是如何被创建为 INTERFACE 的"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 NobleController INTERFACE 节点")
print("=" * 100)

# 1. 查找所有 NobleController INTERFACE 节点
print("\n1. 所有 NobleController INTERFACE 节点:")
result = storage.execute_query("""
    MATCH (i:INTERFACE)
    WHERE i.name = 'NobleController'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(i)
    OPTIONAL MATCH (impl)-[:IMPLEMENTS]->(i)
    RETURN 
        i.fqn as fqn,
        p.name as project,
        i.is_external as is_external,
        collect(DISTINCT impl.fqn) as implementers
""")

if result:
    print(f"  找到 {len(result)} 个 INTERFACE 节点:")
    for r in result:
        print(f"    FQN: {r['fqn']}")
        print(f"    项目: {r['project'] or 'Unknown'}")
        print(f"    is_external: {r['is_external']}")
        print(f"    被实现: {r['implementers']}")
        print()
else:
    print("  未找到 INTERFACE 节点")

# 2. 查找谁实现了 NobleController
print("\n2. 查找谁实现了 NobleController (IMPLEMENTS -> NobleController):")
result = storage.execute_query("""
    MATCH (impl)-[:IMPLEMENTS]->(i)
    WHERE i.name = 'NobleController'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(impl)
    RETURN 
        p.name as impl_project,
        impl.fqn as impl_fqn,
        labels(impl) as impl_labels,
        i.fqn as interface_fqn
""")

if result:
    print(f"  找到 {len(result)} 个实现:")
    for r in result:
        print(f"    实现类: {r['impl_fqn']} ({r['impl_labels'][0]})")
        print(f"    项目: {r['impl_project'] or 'Unknown'}")
        print(f"    实现接口: {r['interface_fqn']}")
        print()
else:
    print("  没有类实现 NobleController")

# 3. 查找 NobleController CLASS 实现了什么
print("\n3. NobleController CLASS 实现了什么:")
result = storage.execute_query("""
    MATCH (c:CLASS)-[:IMPLEMENTS]->(i)
    WHERE c.name = 'NobleController'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN 
        p.name as project,
        c.fqn as class_fqn,
        collect(i.fqn) as implements
""")

if result:
    print(f"  找到 {len(result)} 个 CLASS:")
    for r in result:
        print(f"    类: {r['class_fqn']}")
        print(f"    项目: {r['project'] or 'Unknown'}")
        print(f"    实现接口: {r['implements']}")
        print()
else:
    print("  未找到")

print("\n" + "=" * 100)
