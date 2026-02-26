#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整测试调用树功能"""
import time
import requests
import json

def print_tree(node, prefix="", is_last=True):
    """递归打印树形结构"""
    if not node:
        return
    
    connector = "└── " if is_last else "├── "
    
    node_type = node.get('node_type', 'unknown')
    project = node.get('project', 'Unknown')
    class_name = node.get('class_name', 'Unknown')
    method_name = node.get('method_name', '')
    
    if node_type == 'method':
        arch_layer = node.get('arch_layer', 'Other')
        label = f"[方法] {project}.{class_name}.{method_name} ({arch_layer})"
    elif node_type == 'dubbo_call':
        dubbo_interface = node.get('dubbo_interface', 'Unknown')
        dubbo_method = node.get('dubbo_method', 'Unknown')
        via_field = node.get('via_field', '')
        label = f"[Dubbo] {dubbo_interface}.{dubbo_method} (via: {via_field})"
    elif node_type == 'db_call':
        table_name = node.get('table_name', 'Unknown')
        mapper_name = node.get('mapper_name', 'Unknown')
        label = f"[数据库] {table_name} (Mapper: {mapper_name})"
    else:
        label = f"[{node_type}] {class_name}"
    
    print(f"{prefix}{connector}{label}")
    
    children = node.get('children', [])
    for i, child in enumerate(children):
        is_last_child = (i == len(children) - 1)
        extension = "    " if is_last else "│   "
        print_tree(child, prefix + extension, is_last_child)


print("=" * 100)
print("完整测试调用树功能")
print("=" * 100)

# 测试 1: 查询实现类方法
print("\n测试 1: 查询实现类方法 (official-room-pro-web.NobleController.openNoble)")
print("-" * 100)

mcp_url = "http://localhost:18000/api/mcp/query"
mcp_response = requests.post(mcp_url, json={
    "project": "official-room-pro-web",
    "class_fqn": "com.yupaopao.chatroom.official.room.web.controller.NobleController",
    "method": "openNoble"
})

if mcp_response.status_code == 200:
    mcp_data = mcp_response.json()
    call_tree = mcp_data.get('call_tree')
    
    if call_tree:
        print("\n调用树:")
        print_tree(call_tree)
        
        # 保存
        with open('call_tree_impl.json', 'w', encoding='utf-8') as f:
            json.dump(call_tree, f, indent=2, ensure_ascii=False)
        print(f"\n已保存到 call_tree_impl.json")
    else:
        print("未找到调用树")
else:
    print(f"查询失败: {mcp_response.status_code}")

# 测试 2: 查询接口方法
print("\n\n" + "=" * 100)
print("测试 2: 查询接口方法 (official-room-pro-web.NobleRemoteService.openNoble)")
print("-" * 100)

mcp_response2 = requests.post(mcp_url, json={
    "project": "official-room-pro-web",
    "class_fqn": "com.yupaopao.yuer.chatroom.official.api.NobleRemoteService",
    "method": "openNoble"
})

if mcp_response2.status_code == 200:
    mcp_data2 = mcp_response2.json()
    call_tree2 = mcp_data2.get('call_tree')
    
    if call_tree2:
        print("\n调用树:")
        print_tree(call_tree2)
        
        # 保存
        with open('call_tree_interface.json', 'w', encoding='utf-8') as f:
            json.dump(call_tree2, f, indent=2, ensure_ascii=False)
        print(f"\n已保存到 call_tree_interface.json")
    else:
        print("未找到调用树")
else:
    print(f"查询失败: {mcp_response2.status_code}")

print("\n" + "=" * 100)
print("测试完成")
print("=" * 100)
