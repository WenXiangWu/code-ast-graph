#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追踪调用树中的 Dubbo 调用"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("追踪调用树中的 Dubbo 调用")
print("=" * 100)

# 1. 查找从 NobleController.openNoble 到 Dubbo 调用的路径
print("\n1. 查找从 NobleController.openNoble 到 Dubbo 调用的路径:")
result = storage.execute_query("""
    MATCH (root:Method)<-[:DECLARES]-(root_class)
    WHERE root_class.fqn = 'com.yupaopao.chatroom.controller.NobleController' 
      AND root.name = 'openNoble'
    
    MATCH path = (root)-[:CALLS*1..5]->(caller:Method)-[:DUBBO_CALLS]->(target:Method)
    MATCH (caller_class)-[:DECLARES]->(caller)
    MATCH (target_class)-[:DECLARES]->(target)
    
    RETURN 
        [n IN nodes(path) | n.name] as call_path,
        caller_class.fqn as caller_class,
        caller.name as caller_method,
        target_class.fqn as target_class,
        target.name as target_method,
        length(path) as depth
    ORDER BY depth
    LIMIT 5
""")

if result:
    print(f"  找到 {len(result)} 条路径:")
    for r in result:
        print(f"\n    深度 {r['depth']}:")
        print(f"    路径: {' -> '.join(r['call_path'])}")
        print(f"    Dubbo 调用: {r['caller_class']}.{r['caller_method']}")
        print(f"      -> {r['target_class']}.{r['target_method']}")
else:
    print("  未找到路径")

# 2. 检查 NobleManager.preLongNoble 的 Dubbo 调用
print("\n\n2. 检查 NobleManager.preLongNoble 的 Dubbo 调用:")
result = storage.execute_query("""
    MATCH (m:Method {name: 'preLongNoble'})-[:DUBBO_CALLS]->(target:Method)
    MATCH (caller_class)-[:DECLARES]->(m)
    MATCH (target_class)-[:DECLARES]->(target)
    RETURN 
        caller_class.fqn as caller_class,
        target_class.fqn as target_class,
        target.name as target_method,
        target.signature as target_signature
""")

if result:
    for r in result:
        print(f"  {r['caller_class']}.preLongNoble")
        print(f"    -> {r['target_class']}.{r['target_method']}")
        print(f"    签名: {r['target_signature']}")
        print()
else:
    print("  未找到")

# 3. 检查 MembershipBizService 的实现类
print("\n3. 检查 MembershipBizService 的实现类:")
result = storage.execute_query("""
    MATCH (iface:INTERFACE {name: 'MembershipBizService'})<-[:IMPLEMENTS]-(impl)
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(impl)
    RETURN 
        iface.fqn as interface_fqn,
        impl.fqn as impl_fqn,
        p.name as project
""")

if result:
    print(f"  找到 {len(result)} 个实现类:")
    for r in result:
        print(f"    接口: {r['interface_fqn']}")
        print(f"    实现: {r['impl_fqn']}")
        print(f"    项目: {r['project'] or 'Unknown'}")
else:
    print("  未找到实现类（可能是外部服务）")

# 4. 检查调用树构建查询是否能找到这个 Dubbo 调用
print("\n\n4. 模拟调用树构建查询（检查 NobleManager.preLongNoble）:")
result = storage.execute_query("""
    MATCH (m:Method)-[:DUBBO_CALLS]->(dubbo_iface_method:Method)
    MATCH (dubbo_iface:INTERFACE)-[:DECLARES]->(dubbo_iface_method)
    MATCH (impl_class:CLASS)-[:IMPLEMENTS]->(dubbo_iface)
    MATCH (impl_class)-[:DECLARES]->(impl_method:Method)
    WHERE m.name = 'preLongNoble'
      AND impl_method.name = dubbo_iface_method.name
    OPTIONAL MATCH (impl_project:Project)-[:CONTAINS]->(impl_class)
    RETURN 
        dubbo_iface.fqn as dubbo_interface,
        dubbo_iface_method.name as dubbo_method,
        impl_method.signature as impl_signature,
        impl_project.name as impl_project,
        impl_class.fqn as impl_class_fqn
""")

if result:
    print(f"  查询成功，找到 {len(result)} 个结果:")
    for r in result:
        print(f"    Dubbo 接口: {r['dubbo_interface']}.{r['dubbo_method']}")
        print(f"    实现类: {r['impl_class_fqn']}")
        print(f"    项目: {r['impl_project'] or 'Unknown'}")
        print(f"    签名: {r['impl_signature']}")
else:
    print("  查询失败（这就是为什么调用树中没有 Dubbo 调用）")
    print("  原因：可能是实现类不在当前项目中，或者没有扫描到实现类")

print("\n" + "=" * 100)
