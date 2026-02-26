#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 NobleMessageSendManager 的两个节点"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 NobleMessageSendManager 的两个节点")
print("=" * 100)

# 1. 查找所有 NobleMessageSendManager 节点
print("\n1. 所有 NobleMessageSendManager 节点:")
result = storage.execute_query("""
    MATCH (c)
    WHERE c.name = 'NobleMessageSendManager'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN 
        p.name as project,
        c.fqn as fqn,
        labels(c) as labels,
        c.is_external as is_external,
        c.file_path as file_path
""")

if result:
    for r in result:
        print(f"  FQN: {r['fqn']}")
        print(f"  类型: {r['labels'][0]}")
        print(f"  项目: {r['project'] or 'Unknown'}")
        print(f"  is_external: {r['is_external']}")
        print(f"  文件: {r['file_path']}")
        print()
else:
    print("  未找到")

# 2. 检查谁实现了 service.intf.NobleMessageSendManager
print("\n2. 检查谁实现了 service.intf.NobleMessageSendManager:")
result = storage.execute_query("""
    MATCH (impl)-[:IMPLEMENTS]->(iface)
    WHERE iface.fqn = 'com.yupaopao.chatroom.service.intf.NobleMessageSendManager'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(impl)
    RETURN 
        p.name as project,
        impl.fqn as impl_fqn,
        labels(impl) as labels
""")

if result:
    print(f"  找到 {len(result)} 个实现:")
    for r in result:
        print(f"    {r['impl_fqn']} ({r['labels'][0]})")
        print(f"    项目: {r['project'] or 'Unknown'}")
        print()
else:
    print("  没有类实现这个接口")

# 3. 检查 manager.NobleMessageSendManager 实现了什么
print("\n3. 检查 manager.NobleMessageSendManager 实现了什么:")
result = storage.execute_query("""
    MATCH (c)-[:IMPLEMENTS]->(iface)
    WHERE c.fqn = 'com.yupaopao.chatroom.manager.NobleMessageSendManager'
    RETURN 
        iface.fqn as interface_fqn,
        labels(iface) as labels
""")

if result:
    print(f"  实现了 {len(result)} 个接口:")
    for r in result:
        print(f"    {r['interface_fqn']} ({r['labels'][0]})")
else:
    print("  没有实现任何接口")

# 4. 检查调用关系
print("\n4. 检查谁调用了 service.intf.NobleMessageSendManager:")
result = storage.execute_query("""
    MATCH (caller:Method)-[:CALLS]->(called:Method)
    MATCH (iface:INTERFACE {fqn: 'com.yupaopao.chatroom.service.intf.NobleMessageSendManager'})-[:DECLARES]->(called)
    MATCH (caller_class)-[:DECLARES]->(caller)
    RETURN 
        caller_class.fqn as caller_class,
        caller.name as caller_method,
        called.name as called_method
    LIMIT 5
""")

if result:
    print(f"  找到 {len(result)} 个调用:")
    for r in result:
        print(f"    {r['caller_class']}.{r['caller_method']} -> {r['called_method']}")
else:
    print("  没有调用")

print("\n" + "=" * 100)
