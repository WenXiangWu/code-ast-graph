#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理所有错误的 INTERFACE 占位符节点"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("清理所有错误的 INTERFACE 占位符节点")
print("=" * 100)

# 策略：删除所有 is_external=true 且同名存在真实 INTERFACE 节点的占位符
print("\n1. 查找需要清理的占位符:")
result = storage.execute_query("""
    MATCH (placeholder:INTERFACE {is_external: true})
    WHERE NOT EXISTS {
        MATCH (p:Project)-[:CONTAINS]->(placeholder)
    }
    MATCH (real:INTERFACE)
    WHERE real.name = placeholder.name
      AND real.fqn <> placeholder.fqn
      AND EXISTS {
          MATCH (p:Project)-[:CONTAINS]->(real)
      }
    RETURN 
        placeholder.fqn as placeholder_fqn,
        real.fqn as real_fqn,
        placeholder.name as name
""")

if result:
    print(f"  找到 {len(result)} 个需要清理的占位符:")
    
    # 按名称分组
    by_name = {}
    for r in result:
        name = r['name']
        if name not in by_name:
            by_name[name] = []
        by_name[name].append(r)
    
    for name, items in sorted(by_name.items()):
        print(f"\n  {name}:")
        for item in items:
            print(f"    占位符: {item['placeholder_fqn']}")
            print(f"    真实接口: {item['real_fqn']}")
else:
    print("  未找到需要清理的占位符")
    print("\n" + "=" * 100)
    sys.exit(0)

# 2. 删除这些占位符
print(f"\n2. 删除错误的占位符:")
result = storage.execute_query("""
    MATCH (placeholder:INTERFACE {is_external: true})
    WHERE NOT EXISTS {
        MATCH (p:Project)-[:CONTAINS]->(placeholder)
    }
    MATCH (real:INTERFACE)
    WHERE real.name = placeholder.name
      AND real.fqn <> placeholder.fqn
      AND EXISTS {
          MATCH (p:Project)-[:CONTAINS]->(real)
      }
    WITH placeholder
    DETACH DELETE placeholder
    RETURN count(*) as deleted_count
""")

if result:
    deleted_count = result[0]['deleted_count']
    print(f"  ✓ 已删除 {deleted_count} 个占位符节点")
else:
    print(f"  未删除任何节点")

# 3. 统计剩余的 Unknown INTERFACE 节点
print(f"\n3. 统计剩余的 Unknown INTERFACE 节点:")
result = storage.execute_query("""
    MATCH (i:INTERFACE)
    WHERE NOT EXISTS {
        MATCH (p:Project)-[:CONTAINS]->(i)
    }
    RETURN count(*) as count
""")

if result:
    count = result[0]['count']
    print(f"  剩余 Unknown INTERFACE 节点: {count}")
    
    # 列出前 20 个
    result = storage.execute_query("""
        MATCH (i:INTERFACE)
        WHERE NOT EXISTS {
            MATCH (p:Project)-[:CONTAINS]->(i)
        }
        RETURN i.fqn as fqn, i.is_external as is_external
        ORDER BY i.fqn
        LIMIT 20
    """)
    
    if result:
        print(f"\n  前 20 个 Unknown INTERFACE:")
        for r in result:
            external_flag = " (external)" if r['is_external'] else ""
            print(f"    - {r['fqn']}{external_flag}")

print("\n" + "=" * 100)
print("清理完成！")
print("=" * 100)
