#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试调用树结构"""
import time
import requests
import json

def print_tree(node, prefix="", is_last=True):
    """
    递归打印树形结构
    
    Args:
        node: 节点字典
        prefix: 前缀（用于缩进）
        is_last: 是否是最后一个子节点
    """
    if not node:
        return
    
    # 打印当前节点
    connector = "└── " if is_last else "├── "
    
    node_type = node.get('node_type', 'unknown')
    project = node.get('project', 'Unknown')
    class_name = node.get('class_name', 'Unknown')
    method_name = node.get('method_name', '')
    
    # 根据节点类型显示不同的信息
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
    elif node_type == 'mq':
        topic = node.get('mq_topic', 'Unknown')
        role = node.get('mq_role', 'Unknown')
        label = f"[MQ] {topic} ({role})"
    elif node_type == 'aries_job':
        job_type = node.get('job_type', 'Unknown')
        label = f"[Aries Job] {class_name} ({job_type})"
    else:
        label = f"[{node_type}] {class_name}"
    
    print(f"{prefix}{connector}{label}")
    
    # 递归打印子节点
    children = node.get('children', [])
    for i, child in enumerate(children):
        is_last_child = (i == len(children) - 1)
        extension = "    " if is_last else "│   "
        print_tree(child, prefix + extension, is_last_child)


print("=" * 100)
print("测试调用树结构")
print("=" * 100)

# 等待后端启动
print("\n等待后端启动...")
time.sleep(10)

# 测试: 查询 official-room-pro-web.NobleController.openNoble
print("\n查询: official-room-pro-web.NobleController.openNoble")
print("-" * 100)

mcp_url = "http://localhost:18000/api/mcp/query"
mcp_response = requests.post(mcp_url, json={
    "project": "official-room-pro-web",
    "class_fqn": "com.yupaopao.chatroom.official.room.web.controller.NobleController",
    "method": "openNoble"
})

print(f"\n状态码: {mcp_response.status_code}")

if mcp_response.status_code == 200:
    mcp_data = mcp_response.json()
    
    # 检查是否有调用树
    call_tree = mcp_data.get('call_tree')
    
    if call_tree:
        print("\n调用树结构:")
        print("=" * 100)
        print_tree(call_tree)
        print("=" * 100)
        
        # 保存到文件
        with open('call_tree.json', 'w', encoding='utf-8') as f:
            json.dump(call_tree, f, indent=2, ensure_ascii=False)
        print("\n调用树已保存到 call_tree.json")
        
    else:
        print("\n未找到调用树结构")
    
    # 显示统计信息
    print(f"\n统计信息:")
    print(f"  前端入口: {len(mcp_data.get('endpoints', []))} 个")
    print(f"  Dubbo 调用: {len(mcp_data.get('dubbo_calls', []))} 个")
    print(f"  内部类: {len(mcp_data.get('internal_classes', []))} 个")
    print(f"  数据库表: {len(mcp_data.get('tables', []))} 个")
    
else:
    print(f"MCP 查询失败: {mcp_response.status_code}")
    print(f"响应: {mcp_response.text}")

print("\n" + "=" * 100)
