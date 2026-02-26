#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终测试 MCP 查询"""
import time
import requests

print("=" * 100)
print("最终测试 MCP 查询")
print("=" * 100)

# 等待后端启动
print("\n等待后端启动...")
time.sleep(10)

# 测试 MCP 查询
print("\n测试 MCP 查询...")
mcp_url = "http://localhost:18000/api/mcp/query"
mcp_response = requests.post(mcp_url, json={
    "project": "yuer-chatroom-service",
    "class_fqn": "com.yupaopao.chatroom.controller.NobleController",
    "method": "openNoble"
})

print(f"状态码: {mcp_response.status_code}")

if mcp_response.status_code == 200:
    mcp_data = mcp_response.json()
    endpoints = mcp_data.get('endpoints', [])
    
    print(f"\n找到 {len(endpoints)} 个前端入口:")
    for ep in endpoints:
        print(f"\n  项目: {ep.get('project')}")
        print(f"  类: {ep.get('class_fqn')}")
        print(f"  方法: {ep.get('method')}")
        print(f"  路径: {ep.get('path')}")
        print(f"  HTTP方法: {ep.get('http_method')}")
    
    if endpoints:
        # 检查是否有正确的 endpoint
        found_correct = False
        for ep in endpoints:
            if ep.get('path') == '/official/open/noble':
                found_correct = True
                print(f"\n状态: 成功！找到正确的前端入口 /official/open/noble")
                break
        
        if not found_correct:
            print(f"\n状态: 失败！未找到 /official/open/noble endpoint")
    else:
        print(f"\n状态: 失败！未找到任何前端入口")
else:
    print(f"MCP 查询失败: {mcp_response.status_code}")
    print(f"响应: {mcp_response.text}")

print("\n" + "=" * 100)
