#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 NobleController.openNoble 的数据库调用"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

method_sig = "yuer-chatroom-service.com.yupaopao.chatroom.controller.NobleController.openNoble(Long,Long)"

print("=" * 100)
print(f"检查方法的数据库调用: {method_sig}")
print("=" * 100)

# 1. 检查直接的 DB_CALL 关系
print("\n1. 检查直接的 DB_CALL 关系:")
result = storage.execute_query("""
    MATCH (m:Method {signature: $method_sig})-[r:DB_CALL]->(mapper_method:Method)
    MATCH (mapper:MAPPER)-[:DECLARES]->(mapper_method)
    RETURN 
        mapper.fqn as mapper_fqn,
        mapper_method.name as mapper_method_name,
        r.table_name as table_name
""", {'method_sig': method_sig})

if result:
    print(f"  找到 {len(result)} 个直接 DB_CALL:")
    for r in result:
        print(f"    Mapper: {r['mapper_fqn']}")
        print(f"    方法: {r['mapper_method_name']}")
        print(f"    表: {r['table_name']}")
        print()
else:
    print("  未找到直接的 DB_CALL 关系")

# 2. 检查通过 CALLS 链到 Mapper 的路径
print("\n2. 检查通过 CALLS 链到 Mapper 的路径:")
result = storage.execute_query("""
    MATCH (m:Method {signature: $method_sig})-[:CALLS*1..3]->(mapper_method:Method)
    MATCH (mapper:MAPPER)-[:DECLARES]->(mapper_method)
    OPTIONAL MATCH (mapper)-[:MAPS_TO]->(table)
    RETURN 
        mapper.fqn as mapper_fqn,
        mapper_method.name as mapper_method_name,
        table.name as table_name
    LIMIT 10
""", {'method_sig': method_sig})

if result:
    print(f"  找到 {len(result)} 个通过 CALLS 链的 Mapper 调用:")
    for r in result:
        print(f"    Mapper: {r['mapper_fqn']}")
        print(f"    方法: {r['mapper_method_name']}")
        print(f"    表: {r['table_name']}")
        print()
else:
    print("  未找到通过 CALLS 链的 Mapper 调用")

# 3. 检查方法的所有直接调用
print("\n3. 检查方法的所有直接调用:")
result = storage.execute_query("""
    MATCH (m:Method {signature: $method_sig})-[:CALLS]->(called_method:Method)
    MATCH (called_class)-[:DECLARES]->(called_method)
    RETURN 
        called_class.fqn as called_class_fqn,
        called_method.name as called_method_name,
        labels(called_class) as labels
    LIMIT 20
""", {'method_sig': method_sig})

if result:
    print(f"  找到 {len(result)} 个直接调用:")
    for r in result:
        print(f"    类: {r['called_class_fqn']} ({r['labels'][0]})")
        print(f"    方法: {r['called_method_name']}")
        print()
else:
    print("  未找到直接调用")

# 4. 检查是否有 MAPPER 节点
print("\n4. 检查项目中的 MAPPER 节点:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'yuer-chatroom-service'})-[:CONTAINS]->(mapper:MAPPER)
    RETURN mapper.fqn as mapper_fqn, mapper.name as mapper_name
    LIMIT 10
""")

if result:
    print(f"  找到 {len(result)} 个 Mapper:")
    for r in result:
        print(f"    {r['mapper_fqn']}")
else:
    print("  未找到 MAPPER 节点")

# 5. 检查是否有 CLASS 标签的 Mapper
print("\n5. 检查是否有 CLASS 标签的 Mapper (名字包含 Mapper):")
result = storage.execute_query("""
    MATCH (p:Project {name: 'yuer-chatroom-service'})-[:CONTAINS]->(c:CLASS)
    WHERE c.name ENDS WITH 'Mapper'
    RETURN c.fqn as class_fqn, c.name as class_name, labels(c) as labels
    LIMIT 10
""")

if result:
    print(f"  找到 {len(result)} 个 CLASS 标签的 Mapper:")
    for r in result:
        print(f"    {r['class_fqn']} - 标签: {r['labels']}")
else:
    print("  未找到 CLASS 标签的 Mapper")

print("\n" + "=" * 100)
