#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试下游 Dubbo 调用查询"""
import time
import requests

print("=" * 100)
print("测试下游 Dubbo 调用查询")
print("=" * 100)

# 等待后端启动
print("\n等待后端启动...")
time.sleep(10)

# 测试 MCP 查询 - 从 official-room-pro-web.NobleController.openNoble 开始
print("\n测试 MCP 查询 (official-room-pro-web.NobleController.openNoble)...")
mcp_url = "http://localhost:18000/api/mcp/query"
mcp_response = requests.post(mcp_url, json={
    "project": "official-room-pro-web",
    "class_fqn": "com.yupaopao.chatroom.official.room.web.controller.NobleController",
    "method": "openNoble"
})

print(f"状态码: {mcp_response.status_code}")

if mcp_response.status_code == 200:
    mcp_data = mcp_response.json()
    
    # 检查前端入口
    endpoints = mcp_data.get('endpoints', [])
    print(f"\n找到 {len(endpoints)} 个前端入口:")
    for ep in endpoints:
        print(f"  路径: {ep.get('path')}")
    
    # 检查 Dubbo 调用
    dubbo_calls = mcp_data.get('dubbo_calls', [])
    print(f"\n找到 {len(dubbo_calls)} 个 Dubbo 调用:")
    for dc in dubbo_calls:
        print(f"\n  调用方项目: {dc.get('caller_project')}")
        print(f"  调用方类: {dc.get('caller_class')}")
        print(f"  调用方方法: {dc.get('caller_method')}")
        print(f"  Dubbo 接口: {dc.get('dubbo_interface')}")
        print(f"  Dubbo 方法: {dc.get('dubbo_method')}")
        print(f"  通过字段: {dc.get('via_field')}")
    
    if dubbo_calls:
        print(f"\n状态: 成功！找到下游 Dubbo 调用")
    else:
        print(f"\n状态: 失败！未找到下游 Dubbo 调用")
    
    # 检查内部类
    internal_classes = mcp_data.get('internal_classes', [])
    print(f"\n找到 {len(internal_classes)} 个内部类")
    
    # 检查数据库表
    tables = mcp_data.get('tables', [])
    print(f"找到 {len(tables)} 个数据库表")
else:
    print(f"MCP 查询失败: {mcp_response.status_code}")
    print(f"响应: {mcp_response.text}")

print("\n" + "=" * 100)
