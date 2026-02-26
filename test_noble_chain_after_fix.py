#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试修复后的 NobleController 调用链"""
import sys
import io
import requests
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 100)
print("测试修复后的 NobleController 调用链")
print("=" * 100)

# 查询 NobleController.openNoble
print("\n1. 查询 NobleController.openNoble 的调用链:")
try:
    response = requests.post(
        "http://localhost:18000/api/mcp/query",
        json={
            "project": "yuer-chatroom-service",
            "class_fqn": "com.yupaopao.chatroom.manager.NobleController",
            "method": "openNoble"
        },
        timeout=60
    )
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n✓ 查询成功")
        print(f"\n前端入口:")
        endpoints = data.get('endpoints', [])
        if endpoints:
            for ep in endpoints:
                print(f"  - {ep.get('method', 'N/A')} {ep.get('path', 'N/A')}")
                print(f"    类: {ep.get('class_fqn', 'N/A')}")
                print(f"    方法: {ep.get('method_name', 'N/A')}")
        else:
            print("  未找到前端入口")
        
        print(f"\n内部类:")
        internal_classes = data.get('internal_classes', [])
        print(f"  数量: {len(internal_classes)}")
        for cls in internal_classes[:5]:
            print(f"  - {cls.get('project', 'Unknown')}.{cls.get('class_name', 'N/A')} ({cls.get('arch_layer', 'N/A')})")
        if len(internal_classes) > 5:
            print(f"  ... 还有 {len(internal_classes) - 5} 个")
        
        print(f"\nDubbo 调用:")
        dubbo_calls = data.get('dubbo_calls', [])
        print(f"  数量: {len(dubbo_calls)}")
        for call in dubbo_calls:
            print(f"  - {call.get('target_service', 'N/A')}")
            print(f"    方法: {call.get('target_method', 'N/A')}")
        
        print(f"\n数据库表:")
        tables = data.get('tables', [])
        print(f"  数量: {len(tables)}")
        for table in tables:
            print(f"  - {table.get('table_name', 'N/A')}")
        
        # 检查调用树
        print(f"\n调用树:")
        call_tree = data.get('call_tree', {})
        if call_tree:
            print(f"  根节点: {call_tree.get('class_name', 'N/A')}.{call_tree.get('method_name', 'N/A')}")
            print(f"  项目: {call_tree.get('project', 'Unknown')}")
            
            # 统计节点类型
            def count_nodes(node, counts):
                node_type = node.get('node_type', 'unknown')
                counts[node_type] = counts.get(node_type, 0) + 1
                for child in node.get('children', []):
                    count_nodes(child, counts)
                return counts
            
            counts = count_nodes(call_tree, {})
            print(f"\n  节点统计:")
            for node_type, count in counts.items():
                print(f"    {node_type}: {count}")
            
            # 检查是否有 Unknown 项目的节点
            def find_unknown_nodes(node, path=""):
                unknown_nodes = []
                current_path = f"{path}/{node.get('class_name', 'N/A')}.{node.get('method_name', 'N/A')}"
                if node.get('project') == 'Unknown':
                    unknown_nodes.append({
                        'path': current_path,
                        'node': node
                    })
                for child in node.get('children', []):
                    unknown_nodes.extend(find_unknown_nodes(child, current_path))
                return unknown_nodes
            
            unknown_nodes = find_unknown_nodes(call_tree)
            if unknown_nodes:
                print(f"\n  ⚠ 发现 {len(unknown_nodes)} 个 Unknown 节点:")
                for item in unknown_nodes[:5]:
                    node = item['node']
                    print(f"    - {node.get('class_name', 'N/A')}.{node.get('method_name', 'N/A')}")
                    print(f"      类型: {node.get('node_type', 'N/A')}")
                    print(f"      路径: {item['path']}")
                if len(unknown_nodes) > 5:
                    print(f"    ... 还有 {len(unknown_nodes) - 5} 个")
            else:
                print(f"\n  ✓ 没有 Unknown 节点")
        else:
            print("  调用树为空")
    else:
        print(f"✗ 查询失败: {response.status_code}")
        print(f"  响应: {response.text}")
except Exception as e:
    print(f"✗ 请求失败: {e}")

print("\n" + "=" * 100)
