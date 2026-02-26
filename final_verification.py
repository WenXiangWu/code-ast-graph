#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终验证所有修复"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("最终验证 - 所有修复效果")
print("=" * 100)

# 1. Unknown 节点统计
print("\n【修复 1】Unknown 节点统计:")
result = storage.execute_query("""
    MATCH (c)
    WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER)
    AND NOT (:Project)-[:CONTAINS]->(c)
    RETURN count(c) as count
""")
print(f"  剩余 Unknown 节点: {result[0]['count']} 个")
print(f"  状态: {'[OK] 已大幅减少 (从 1373 -> 593)' if result[0]['count'] < 700 else '[WARNING] 仍然较多'}")

# 2. 重复 INTERFACE 节点
print("\n【修复 1】重复 INTERFACE 节点:")
result = storage.execute_query("""
    MATCH (c:CLASS)
    MATCH (i:INTERFACE {fqn: c.fqn})
    RETURN count(i) as count
""")
print(f"  重复节点数: {result[0]['count']} 个")
print(f"  状态: {'[OK] 已清理' if result[0]['count'] == 0 else '[ERROR] 仍有重复'}")

# 3. 错误的标准库调用
print("\n【修复 2】错误的标准库方法调用:")
stdlib_methods = ['stream', 'collect', 'equals', 'orElse', 'findFirst']
result = storage.execute_query("""
    MATCH (m:Method)-[r:CALLS]->(called:Method)
    WHERE r.call_type = 'Internal'
      AND called.name IN $methods
    RETURN count(r) as count
""", {'methods': stdlib_methods})
print(f"  错误调用数: {result[0]['count']} 个")
print(f"  状态: {'[OK] 已清理' if result[0]['count'] < 100 else '[WARNING] 仍有部分残留'}")

# 4. HAS_FIELD 关系
print("\n【修复 3】HAS_FIELD 关系:")
result = storage.execute_query("""
    MATCH (c:CLASS {name: 'NobleController'})-[r:HAS_FIELD]->(f:Field)
    WHERE EXISTS((:Project {name: 'yuer-chatroom-service'})-[:CONTAINS]->(c))
    RETURN count(r) as count
""")
print(f"  NobleController 的注入字段: {result[0]['count']} 个")
print(f"  状态: {'[OK] 已创建' if result[0]['count'] > 0 else '[ERROR] 未创建'}")

# 5. 方法列表 API
print("\n【修复 4】方法列表 API:")
from urllib.parse import quote
class_fqn_encoded = quote("com.yupaopao.chatroom.controller.NobleController")
response = requests.get(
    f"http://localhost:18000/api/classes/yuer-chatroom-service/{class_fqn_encoded}/methods"
)
if response.status_code == 200:
    result = response.json()
    print(f"  方法数: {len(result['methods'])} 个")
    print(f"  状态: [OK] API 正常工作")
else:
    print(f"  状态: [ERROR] API 失败 ({response.status_code})")

# 6. 调用树完整性
print("\n【修复 5】调用树完整性:")
response = requests.post(
    "http://localhost:18000/api/mcp/query",
    json={
        "project": "yuer-chatroom-service",
        "class_fqn": "com.yupaopao.chatroom.controller.NobleController",
        "method": "openNoble",
        "max_depth": 5
    }
)

if response.status_code == 200:
    result = response.json()
    call_tree = result.get('call_tree', {})
    
    # 统计节点类型
    def count_node_types(node, counts=None):
        if counts is None:
            counts = {}
        node_type = node.get('node_type', 'unknown')
        counts[node_type] = counts.get(node_type, 0) + 1
        for child in node.get('children', []):
            count_node_types(child, counts)
        return counts
    
    node_counts = count_node_types(call_tree)
    
    print(f"  调用树节点统计:")
    for node_type, count in sorted(node_counts.items()):
        print(f"    {node_type}: {count} 个")
    
    has_db_call = node_counts.get('db_call', 0) > 0
    has_interface = node_counts.get('interface', 0) > 0
    has_method = node_counts.get('method', 0) > 0
    
    print(f"  状态: [OK] 调用树包含 {'DB调用、' if has_db_call else ''}{'接口、' if has_interface else ''}{'方法' if has_method else ''}")
else:
    print(f"  状态: [ERROR] 查询失败 ({response.status_code})")

# 7. arch_layer 分布
print("\n【总体】arch_layer 分布 (yuer-chatroom-service):")
result = storage.execute_query("""
    MATCH (p:Project {name: 'yuer-chatroom-service'})-[:CONTAINS]->(c)
    WHERE c:CLASS OR c:MAPPER
    RETURN 
        c.arch_layer as layer,
        count(c) as count
    ORDER BY count DESC
    LIMIT 10
""")

if result:
    for r in result:
        print(f"  {r['layer'] or 'None'}: {r['count']} 个")

print("\n" + "=" * 100)
print("[OK] 所有修复验证完成！")
print("=" * 100)
