#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试下游 Dubbo 调用"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("调试下游 Dubbo 调用")
print("=" * 100)

# 1. 检查 official-room-pro-web.NobleController.openNoble 方法
print("\n1. 检查方法是否存在:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS)
    WHERE c.name = 'NobleController'
    MATCH (c)-[:DECLARES]->(m:Method {name: 'openNoble'})
    RETURN c.fqn as class_fqn, m.signature as method_sig
""")

if result:
    for r in result:
        print(f"  类: {r['class_fqn']}")
        print(f"  方法签名: {r['method_sig']}")
else:
    print("  未找到方法")

# 2. 检查该方法的 DUBBO_CALLS 关系
print("\n2. 检查方法的 DUBBO_CALLS 关系:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS)
    WHERE c.name = 'NobleController'
    MATCH (c)-[:DECLARES]->(m:Method {name: 'openNoble'})
    OPTIONAL MATCH (m)-[r:DUBBO_CALLS]->(target:Method)
    MATCH (target_class)-[:DECLARES]->(target)
    RETURN 
        m.signature as caller_sig,
        r.via_field as via_field,
        target.signature as target_sig,
        target_class.fqn as target_class
""")

if result:
    print(f"  找到 {len(result)} 个 DUBBO_CALLS:")
    for r in result:
        print(f"\n    调用方: {r['caller_sig']}")
        print(f"    通过字段: {r['via_field']}")
        print(f"    目标方法: {r['target_sig']}")
        print(f"    目标类: {r['target_class']}")
else:
    print("  未找到任何 DUBBO_CALLS 关系")

# 3. 检查该方法的所有 CALLS 关系
print("\n3. 检查方法的所有 CALLS 关系:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS)
    WHERE c.name = 'NobleController'
    MATCH (c)-[:DECLARES]->(m:Method {name: 'openNoble'})
    OPTIONAL MATCH (m)-[r:CALLS]->(target:Method)
    MATCH (target_class)-[:DECLARES]->(target)
    RETURN 
        m.signature as caller_sig,
        target.signature as target_sig,
        target_class.fqn as target_class,
        count(r) as calls_count
    LIMIT 20
""")

if result:
    print(f"  找到 {len(result)} 个 CALLS:")
    for r in result:
        if r['target_sig']:
            print(f"\n    调用方: {r['caller_sig']}")
            print(f"    目标方法: {r['target_sig']}")
            print(f"    目标类: {r['target_class']}")
            print(f"    CALLS 数量: {r['calls_count']}")
else:
    print("  未找到任何 CALLS 关系")

# 4. 检查该类的注入字段
print("\n4. 检查 NobleController 的注入字段:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS)
    WHERE c.name = 'NobleController'
    MATCH (c)-[:HAS_FIELD]->(f)
    WHERE f.is_injected = true
    RETURN f.name as field_name, f.type as field_type
""")

if result:
    print(f"  找到 {len(result)} 个注入字段:")
    for r in result:
        print(f"    字段名: {r['field_name']}")
        print(f"    字段类型: {r['field_type']}")
        if 'NobleRemoteService' in r['field_type']:
            print(f"      *** 这是 NobleRemoteService 字段！")
else:
    print("  未找到注入字段")

print("\n" + "=" * 100)
