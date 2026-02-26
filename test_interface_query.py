#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试接口方法查询"""
import time
import requests

print("=" * 100)
print("测试接口方法查询")
print("=" * 100)

# 等待后端启动
print("\n等待后端启动...")
time.sleep(10)

# 测试 1: 查询接口方法 - official-room-pro-web.NobleRemoteService.openNoble
print("\n测试 1: 查询接口方法 (official-room-pro-web.NobleRemoteService.openNoble)...")
mcp_url = "http://localhost:18000/api/mcp/query"
mcp_response = requests.post(mcp_url, json={
    "project": "official-room-pro-web",
    "class_fqn": "com.yupaopao.yuer.chatroom.official.api.NobleRemoteService",
    "method": "openNoble"
})

print(f"状态码: {mcp_response.status_code}")

if mcp_response.status_code == 200:
    mcp_data = mcp_response.json()
    
    # 检查前端入口
    endpoints = mcp_data.get('endpoints', [])
    print(f"\n找到 {len(endpoints)} 个前端入口:")
    for ep in endpoints:
        print(f"  项目: {ep.get('project')}")
        print(f"  类: {ep.get('class_fqn')}")
        print(f"  路径: {ep.get('path')}")
    
    # 检查 Dubbo 调用
    dubbo_calls = mcp_data.get('dubbo_calls', [])
    print(f"\n找到 {len(dubbo_calls)} 个 Dubbo 调用:")
    for dc in dubbo_calls:
        print(f"\n  调用方项目: {dc.get('caller_project')}")
        print(f"  调用方类: {dc.get('caller_class')}")
        print(f"  Dubbo 接口: {dc.get('dubbo_interface')}")
        print(f"  Dubbo 方法: {dc.get('dubbo_method')}")
    
    # 检查内部类
    internal_classes = mcp_data.get('internal_classes', [])
    print(f"\n找到 {len(internal_classes)} 个内部类:")
    for ic in internal_classes[:5]:  # 只显示前5个
        print(f"  {ic.get('project')}.{ic.get('class_name')} ({ic.get('arch_layer')})")
    if len(internal_classes) > 5:
        print(f"  ... 还有 {len(internal_classes) - 5} 个")
    
    # 检查数据库表
    tables = mcp_data.get('tables', [])
    print(f"\n找到 {len(tables)} 个数据库表:")
    for t in tables:
        print(f"  {t.get('table_name')} (Mapper: {t.get('mapper_name')})")
    
    if dubbo_calls or tables or len(internal_classes) > 1:
        print(f"\n状态: 成功！接口方法查询到了实现类的下游链路")
    else:
        print(f"\n状态: 可能未找到实现类的下游链路")
else:
    print(f"MCP 查询失败: {mcp_response.status_code}")
    print(f"响应: {mcp_response.text}")

print("\n" + "=" * 100)

# 测试 2: 对比查询实现类方法
print("\n测试 2: 对比查询实现类方法 (official-room-pro-web.NobleController.openNoble)...")
mcp_response2 = requests.post(mcp_url, json={
    "project": "official-room-pro-web",
    "class_fqn": "com.yupaopao.chatroom.official.room.web.controller.NobleController",
    "method": "openNoble"
})

if mcp_response2.status_code == 200:
    mcp_data2 = mcp_response2.json()
    dubbo_calls2 = mcp_data2.get('dubbo_calls', [])
    tables2 = mcp_data2.get('tables', [])
    
    print(f"实现类查询结果:")
    print(f"  Dubbo 调用: {len(dubbo_calls2)} 个")
    print(f"  数据库表: {len(tables2)} 个")
    
    if len(dubbo_calls) == len(dubbo_calls2) and len(tables) == len(tables2):
        print(f"\n验证: 接口方法查询结果与实现类查询结果一致！✅")
    else:
        print(f"\n验证: 结果不一致，可能需要进一步检查")

print("\n" + "=" * 100)
