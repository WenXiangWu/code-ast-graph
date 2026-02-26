#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 NobleController 的注入字段和方法调用"""
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

class_fqn = "com.yupaopao.chatroom.controller.NobleController"

print("=" * 100)
print(f"检查类: {class_fqn}")
print("=" * 100)

# 1. 检查类的注入字段
print("\n1. 检查类的注入字段:")
result = storage.execute_query("""
    MATCH (c:CLASS {fqn: $class_fqn})-[:HAS_FIELD]->(f)
    RETURN 
        f.name as field_name,
        f.type_fqn as field_type,
        f.annotation as annotation
    ORDER BY f.name
""", {'class_fqn': class_fqn})

if result:
    print(f"  找到 {len(result)} 个字段:")
    for r in result:
        print(f"    {r['field_name']}: {r['field_type']} (@{r['annotation']})")
else:
    print("  未找到注入字段")

# 2. 检查 openNoble 方法
print("\n2. 检查 openNoble 方法:")
result = storage.execute_query("""
    MATCH (c:CLASS {fqn: $class_fqn})-[:DECLARES]->(m:Method)
    WHERE m.name = 'openNoble'
    RETURN 
        m.signature as signature,
        m.name as name,
        m.parameters as parameters
""", {'class_fqn': class_fqn})

if result:
    print(f"  找到 {len(result)} 个 openNoble 方法:")
    for r in result:
        print(f"    签名: {r['signature']}")
        print(f"    参数: {r['parameters']}")
        print()
else:
    print("  未找到 openNoble 方法")

# 3. 检查 openNoble 方法的 CALLS 关系
print("\n3. 检查 openNoble 方法的 CALLS 关系:")
result = storage.execute_query("""
    MATCH (c:CLASS {fqn: $class_fqn})-[:DECLARES]->(m:Method)
    WHERE m.name = 'openNoble'
    OPTIONAL MATCH (m)-[r:CALLS]->(called_method:Method)
    OPTIONAL MATCH (called_class)-[:DECLARES]->(called_method)
    RETURN 
        m.signature as method_sig,
        count(r) as calls_count,
        collect(called_class.fqn + '.' + called_method.name) as called_methods
""", {'class_fqn': class_fqn})

if result:
    for r in result:
        print(f"  方法: {r['method_sig']}")
        print(f"  CALLS 关系数量: {r['calls_count']}")
        if r['calls_count'] > 0:
            print(f"  调用的方法:")
            for cm in r['called_methods']:
                if cm != '.':  # 过滤空值
                    print(f"    - {cm}")
        else:
            print(f"  ❌ 没有 CALLS 关系！")
        print()

# 4. 检查项目中是否有 CALLS 关系
print("\n4. 检查项目中是否有 CALLS 关系:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'yuer-chatroom-service'})-[:CONTAINS]->(c:CLASS)-[:DECLARES]->(m:Method)
    WHERE EXISTS((m)-[:CALLS]->(:Method))
    RETURN count(DISTINCT m) as methods_with_calls
""")

if result:
    print(f"  项目中有 {result[0]['methods_with_calls']} 个方法有 CALLS 关系")
else:
    print("  项目中没有方法有 CALLS 关系")

# 5. 检查是否有 DB_CALL 关系
print("\n5. 检查项目中是否有 DB_CALL 关系:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'yuer-chatroom-service'})-[:CONTAINS]->(c:CLASS)-[:DECLARES]->(m:Method)
    WHERE EXISTS((m)-[:DB_CALL]->(:Method))
    RETURN count(DISTINCT m) as methods_with_db_calls
""")

if result:
    print(f"  项目中有 {result[0]['methods_with_db_calls']} 个方法有 DB_CALL 关系")
else:
    print("  项目中没有方法有 DB_CALL 关系")

print("\n" + "=" * 100)
