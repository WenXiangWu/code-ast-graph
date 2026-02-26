#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试调用树中的 DB 调用"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

method_sig = "com.yupaopao.chatroom.controller.NobleController.openNoble(OpenNobleRequest)"

print("=" * 100)
print(f"测试方法的 DB 调用: {method_sig}")
print("=" * 100)

# 1. 测试 _build_call_tree 中的 DB 调用查询
print("\n1. 测试 _build_call_tree 中的 DB 调用查询:")
result = storage.execute_query("""
    MATCH (m:Method {signature: $method_sig})-[:CALLS|DB_CALL*1..3]->(mapper_method:Method)
    MATCH (mapper:MAPPER)-[:DECLARES]->(mapper_method)
    MATCH (mapper)-[:MAPS_TO]->(table)
    OPTIONAL MATCH (mapper_project:Project)-[:CONTAINS]->(mapper)
    RETURN DISTINCT
        mapper_project.name as mapper_project,
        mapper.fqn as mapper_fqn,
        mapper.name as mapper_name,
        table.name as table_name
    LIMIT 5
""", {'method_sig': method_sig})

if result:
    print(f"  找到 {len(result)} 个 DB 调用:")
    for r in result:
        print(f"    表: {r['table_name']}")
        print(f"    Mapper: {r['mapper_name']}")
        print(f"    项目: {r['mapper_project']}")
        print()
else:
    print("  未找到 DB 调用")

# 2. 检查是否有 MAPS_TO 关系
print("\n2. 检查 Mapper 的 MAPS_TO 关系:")
result = storage.execute_query("""
    MATCH (mapper:MAPPER)-[:MAPS_TO]->(table)
    WHERE mapper.name = 'NobleRecordMapper'
    RETURN 
        mapper.fqn as mapper_fqn,
        table.name as table_name
""")

if result:
    print(f"  找到 {len(result)} 个 MAPS_TO 关系:")
    for r in result:
        print(f"    {r['mapper_fqn']} -> {r['table_name']}")
else:
    print("  未找到 MAPS_TO 关系")

# 3. 检查 NobleRecordMapper 的关系类型
print("\n3. 检查 NobleRecordMapper 的所有关系:")
result = storage.execute_query("""
    MATCH (mapper:MAPPER {name: 'NobleRecordMapper'})-[r]->(target)
    RETURN 
        type(r) as rel_type,
        labels(target)[0] as target_type,
        target.name as target_name
    LIMIT 10
""")

if result:
    print(f"  找到 {len(result)} 个关系:")
    for r in result:
        print(f"    -{r['rel_type']}-> {r['target_type']}: {r['target_name']}")
else:
    print("  未找到关系")

# 4. 检查 openNoble 到 NobleRecordMapper 的路径
print("\n4. 检查 openNoble 到 NobleRecordMapper 的路径:")
result = storage.execute_query("""
    MATCH path = (m:Method {signature: $method_sig})-[:CALLS|DB_CALL*1..5]->(mapper_method:Method)
    MATCH (mapper:MAPPER {name: 'NobleRecordMapper'})-[:DECLARES]->(mapper_method)
    RETURN 
        [node in nodes(path) | node.name] as path_nodes,
        [rel in relationships(path) | type(rel)] as path_rels
    LIMIT 3
""", {'method_sig': method_sig})

if result:
    print(f"  找到 {len(result)} 条路径:")
    for r in result:
        print(f"    路径: {' -> '.join(r['path_nodes'])}")
        print(f"    关系: {' -> '.join(r['path_rels'])}")
        print()
else:
    print("  未找到路径")

print("\n" + "=" * 100)
