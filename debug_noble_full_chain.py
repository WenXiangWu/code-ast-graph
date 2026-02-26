#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整调试 Noble 调用链"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("完整调试 Noble 调用链")
print("=" * 100)

# 1. 检查 official-room-pro-web 的 NobleRemoteService 接口
print("\n1. official-room-pro-web.NobleRemoteService 接口:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(i:INTERFACE)
    WHERE i.fqn = 'com.yupaopao.yuer.chatroom.official.api.NobleRemoteService'
    RETURN i.name as name, i.fqn as fqn, i.file_path as file_path
""")

if result:
    print(f"  找到接口: {result[0]['fqn']}")
    print(f"  文件路径: {result[0]['file_path']}")
else:
    print("  未找到接口")
    exit(1)

# 2. 检查该接口的 openNoble 方法
print("\n2. official-room-pro-web.NobleRemoteService.openNoble 方法:")
result = storage.execute_query("""
    MATCH (i:INTERFACE {fqn: 'com.yupaopao.yuer.chatroom.official.api.NobleRemoteService'})
    MATCH (i)-[:DECLARES]->(m:Method {name: 'openNoble'})
    OPTIONAL MATCH (m)-[:EXPOSES]->(ep:RpcEndpoint)
    RETURN m.signature as signature, 
           m.annotations as annotations,
           ep.path as endpoint_path,
           ep.http_method as http_method
""")

if result:
    print(f"  方法签名: {result[0]['signature']}")
    print(f"  方法注解: {result[0]['annotations']}")
    print(f"  Endpoint 路径: {result[0]['endpoint_path']}")
    print(f"  HTTP 方法: {result[0]['http_method']}")
    
    if not result[0]['endpoint_path']:
        print("  ❌ 没有 RpcEndpoint！这是问题所在！")
else:
    print("  ❌ 未找到 openNoble 方法")
    exit(1)

# 3. 检查 official-room-pro-web.NobleController 的 openNoble 方法
print("\n3. official-room-pro-web.NobleController.openNoble:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS {name: 'NobleController'})
    MATCH (c)-[:DECLARES]->(m:Method {name: 'openNoble'})
    RETURN c.fqn as class_fqn, m.signature as method_sig
""")

if result:
    print(f"  类FQN: {result[0]['class_fqn']}")
    print(f"  方法签名: {result[0]['method_sig']}")
else:
    print("  未找到")

# 4. 检查 official-room-pro-web.NobleController.openNoble 是否调用了 yuer-chatroom-service
print("\n4. official-room-pro-web.NobleController.openNoble 的 DUBBO_CALLS:")
result = storage.execute_query("""
    MATCH (p1:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c1:CLASS {name: 'NobleController'})
    MATCH (c1)-[:DECLARES]->(m1:Method {name: 'openNoble'})
    OPTIONAL MATCH (m1)-[r:DUBBO_CALLS]->(m2:Method)
    OPTIONAL MATCH (c2)-[:DECLARES]->(m2)
    OPTIONAL MATCH (p2:Project)-[:CONTAINS]->(c2)
    RETURN m1.signature as caller,
           type(r) as rel_type,
           r.via_field as via_field,
           m2.signature as callee,
           c2.fqn as callee_class,
           p2.name as callee_project
""")

if result and result[0]['callee']:
    for r in result:
        print(f"  调用方: {r['caller']}")
        print(f"  关系类型: {r['rel_type']}")
        print(f"  通过字段: {r['via_field']}")
        print(f"  被调用方: {r['callee']}")
        print(f"  被调用类: {r['callee_class']}")
        print(f"  被调用项目: {r['callee_project']}")
else:
    print("  ❌ 没有 DUBBO_CALLS 关系")

# 5. 检查 yuer-chatroom-service.NobleController.openNoble
print("\n5. yuer-chatroom-service.NobleController.openNoble:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'yuer-chatroom-service'})-[:CONTAINS]->(c:CLASS {name: 'NobleController'})
    MATCH (c)-[:DECLARES]->(m:Method {name: 'openNoble'})
    RETURN c.fqn as class_fqn, m.signature as method_sig
""")

if result:
    print(f"  类FQN: {result[0]['class_fqn']}")
    print(f"  方法签名: {result[0]['method_sig']}")
else:
    print("  未找到")

# 6. 反向查询：谁在调用 yuer-chatroom-service.NobleController.openNoble
print("\n6. 反向查询：谁在调用 yuer-chatroom-service.NobleController.openNoble:")
result = storage.execute_query("""
    MATCH (p1:Project {name: 'yuer-chatroom-service'})-[:CONTAINS]->(c1:CLASS {name: 'NobleController'})
    MATCH (c1)-[:DECLARES]->(m1:Method {name: 'openNoble'})
    OPTIONAL MATCH (caller:Method)-[r:CALLS|DUBBO_CALLS]->(m1)
    OPTIONAL MATCH (caller_class)-[:DECLARES]->(caller)
    OPTIONAL MATCH (p2:Project)-[:CONTAINS]->(caller_class)
    RETURN caller.signature as caller_method,
           type(r) as rel_type,
           caller_class.fqn as caller_class,
           p2.name as caller_project
""")

if result and result[0]['caller_method']:
    print(f"  找到 {len(result)} 个上游调用:")
    for r in result:
        print(f"\n    调用方项目: {r['caller_project']}")
        print(f"    调用方类: {r['caller_class']}")
        print(f"    调用方方法: {r['caller_method']}")
        print(f"    关系类型: {r['rel_type']}")
else:
    print("  ❌ 没有找到任何上游调用")

print("\n" + "=" * 100)
