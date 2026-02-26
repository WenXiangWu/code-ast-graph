#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 NobleManager 的字段类型推断"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 NobleManager 的字段类型推断")
print("=" * 100)

# 1. 查找 NobleManager 的所有字段
print("\n1. NobleManager 的所有注入字段:")
result = storage.execute_query("""
    MATCH (c:CLASS {fqn: 'com.yupaopao.chatroom.manager.NobleManager'})-[r:HAS_FIELD]->(f:Field)
    RETURN 
        f.name as field_name,
        r.type_fqn as type_fqn,
        r.injection_type as injection_type
    ORDER BY f.name
""")

if result:
    print(f"  找到 {len(result)} 个注入字段:")
    for r in result:
        print(f"    {r['field_name']}: {r['type_fqn']} ({r['injection_type']})")
else:
    print("  未找到注入字段")

# 2. 检查 nobleMessageSendManager 字段的类型
print("\n2. nobleMessageSendManager 字段的类型推断:")
result = storage.execute_query("""
    MATCH (c:CLASS {fqn: 'com.yupaopao.chatroom.manager.NobleManager'})-[r:HAS_FIELD]->(f:Field {name: 'nobleMessageSendManager'})
    RETURN 
        f.name as field_name,
        r.type_fqn as type_fqn,
        r.injection_type as injection_type
""")

if result:
    r = result[0]
    print(f"  字段名: {r['field_name']}")
    print(f"  类型: {r['type_fqn']}")
    print(f"  注入类型: {r['injection_type']}")
    
    # 检查这个类型是否存在
    print(f"\n  检查类型是否存在:")
    check_result = storage.execute_query("""
        MATCH (c)
        WHERE c.fqn = $fqn
        OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
        RETURN 
            c.fqn as fqn,
            labels(c) as labels,
            p.name as project
    """, {'fqn': r['type_fqn']})
    
    if check_result:
        for cr in check_result:
            print(f"    FQN: {cr['fqn']}")
            print(f"    类型: {cr['labels'][0]}")
            print(f"    项目: {cr['project'] or 'Unknown'}")
    else:
        print(f"    [ERROR] 类型不存在: {r['type_fqn']}")
else:
    print("  未找到该字段")

# 3. 检查调用关系
print("\n3. 检查 NobleManager 调用 NobleMessageSendManager 的方法:")
result = storage.execute_query("""
    MATCH (caller:Method)-[:CALLS]->(called:Method)
    MATCH (caller_class:CLASS {fqn: 'com.yupaopao.chatroom.manager.NobleManager'})-[:DECLARES]->(caller)
    MATCH (called_class)-[:DECLARES]->(called)
    WHERE called_class.name = 'NobleMessageSendManager'
    RETURN 
        caller.name as caller_method,
        called_class.fqn as called_class_fqn,
        labels(called_class) as called_class_type,
        called.name as called_method
    LIMIT 5
""")

if result:
    print(f"  找到 {len(result)} 个调用:")
    for r in result:
        print(f"    {r['caller_method']} -> {r['called_class_fqn']}.{r['called_method']} ({r['called_class_type'][0]})")
else:
    print("  未找到调用")

print("\n" + "=" * 100)
