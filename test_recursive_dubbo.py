#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试递归 Dubbo 调用查询"""
import time
import requests

print("=" * 100)
print("测试递归 Dubbo 调用查询")
print("=" * 100)

# 等待后端启动
print("\n等待后端启动...")
time.sleep(10)

# 测试: 查询 official-room-pro-web.NobleController.openNoble
# 期望：能看到下游 yuer-chatroom-service 的完整链路
print("\n测试: 查询 official-room-pro-web.NobleController.openNoble")
print("期望: 能看到下游 yuer-chatroom-service 的完整链路")
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
    
    # 1. 前端入口
    endpoints = mcp_data.get('endpoints', [])
    print(f"\n1. 前端入口 ({len(endpoints)} 个):")
    for ep in endpoints:
        print(f"   {ep.get('http_method')} {ep.get('path')}")
    
    # 2. Dubbo 调用
    dubbo_calls = mcp_data.get('dubbo_calls', [])
    print(f"\n2. Dubbo 调用 ({len(dubbo_calls)} 个):")
    for dc in dubbo_calls:
        print(f"   {dc.get('caller_project')}.{dc.get('caller_class')}.{dc.get('caller_method')}")
        print(f"   -> {dc.get('dubbo_interface')}.{dc.get('dubbo_method')}")
        print(f"   (via: {dc.get('via_field')})")
        print()
    
    # 3. 内部类
    internal_classes = mcp_data.get('internal_classes', [])
    print(f"\n3. 内部类 ({len(internal_classes)} 个):")
    
    # 按项目分组
    by_project = {}
    for ic in internal_classes:
        proj = ic.get('project', 'Unknown')
        if proj not in by_project:
            by_project[proj] = []
        by_project[proj].append(ic)
    
    for proj, classes in sorted(by_project.items()):
        print(f"\n   项目: {proj} ({len(classes)} 个类)")
        for ic in classes[:10]:  # 每个项目最多显示10个
            print(f"     - {ic.get('class_name')} ({ic.get('arch_layer')})")
        if len(classes) > 10:
            print(f"     ... 还有 {len(classes) - 10} 个")
    
    # 4. 数据库表
    tables = mcp_data.get('tables', [])
    print(f"\n4. 数据库表 ({len(tables)} 个):")
    for t in tables:
        print(f"   {t.get('project')}: {t.get('table_name')} (Mapper: {t.get('mapper_name')})")
    
    # 5. Aries Job
    aries_jobs = mcp_data.get('aries_jobs', [])
    print(f"\n5. Aries Job ({len(aries_jobs)} 个):")
    for aj in aries_jobs:
        print(f"   {aj.get('project')}.{aj.get('class_name')} ({aj.get('job_type')})")
    
    # 6. MQ
    mq_info = mcp_data.get('mq_info', [])
    print(f"\n6. MQ ({len(mq_info)} 个):")
    for mq in mq_info:
        print(f"   {mq.get('project')}.{mq.get('class_name')}: {mq.get('topic')} ({mq.get('role')})")
    
    # 验证结果
    print("\n" + "=" * 100)
    print("验证结果:")
    
    has_downstream = False
    for proj in by_project.keys():
        if proj != 'official-room-pro-web' and proj != 'Unknown':
            has_downstream = True
            print(f"  发现下游项目: {proj}")
    
    if has_downstream:
        print(f"\n  状态: 成功！递归查询到了下游服务的链路")
    else:
        print(f"\n  状态: 失败！未找到下游服务的链路")
        print(f"  提示: 可能下游服务未扫描，或者查询逻辑有问题")
    
else:
    print(f"MCP 查询失败: {mcp_response.status_code}")
    print(f"响应: {mcp_response.text}")

print("\n" + "=" * 100)
