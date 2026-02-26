#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证修复效果"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("验证修复效果")
print("=" * 100)

# 1. 检查 Unknown 节点数量
print("\n1. 检查 Unknown 节点数量:")
result = storage.execute_query("""
    MATCH (c)
    WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER)
    AND NOT (:Project)-[:CONTAINS]->(c)
    RETURN count(c) as count
""")
print(f"  剩余 Unknown 节点: {result[0]['count']} 个")

# 2. 检查 NobleController 是否还有 INTERFACE 重复节点
print("\n2. 检查 NobleController 是否还有 INTERFACE 重复节点:")
result = storage.execute_query("""
    MATCH (c:CLASS {name: 'NobleController'})
    MATCH (i:INTERFACE {fqn: c.fqn})
    RETURN count(i) as count
""")
print(f"  重复的 INTERFACE 节点: {result[0]['count']} 个")

# 3. 检查 NobleController 的 HAS_FIELD 关系
print("\n3. 检查 NobleController 的 HAS_FIELD 关系:")
result = storage.execute_query("""
    MATCH (c:CLASS {name: 'NobleController'})-[r:HAS_FIELD]->(f:Field)
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    WHERE p.name = 'yuer-chatroom-service'
    RETURN 
        c.fqn as class_fqn,
        f.name as field_name,
        f.type_fqn as field_type,
        r.injection_type as injection_type
    ORDER BY f.name
    LIMIT 10
""")

if result:
    print(f"  找到 {len(result)} 个注入字段:")
    for r in result:
        print(f"    {r['field_name']}: {r['field_type']} (@{r['injection_type']})")
else:
    print("  [ERROR] 未找到 HAS_FIELD 关系")

# 4. 检查 openNoble 方法的 CALLS 关系
print("\n4. 检查 openNoble 方法的 CALLS 关系:")
result = storage.execute_query("""
    MATCH (c:CLASS)-[:DECLARES]->(m:Method)
    WHERE c.fqn = 'com.yupaopao.chatroom.controller.NobleController'
      AND m.name = 'openNoble'
    OPTIONAL MATCH (m)-[:CALLS]->(called:Method)
    OPTIONAL MATCH (called_class)-[:DECLARES]->(called)
    RETURN 
        m.signature as method_sig,
        count(called) as calls_count,
        collect(DISTINCT called_class.fqn + '.' + called.name)[0..5] as sample_calls
""")

if result:
    for r in result:
        print(f"  方法: {r['method_sig']}")
        print(f"  CALLS 关系数量: {r['calls_count']}")
        if r['calls_count'] > 0:
            print(f"  调用示例:")
            for call in r['sample_calls']:
                if call and call != '.':
                    print(f"    - {call}")
else:
    print("  [ERROR] 未找到方法")

# 5. 检查是否还有错误的 Internal 调用（调用 Java 标准库方法）
print("\n5. 检查是否还有错误的 Internal 调用:")
result = storage.execute_query("""
    MATCH (m:Method)-[r:CALLS]->(called:Method)
    WHERE r.call_type = 'Internal'
      AND (called.name IN ['stream', 'collect', 'equals', 'orElse', 'findFirst'])
    RETURN count(r) as count
""")
print(f"  错误的 Internal 调用: {result[0]['count']} 个")

# 6. 统计 arch_layer 分布
print("\n6. 统计 arch_layer 分布 (yuer-chatroom-service):")
result = storage.execute_query("""
    MATCH (p:Project {name: 'yuer-chatroom-service'})-[:CONTAINS]->(c)
    WHERE c:CLASS OR c:MAPPER
    RETURN 
        c.arch_layer as layer,
        count(c) as count
    ORDER BY count DESC
""")

if result:
    for r in result:
        print(f"  {r['layer'] or 'None'}: {r['count']} 个")

print("\n" + "=" * 100)
print("验证完成")
print("=" * 100)
