#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查找谁在调用 NobleController 的方法"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("查找谁在调用 NobleController")
print("=" * 100)

# 1. 查找调用 NobleController INTERFACE 节点的方法
print("\n1. 查找调用 NobleController INTERFACE 节点的方法:")
result = storage.execute_query("""
    MATCH (caller_method:Method)-[:CALLS]->(called_method:Method)
    MATCH (i:INTERFACE {name: 'NobleController'})-[:DECLARES]->(called_method)
    MATCH (caller_class)-[:DECLARES]->(caller_method)
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(caller_class)
    RETURN 
        p.name as caller_project,
        caller_class.fqn as caller_class,
        caller_method.name as caller_method,
        called_method.name as called_method,
        i.fqn as interface_fqn
    LIMIT 20
""")

if result:
    print(f"  找到 {len(result)} 个调用:")
    for r in result:
        print(f"    调用者: {r['caller_project'] or 'Unknown'}.{r['caller_class']}.{r['caller_method']}")
        print(f"    被调用: {r['interface_fqn']}.{r['called_method']}")
        print()
else:
    print("  未找到调用")

# 2. 查找 NobleController INTERFACE 节点声明的方法
print("\n2. NobleController INTERFACE 节点声明的方法:")
result = storage.execute_query("""
    MATCH (i:INTERFACE {name: 'NobleController'})-[:DECLARES]->(m:Method)
    RETURN 
        i.fqn as interface_fqn,
        m.name as method_name,
        m.signature as signature
    LIMIT 20
""")

if result:
    print(f"  找到 {len(result)} 个方法:")
    for r in result:
        print(f"    接口: {r['interface_fqn']}")
        print(f"    方法: {r['method_name']}")
        print(f"    签名: {r['signature']}")
        print()
else:
    print("  未找到方法")

print("\n" + "=" * 100)
