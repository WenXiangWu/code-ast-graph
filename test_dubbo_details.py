#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 Dubbo 调用详情"""
import sys
import io
import requests
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 100)
print("测试 Dubbo 调用详情")
print("=" * 100)

# 查询 NobleController.openNoble
print("\n查询 NobleController.openNoble 的调用树:")
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
        call_tree = data.get('call_tree', {})
        
        # 递归查找所有 dubbo_call 节点
        def find_dubbo_calls(node, path="", depth=0):
            dubbo_calls = []
            current_path = f"{path}/{node.get('class_name', 'N/A')}.{node.get('method_name', 'N/A')}"
            
            if node.get('node_type') == 'dubbo_call':
                dubbo_calls.append({
                    'path': current_path,
                    'node': node,
                    'depth': depth
                })
            
            for child in node.get('children', []):
                dubbo_calls.extend(find_dubbo_calls(child, current_path, depth + 1))
            
            return dubbo_calls
        
        dubbo_calls = find_dubbo_calls(call_tree)
        
        print(f"\n找到 {len(dubbo_calls)} 个 Dubbo 调用:")
        for i, item in enumerate(dubbo_calls, 1):
            node = item['node']
            print(f"\n{i}. Dubbo 调用 (深度 {item['depth']}):")
            print(f"   项目: {node.get('project', 'N/A')}")
            print(f"   接口: {node.get('dubbo_interface', 'N/A')}")
            print(f"   方法: {node.get('dubbo_method', 'N/A')}")
            print(f"   通过字段: {node.get('via_field', 'N/A')}")
            print(f"   实现类: {node.get('class_fqn', 'N/A')}")
            print(f"   路径: {item['path']}")
            
            # 检查是否有子节点
            children_count = len(node.get('children', []))
            if children_count > 0:
                print(f"   子节点数: {children_count}")
    else:
        print(f"✗ 查询失败: {response.status_code}")
        print(f"  响应: {response.text}")
except Exception as e:
    print(f"✗ 请求失败: {e}")

print("\n" + "=" * 100)
