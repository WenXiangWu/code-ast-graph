#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 Dubbo 调用"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 Dubbo 调用")
print("=" * 100)

# 1. 检查 NobleController.openNoble 方法
print("\n1. 查找 NobleController.openNoble 方法:")
result = storage.execute_query("""
    MATCH (c)-[:DECLARES]->(m:Method)
    WHERE c.name = 'NobleController' AND m.name = 'openNoble'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN 
        p.name as project,
        c.fqn as class_fqn,
        m.signature as signature
""")

if result:
    for r in result:
        print(f"  项目: {r['project'] or 'Unknown'}")
        print(f"  类: {r['class_fqn']}")
        print(f"  签名: {r['signature']}")
        print()
else:
    print("  未找到")

# 2. 检查该方法的直接 Dubbo 调用
print("\n2. 检查 NobleController.openNoble 的直接 Dubbo 调用:")
result = storage.execute_query("""
    MATCH (caller:Method)-[:DUBBO_CALLS]->(target:Method)
    MATCH (caller_class)-[:DECLARES]->(caller)
    MATCH (target_class)-[:DECLARES]->(target)
    WHERE caller_class.name = 'NobleController' AND caller.name = 'openNoble'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(target_class)
    RETURN 
        target_class.fqn as target_class,
        target.name as target_method,
        p.name as target_project,
        labels(target_class) as target_labels
""")

if result:
    print(f"  找到 {len(result)} 个 Dubbo 调用:")
    for r in result:
        print(f"    -> {r['target_class']}.{r['target_method']}")
        print(f"       项目: {r['target_project'] or 'Unknown'}")
        print(f"       类型: {r['target_labels'][0]}")
        print()
else:
    print("  未找到直接的 Dubbo 调用")

# 3. 检查该方法调用链中的 Dubbo 调用（递归查找）
print("\n3. 检查调用链中的 Dubbo 调用（深度 3）:")
result = storage.execute_query("""
    MATCH (root:Method)<-[:DECLARES]-(root_class)
    WHERE root_class.name = 'NobleController' AND root.name = 'openNoble'
    
    MATCH path = (root)-[:CALLS*0..3]->(caller:Method)-[:DUBBO_CALLS]->(target:Method)
    MATCH (caller_class)-[:DECLARES]->(caller)
    MATCH (target_class)-[:DECLARES]->(target)
    
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(target_class)
    
    RETURN DISTINCT
        caller_class.fqn as caller_class,
        caller.name as caller_method,
        target_class.fqn as target_class,
        target.name as target_method,
        p.name as target_project,
        labels(target_class) as target_labels,
        length(path) as depth
    ORDER BY depth
    LIMIT 10
""")

if result:
    print(f"  找到 {len(result)} 个 Dubbo 调用:")
    for r in result:
        print(f"    深度 {r['depth']}: {r['caller_class']}.{r['caller_method']}")
        print(f"      -> {r['target_class']}.{r['target_method']}")
        print(f"         项目: {r['target_project'] or 'Unknown'}")
        print(f"         类型: {r['target_labels'][0]}")
        print()
else:
    print("  未找到任何 Dubbo 调用")

# 4. 检查 NobleManager 是否有 Dubbo 调用
print("\n4. 检查 NobleManager 的 Dubbo 调用:")
result = storage.execute_query("""
    MATCH (caller:Method)-[:DUBBO_CALLS]->(target:Method)
    MATCH (caller_class {name: 'NobleManager'})-[:DECLARES]->(caller)
    MATCH (target_class)-[:DECLARES]->(target)
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(target_class)
    RETURN 
        caller.name as caller_method,
        target_class.fqn as target_class,
        target.name as target_method,
        p.name as target_project
    LIMIT 10
""")

if result:
    print(f"  找到 {len(result)} 个 Dubbo 调用:")
    for r in result:
        print(f"    {r['caller_method']} -> {r['target_class']}.{r['target_method']}")
        print(f"      项目: {r['target_project'] or 'Unknown'}")
        print()
else:
    print("  未找到 Dubbo 调用")

# 5. 统计所有 Dubbo 调用
print("\n5. 统计所有 DUBBO_CALLS 关系:")
result = storage.execute_query("""
    MATCH (caller:Method)-[:DUBBO_CALLS]->(target:Method)
    MATCH (caller_class)-[:DECLARES]->(caller)
    MATCH (target_class)-[:DECLARES]->(target)
    OPTIONAL MATCH (p1:Project)-[:CONTAINS]->(caller_class)
    OPTIONAL MATCH (p2:Project)-[:CONTAINS]->(target_class)
    RETURN 
        p1.name as caller_project,
        count(*) as count
    ORDER BY count DESC
""")

if result:
    print(f"  按项目统计:")
    for r in result:
        print(f"    {r['caller_project'] or 'Unknown'}: {r['count']} 个")
else:
    print("  未找到任何 DUBBO_CALLS 关系")

# 6. 检查 NobleController 的注入字段
print("\n6. 检查 NobleController 的注入字段（可能包含 Dubbo 服务）:")
result = storage.execute_query("""
    MATCH (c {name: 'NobleController'})-[r:HAS_FIELD]->(f:Field)
    WHERE r.injection_type = 'Reference'
    RETURN 
        f.name as field_name,
        r.type_fqn as type_fqn
""")

if result:
    print(f"  找到 {len(result)} 个 @Reference 字段:")
    for r in result:
        print(f"    {r['field_name']}: {r['type_fqn']}")
else:
    print("  未找到 @Reference 字段")

print("\n" + "=" * 100)
