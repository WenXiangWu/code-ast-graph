#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查为什么接口显示为 Unknown"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查接口节点的项目关联")
print("=" * 100)

# 1. 检查 HomeShowCardService
print("\n1. 检查 HomeShowCardService:")
result = storage.execute_query("""
    MATCH (c)
    WHERE c.fqn = 'com.yupaopao.chatroom.service.intf.HomeShowCardService'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN 
        c.fqn as fqn,
        labels(c) as labels,
        p.name as project,
        c.arch_layer as arch_layer
""")

if result:
    for r in result:
        print(f"  FQN: {r['fqn']}")
        print(f"  标签: {r['labels']}")
        print(f"  项目: {r['project'] or 'Unknown'}")
        print(f"  架构层: {r['arch_layer']}")
        print()
else:
    print("  未找到")

# 2. 检查 NobleMessageSendManager
print("\n2. 检查 NobleMessageSendManager:")
result = storage.execute_query("""
    MATCH (c)
    WHERE c.fqn = 'com.yupaopao.chatroom.service.intf.NobleMessageSendManager'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN 
        c.fqn as fqn,
        labels(c) as labels,
        p.name as project,
        c.arch_layer as arch_layer
""")

if result:
    for r in result:
        print(f"  FQN: {r['fqn']}")
        print(f"  标签: {r['labels']}")
        print(f"  项目: {r['project'] or 'Unknown'}")
        print(f"  架构层: {r['arch_layer']}")
        print()
else:
    print("  未找到")

# 3. 检查这些接口的实现类
print("\n3. 检查 HomeShowCardService 的实现类:")
result = storage.execute_query("""
    MATCH (impl)-[:IMPLEMENTS]->(iface)
    WHERE iface.fqn = 'com.yupaopao.chatroom.service.intf.HomeShowCardService'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(impl)
    RETURN 
        p.name as project,
        impl.fqn as impl_fqn,
        labels(impl) as labels,
        impl.arch_layer as arch_layer
""")

if result:
    print(f"  找到 {len(result)} 个实现类:")
    for r in result:
        print(f"    项目: {r['project'] or 'Unknown'}")
        print(f"    类: {r['impl_fqn']}")
        print(f"    类型: {r['labels']}")
        print(f"    架构层: {r['arch_layer']}")
        print()
else:
    print("  未找到实现类")

# 4. 检查为什么接口没有项目关联
print("\n4. 检查为什么接口没有 CONTAINS 关系:")
print("  可能原因:")
print("    1. 接口是在 IMPLEMENTS 关系创建时自动生成的占位符")
print("    2. 接口所在的文件没有被扫描（被过滤掉了）")
print("    3. 接口在扫描时被识别为非业务类")

# 5. 检查接口文件是否存在
print("\n5. 检查接口是否在项目中:")
result = storage.execute_query("""
    MATCH (c)
    WHERE c.fqn = 'com.yupaopao.chatroom.service.intf.HomeShowCardService'
    RETURN 
        c.file_path as file_path,
        c.is_external as is_external
""")

if result:
    for r in result:
        print(f"  文件路径: {r['file_path']}")
        print(f"  is_external: {r['is_external']}")
else:
    print("  未找到文件信息")

# 6. 统计所有 INTERFACE 节点的项目关联情况
print("\n6. 统计 INTERFACE 节点的项目关联:")
result = storage.execute_query("""
    MATCH (i:INTERFACE)
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(i)
    WITH CASE WHEN p IS NULL THEN 'Unknown' ELSE p.name END as project_status
    RETURN project_status, count(*) as count
    ORDER BY count DESC
""")

if result:
    for r in result:
        print(f"  {r['project_status']}: {r['count']} 个")

print("\n" + "=" * 100)
