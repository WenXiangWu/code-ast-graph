#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 Dubbo 调用列表"""
import sys
import io
import requests
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 100)
print("测试 Dubbo 调用列表")
print("=" * 100)

# 查询 NobleController.openNoble
print("\n查询 NobleController.openNoble:")
try:
    response = requests.post(
        "http://localhost:18000/api/mcp/query",
        json={
            "project": "yuer-chatroom-service",
            "class_fqn": "com.yupaopao.chatroom.controller.NobleController",
            "method": "openNoble"
        },
        timeout=60
    )
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n✓ 查询成功")
        
        # 检查 dubbo_calls 列表
        dubbo_calls = data.get('dubbo_calls', [])
        print(f"\nDubbo 调用列表:")
        print(f"  数量: {len(dubbo_calls)}")
        
        if dubbo_calls:
            print(f"\n  详细列表:")
            for i, call in enumerate(dubbo_calls, 1):
                print(f"\n  {i}. Dubbo 调用:")
                print(f"     调用方项目: {call.get('caller_project', 'N/A')}")
                print(f"     调用方类: {call.get('caller_class', 'N/A')}")
                print(f"     调用方法: {call.get('caller_method', 'N/A')}")
                print(f"     目标接口: {call.get('dubbo_interface', 'N/A')}")
                print(f"     目标方法: {call.get('dubbo_method', 'N/A')}")
                print(f"     通过字段: {call.get('via_field', 'N/A')}")
                print(f"     目标项目: {call.get('target_project', 'N/A')}")
        else:
            print("  ⚠ 列表为空")
        
        # 检查调用树中的 dubbo_call 节点
        call_tree = data.get('call_tree', {})
        
        def count_dubbo_calls(node):
            count = 1 if node.get('node_type') == 'dubbo_call' else 0
            for child in node.get('children', []):
                count += count_dubbo_calls(child)
            return count
        
        tree_dubbo_count = count_dubbo_calls(call_tree)
        print(f"\n调用树中的 Dubbo 调用:")
        print(f"  数量: {tree_dubbo_count}")
        
        # 对比
        if len(dubbo_calls) != tree_dubbo_count:
            print(f"\n  ⚠ 注意: 列表和树中的数量不一致")
            print(f"     列表: {len(dubbo_calls)}")
            print(f"     树: {tree_dubbo_count}")
    else:
        print(f"✗ 查询失败: {response.status_code}")
        print(f"  响应: {response.text}")
except Exception as e:
    print(f"✗ 请求失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 100)
