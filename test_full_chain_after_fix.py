#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试修复后的完整调用链"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json

print("=" * 100)
print("测试修复后的完整调用链")
print("=" * 100)

# 1. 测试 yuer-chatroom-service.NobleController.openNoble
print("\n1. 查询 yuer-chatroom-service.NobleController.openNoble:")
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
    print(f"  [OK] 查询成功")
    print(f"  前端入口: {len(result.get('endpoints', []))} 个")
    print(f"  涉及类: {len(result.get('internal_classes', []))} 个")
    print(f"  Dubbo 调用: {len(result.get('dubbo_calls', []))} 个")
    print(f"  数据库表: {len(result.get('tables', []))} 个")
    print(f"  MQ: {len(result.get('mq_topics', []))} 个")
    print(f"  Aries Job: {len(result.get('aries_jobs', []))} 个")
    
    # 显示调用树
    if result.get('call_tree'):
        print(f"\n  调用树:")
        print(f"    根节点: {result['call_tree']['class_name']}.{result['call_tree']['method_name']}")
        print(f"    子节点数: {len(result['call_tree'].get('children', []))}")
        
        # 显示前 5 个子节点
        for i, child in enumerate(result['call_tree'].get('children', [])[:5], 1):
            print(f"      {i}. {child['node_type']}: {child.get('class_name', 'N/A')}")
    
    # 显示数据库表
    if result.get('tables'):
        print(f"\n  数据库表:")
        for table in result['tables'][:10]:
            print(f"    - {table['table_name']} (via {table['mapper_name']})")
    
    # 保存完整结果
    with open('test_result_after_fix.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n  完整结果已保存到: test_result_after_fix.json")
else:
    print(f"  [ERROR] 查询失败: {response.status_code}")
    print(f"  {response.text}")

# 2. 测试获取类方法列表 API
print("\n2. 测试获取类方法列表 API:")
from urllib.parse import quote
class_fqn_encoded = quote("com.yupaopao.chatroom.controller.NobleController")
response = requests.get(
    f"http://localhost:18000/api/classes/yuer-chatroom-service/{class_fqn_encoded}/methods"
)

if response.status_code == 200:
    result = response.json()
    print(f"  [OK] 查询成功")
    print(f"  类: {result['class_fqn']}")
    print(f"  方法数: {len(result['methods'])}")
    print(f"\n  方法列表 (前 10 个):")
    for method in result['methods'][:10]:
        print(f"    - {method['name']}")
else:
    print(f"  [ERROR] 查询失败: {response.status_code}")
    print(f"  {response.text}")

print("\n" + "=" * 100)
print("测试完成")
print("=" * 100)
