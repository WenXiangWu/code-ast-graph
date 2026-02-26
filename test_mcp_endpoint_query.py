#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 MCP endpoint 查询"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

start_method = "com.yupaopao.chatroom.controller.NobleController.openNoble(OpenNobleRequest)"

print("=" * 100)
print(f"测试 MCP Endpoint 查询: {start_method}")
print("=" * 100)

# 查询 1: 方法自身的 RpcEndpoint
print("\n查询 1: 方法自身的 RpcEndpoint")
result = storage.execute_query("""
    MATCH (m:Method {signature: $start_method})-[:EXPOSES]->(ep:RpcEndpoint)
    MATCH (c)-[:DECLARES]->(m)
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN 
        p.name as project,
        c.fqn as class_fqn,
        m.name as method,
        ep.path as path,
        ep.http_method as http_method
""", {'start_method': start_method})

if result:
    print(f"  找到 {len(result)} 个结果:")
    for r in result:
        print(f"    项目: {r['project']}")
        print(f"    类: {r['class_fqn']}")
        print(f"    方法: {r['method']}")
        print(f"    路径: {r['path']}")
else:
    print("  未找到")

# 查询 2: 实现的接口方法的 RpcEndpoint
print("\n查询 2: 实现的接口方法的 RpcEndpoint")
result = storage.execute_query("""
    MATCH (impl_class)-[:DECLARES]->(impl_method:Method {signature: $start_method})
    MATCH (impl_class)-[:IMPLEMENTS]->(iface:INTERFACE)
    MATCH (iface)-[:DECLARES]->(iface_method:Method)
    WHERE iface_method.name = impl_method.name
    OPTIONAL MATCH (iface_method)-[:EXPOSES]->(ep:RpcEndpoint)
    RETURN 
        iface.fqn as class_fqn,
        iface_method.name as method,
        iface_method.signature as method_sig,
        ep.path as path,
        ep.http_method as http_method
""", {'start_method': start_method})

if result:
    print(f"  找到 {len(result)} 个结果:")
    for r in result:
        print(f"    接口: {r['class_fqn']}")
        print(f"    方法: {r['method']}")
        print(f"    方法签名: {r['method_sig']}")
        print(f"    路径: {r['path']}")
else:
    print("  未找到")

# 查询 3: 反向查询 - 谁通过 DUBBO_CALLS 调用了这个方法
print("\n查询 3: 反向查询 - 谁通过 DUBBO_CALLS 调用了这个方法")
result = storage.execute_query("""
    MATCH (impl_class)-[:DECLARES]->(impl_method:Method {signature: $start_method})
    MATCH (impl_class)-[:IMPLEMENTS]->(iface:INTERFACE)
    MATCH (iface)-[:DECLARES]->(iface_method:Method)
    WHERE iface_method.name = impl_method.name
    MATCH (caller_method:Method)-[:DUBBO_CALLS]->(iface_method)
    MATCH (caller_class)-[:DECLARES]->(caller_method)
    
    OPTIONAL MATCH (caller_method)-[:EXPOSES]->(ep1:RpcEndpoint)
    OPTIONAL MATCH (iface_method)-[:EXPOSES]->(ep2:RpcEndpoint)
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(caller_class)
    
    RETURN DISTINCT
        p.name as project,
        caller_class.fqn as class_fqn,
        caller_method.name as method,
        caller_method.signature as caller_sig,
        iface_method.signature as iface_sig,
        COALESCE(ep1.path, ep2.path) as path,
        COALESCE(ep1.http_method, ep2.http_method) as http_method
""", {'start_method': start_method})

if result:
    print(f"  找到 {len(result)} 个结果:")
    for r in result:
        print(f"\n    项目: {r['project']}")
        print(f"    调用方类: {r['class_fqn']}")
        print(f"    调用方方法: {r['method']}")
        print(f"    调用方签名: {r['caller_sig']}")
        print(f"    接口方法签名: {r['iface_sig']}")
        print(f"    路径: {r['path']}")
        print(f"    HTTP方法: {r['http_method']}")
else:
    print("  未找到")

print("\n" + "=" * 100)
