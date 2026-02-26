#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 NobleManager.changeNobleInfo 的 DB 调用"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 NobleManager.changeNobleInfo 的 DB 调用")
print("=" * 100)

# 1. 查找 changeNobleInfo 方法
print("\n1. 查找 changeNobleInfo 方法:")
result = storage.execute_query("""
    MATCH (c:CLASS {name: 'NobleManager'})-[:DECLARES]->(m:Method)
    WHERE m.name = 'changeNobleInfo'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN 
        p.name as project,
        c.fqn as class_fqn,
        m.signature as signature
""")

if result:
    for r in result:
        print(f"  项目: {r['project']}")
        print(f"  类: {r['class_fqn']}")
        print(f"  签名: {r['signature']}")
        
        # 2. 检查该方法的 DB_CALL 关系
        print(f"\n2. 检查该方法的 DB_CALL 关系:")
        db_result = storage.execute_query("""
            MATCH (m:Method {signature: $sig})-[r:DB_CALL]->(mapper_method:Method)
            MATCH (mapper:MAPPER)-[:DECLARES]->(mapper_method)
            RETURN 
                mapper.name as mapper_name,
                mapper_method.name as mapper_method_name
        """, {'sig': r['signature']})
        
        if db_result:
            print(f"  找到 {len(db_result)} 个 DB_CALL:")
            for dr in db_result:
                print(f"    {dr['mapper_name']}.{dr['mapper_method_name']}")
        else:
            print("  未找到 DB_CALL 关系")
        
        # 3. 检查通过 CALLS 链到 Mapper 的路径
        print(f"\n3. 检查通过 CALLS 链到 Mapper 的路径 (深度 1-3):")
        calls_result = storage.execute_query("""
            MATCH path = (m:Method {signature: $sig})-[:CALLS*1..3]->(mapper_method:Method)
            MATCH (mapper:MAPPER)-[:DECLARES]->(mapper_method)
            RETURN 
                mapper.name as mapper_name,
                mapper_method.name as mapper_method_name,
                length(path) as depth
            LIMIT 10
        """, {'sig': r['signature']})
        
        if calls_result:
            print(f"  找到 {len(calls_result)} 条路径:")
            for cr in calls_result:
                print(f"    深度 {cr['depth']}: {cr['mapper_name']}.{cr['mapper_method_name']}")
        else:
            print("  未找到路径")
        
        # 4. 检查该方法的所有 CALLS 关系
        print(f"\n4. 检查该方法的所有 CALLS 关系 (前 10 个):")
        all_calls = storage.execute_query("""
            MATCH (m:Method {signature: $sig})-[:CALLS]->(called:Method)
            MATCH (called_class)-[:DECLARES]->(called)
            RETURN 
                called_class.fqn as called_class,
                called.name as called_method,
                labels(called_class)[0] as class_type
            LIMIT 10
        """, {'sig': r['signature']})
        
        if all_calls:
            print(f"  找到 {len(all_calls)} 个 CALLS:")
            for ac in all_calls:
                print(f"    {ac['class_type']}: {ac['called_class']}.{ac['called_method']}")
        else:
            print("  未找到 CALLS 关系")

else:
    print("  未找到 changeNobleInfo 方法")

print("\n" + "=" * 100)
