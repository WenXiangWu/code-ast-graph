#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理错误的 INTERFACE 占位符节点（因类型推断错误产生的）"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("清理错误的 INTERFACE 占位符节点")
print("=" * 100)

# 1. 统计需要清理的节点
print("\n1. 统计需要清理的 INTERFACE 占位符节点:")
print("   条件: is_external=true 且存在同名的 CLASS 或 MAPPER 节点")

result = storage.execute_query("""
    MATCH (iface:INTERFACE {is_external: true})
    WHERE NOT EXISTS {
        MATCH (p:Project)-[:CONTAINS]->(iface)
    }
    MATCH (real_class)
    WHERE (real_class:CLASS OR real_class:MAPPER)
      AND real_class.name = iface.name
      AND real_class.fqn <> iface.fqn
    RETURN 
        iface.fqn as interface_fqn,
        real_class.fqn as class_fqn,
        labels(real_class) as class_type
""")

if result:
    print(f"   找到 {len(result)} 个错误的占位符节点:")
    for r in result[:10]:  # 只显示前 10 个
        print(f"     - INTERFACE: {r['interface_fqn']}")
        print(f"       真实类: {r['class_fqn']} ({r['class_type'][0]})")
    if len(result) > 10:
        print(f"     ... 还有 {len(result) - 10} 个")
else:
    print("   未找到需要清理的节点")

# 2. 特别检查 NobleMessageSendManager
print("\n2. 检查 NobleMessageSendManager 的情况:")
result = storage.execute_query("""
    MATCH (n)
    WHERE n.name = 'NobleMessageSendManager'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(n)
    RETURN 
        n.fqn as fqn,
        labels(n) as labels,
        p.name as project,
        n.is_external as is_external
""")

if result:
    for r in result:
        print(f"   FQN: {r['fqn']}")
        print(f"   类型: {r['labels'][0]}")
        print(f"   项目: {r['project'] or 'Unknown'}")
        print(f"   is_external: {r['is_external']}")
        print()

# 3. 删除错误的 INTERFACE 占位符
print("\n3. 删除错误的 INTERFACE 占位符节点:")
print("   删除 com.yupaopao.chatroom.service.intf.NobleMessageSendManager ...")

result = storage.execute_query("""
    MATCH (iface:INTERFACE {fqn: 'com.yupaopao.chatroom.service.intf.NobleMessageSendManager'})
    WHERE iface.is_external = true
    DETACH DELETE iface
    RETURN count(*) as deleted_count
""")

if result:
    print(f"   已删除 {result[0]['deleted_count']} 个节点")

# 4. 验证删除结果
print("\n4. 验证删除结果:")
result = storage.execute_query("""
    MATCH (n)
    WHERE n.name = 'NobleMessageSendManager'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(n)
    RETURN 
        n.fqn as fqn,
        labels(n) as labels,
        p.name as project
""")

if result:
    print(f"   剩余 {len(result)} 个 NobleMessageSendManager 节点:")
    for r in result:
        print(f"     - {r['fqn']} ({r['labels'][0]}) - 项目: {r['project'] or 'Unknown'}")
else:
    print("   未找到 NobleMessageSendManager 节点")

# 5. 统计所有 Unknown INTERFACE 节点
print("\n5. 统计所有 Unknown INTERFACE 节点:")
result = storage.execute_query("""
    MATCH (i:INTERFACE)
    WHERE NOT EXISTS {
        MATCH (p:Project)-[:CONTAINS]->(i)
    }
    RETURN count(*) as count
""")

if result:
    print(f"   Unknown INTERFACE 节点数量: {result[0]['count']}")

print("\n" + "=" * 100)
print("清理完成！")
print("=" * 100)
