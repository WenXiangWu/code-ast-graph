#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试重复的前端入口"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

start_method = "com.yupaopao.chatroom.controller.NobleController.openNoble(OpenNobleRequest)"

print("=" * 100)
print("调试重复的前端入口")
print("=" * 100)

# 执行查询 3 - 查看详细结果
print("\n查询 3: 反向查询 - 谁通过 DUBBO_CALLS 调用了这个方法")
result = storage.execute_query("""
    MATCH (impl_class)-[:DECLARES]->(impl_method:Method {signature: $start_method})
    MATCH (impl_class)-[:IMPLEMENTS]->(iface:INTERFACE)
    MATCH (iface)-[:DECLARES]->(iface_method:Method)
    WHERE iface_method.name = impl_method.name
    MATCH (caller_method:Method)-[:DUBBO_CALLS]->(iface_method)
    MATCH (caller_class)-[:DECLARES]->(caller_method)
    
    // 3.1 先查调用方自身的 RpcEndpoint
    OPTIONAL MATCH (caller_method)-[:EXPOSES]->(ep1:RpcEndpoint)
    
    // 3.2 查询调用方实现的接口方法的 RpcEndpoint（@MobileAPI 在调用方的接口上）
    OPTIONAL MATCH (caller_class)-[:IMPLEMENTS]->(caller_iface:INTERFACE)
    OPTIONAL MATCH (caller_iface)-[:DECLARES]->(caller_iface_method:Method)
    WHERE caller_iface_method.name = caller_method.name
    OPTIONAL MATCH (caller_iface_method)-[:EXPOSES]->(ep2:RpcEndpoint)
    
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(caller_class)
    
    // 返回所有详细信息
    RETURN 
        p.name as project,
        caller_class.fqn as caller_class_fqn,
        caller_method.name as caller_method_name,
        caller_method.signature as caller_method_sig,
        ep1.path as ep1_path,
        caller_iface.fqn as caller_iface_fqn,
        caller_iface_method.signature as caller_iface_method_sig,
        ep2.path as ep2_path,
        COALESCE(ep1.path, ep2.path) as final_path,
        COALESCE(ep1.http_method, ep2.http_method) as final_http_method
""", {'start_method': start_method})

if result:
    print(f"  找到 {len(result)} 个结果:")
    for i, r in enumerate(result, 1):
        print(f"\n  结果 {i}:")
        print(f"    项目: {r['project']}")
        print(f"    调用方类: {r['caller_class_fqn']}")
        print(f"    调用方方法: {r['caller_method_name']}")
        print(f"    调用方方法签名: {r['caller_method_sig']}")
        print(f"    调用方自身 RpcEndpoint (ep1): {r['ep1_path']}")
        print(f"    调用方接口: {r['caller_iface_fqn']}")
        print(f"    调用方接口方法签名: {r['caller_iface_method_sig']}")
        print(f"    调用方接口 RpcEndpoint (ep2): {r['ep2_path']}")
        print(f"    最终路径: {r['final_path']}")
        print(f"    最终 HTTP 方法: {r['final_http_method']}")
else:
    print("  未找到")

# 检查 NobleController 有多少个 openNoble 方法
print("\n\n检查 official-room-pro-web.NobleController 的 openNoble 方法:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS {name: 'NobleController'})
    MATCH (c)-[:DECLARES]->(m:Method {name: 'openNoble'})
    RETURN m.signature as signature, m.parameters as parameters
""")

if result:
    print(f"  找到 {len(result)} 个 openNoble 方法:")
    for r in result:
        print(f"    签名: {r['signature']}")
        print(f"    参数: {r['parameters']}")
else:
    print("  未找到")

# 检查 NobleController 实现了多少个接口
print("\n\n检查 official-room-pro-web.NobleController 实现的接口:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS {name: 'NobleController'})
    MATCH (c)-[:IMPLEMENTS]->(i:INTERFACE)
    RETURN i.fqn as interface_fqn
""")

if result:
    print(f"  实现了 {len(result)} 个接口:")
    for r in result:
        print(f"    接口: {r['interface_fqn']}")
else:
    print("  未实现任何接口")

print("\n" + "=" * 100)
