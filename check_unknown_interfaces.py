#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 Unknown 接口节点"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查 Unknown 接口节点")
print("=" * 100)

interfaces = [
    "HomeShowCardService",
    "NobleService",
    "RedisService"
]

for interface_name in interfaces:
    print(f"\n{'=' * 50}")
    print(f"检查 {interface_name}:")
    print(f"{'=' * 50}")
    
    # 1. 查找所有同名节点
    result = storage.execute_query("""
        MATCH (c)
        WHERE c.name = $name
        OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
        RETURN 
            c.fqn as fqn,
            labels(c) as labels,
            p.name as project,
            c.is_external as is_external,
            c.file_path as file_path
        ORDER BY c.fqn
    """, {'name': interface_name})
    
    if result:
        print(f"\n找到 {len(result)} 个节点:")
        for r in result:
            print(f"  FQN: {r['fqn']}")
            print(f"  类型: {r['labels'][0]}")
            print(f"  项目: {r['project'] or 'Unknown'}")
            print(f"  is_external: {r['is_external']}")
            print(f"  文件: {r['file_path'] or 'N/A'}")
            print()
    else:
        print(f"  未找到 {interface_name}")
    
    # 2. 查找实现类
    result = storage.execute_query("""
        MATCH (impl)-[:IMPLEMENTS]->(iface)
        WHERE iface.name = $name
        OPTIONAL MATCH (p:Project)-[:CONTAINS]->(impl)
        RETURN 
            iface.fqn as interface_fqn,
            impl.fqn as impl_fqn,
            p.name as project
    """, {'name': interface_name})
    
    if result:
        print(f"  实现类:")
        for r in result:
            print(f"    接口: {r['interface_fqn']}")
            print(f"    实现: {r['impl_fqn']}")
            print(f"    项目: {r['project'] or 'Unknown'}")
            print()

print("\n" + "=" * 100)
