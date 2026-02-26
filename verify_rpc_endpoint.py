#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 RpcEndpoint 是否创建"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("验证 RpcEndpoint")
print("=" * 100)

# 1. 检查 NobleRemoteService.openNoble 方法的 RpcEndpoint
print("\n1. 检查 NobleRemoteService.openNoble 的 RpcEndpoint:")
result = storage.execute_query("""
    MATCH (i:INTERFACE {fqn: 'com.yupaopao.yuer.chatroom.official.api.NobleRemoteService'})
    MATCH (i)-[:DECLARES]->(m:Method {name: 'openNoble'})
    OPTIONAL MATCH (m)-[:EXPOSES]->(ep:RpcEndpoint)
    RETURN m.signature as method_sig,
           m.annotations as annotations,
           ep.path as endpoint_path,
           ep.http_method as http_method
""")

if result:
    r = result[0]
    print(f"  方法签名: {r['method_sig']}")
    print(f"  注解: {r['annotations']}")
    print(f"  Endpoint 路径: {r['endpoint_path']}")
    print(f"  HTTP 方法: {r['http_method']}")
    
    if r['endpoint_path']:
        print(f"  状态: RpcEndpoint 已创建")
    else:
        print(f"  状态: RpcEndpoint 未创建！")
else:
    print("  未找到方法")

# 2. 检查所有 RpcEndpoint 节点
print("\n2. 检查所有 RpcEndpoint 节点:")
result = storage.execute_query("""
    MATCH (ep:RpcEndpoint)
    WHERE ep.path CONTAINS 'noble'
    RETURN ep.path as path, ep.http_method as method
    LIMIT 20
""")

if result:
    print(f"  找到 {len(result)} 个与 noble 相关的 RpcEndpoint:")
    for r in result:
        print(f"    {r['method']} {r['path']}")
else:
    print("  未找到任何与 noble 相关的 RpcEndpoint")

# 3. 检查 official-room-pro-web 项目的所有 RpcEndpoint
print("\n3. 检查 official-room-pro-web 项目的所有 RpcEndpoint:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c)
    MATCH (c)-[:DECLARES]->(m:Method)
    MATCH (m)-[:EXPOSES]->(ep:RpcEndpoint)
    RETURN c.name as class_name, m.name as method_name, ep.path as path
    LIMIT 20
""")

if result:
    print(f"  找到 {len(result)} 个 RpcEndpoint:")
    for r in result:
        print(f"    {r['class_name']}.{r['method_name']} -> {r['path']}")
else:
    print("  未找到任何 RpcEndpoint")

print("\n" + "=" * 100)
