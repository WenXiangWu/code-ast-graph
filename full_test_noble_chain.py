#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整测试 Noble 调用链（重新扫描后）"""
import sys
import time
import requests
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.storage.neo4j.storage import Neo4jStorage

print("=" * 100)
print("完整测试 Noble 调用链")
print("=" * 100)

# 1. 触发重新扫描 official-room-pro-web
print("\n步骤 1: 触发重新扫描 official-room-pro-web...")
url = "http://localhost:18000/api/projects/official-room-pro-web/scan"
response = requests.post(url, json={"project_path": "d:/cursor/code-ast-graph/git-repos/official-room-pro-web"})

if response.status_code in (200, 202):
    data = response.json()
    task_id = data.get('task_id')
    print(f"  扫描任务已启动: {task_id}")
    
    # 等待扫描完成
    status_url = f"http://localhost:18000/api/scan/tasks/{task_id}"
    while True:
        time.sleep(5)
        status_response = requests.get(status_url)
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get('status')
            print(f"  任务状态: {status}")
            
            if status == 'completed':
                print(f"  扫描完成！")
                break
            elif status == 'failed':
                print(f"  扫描失败: {status_data.get('error')}")
                sys.exit(1)
        else:
            print(f"  查询状态失败")
            break
else:
    print(f"  触发扫描失败: {response.status_code}")
    print(f"  {response.text}")
    sys.exit(1)

# 2. 连接 Neo4j 验证数据
print("\n步骤 2: 验证 Neo4j 数据...")
storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

# 2.1 检查 NobleController 的 IMPLEMENTS 关系
print("\n2.1 检查 official-room-pro-web.NobleController 的 IMPLEMENTS 关系:")
result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS {name: 'NobleController'})
    MATCH (c)-[:IMPLEMENTS]->(i:INTERFACE)
    RETURN c.fqn as class_fqn, i.fqn as interface_fqn
""")

if result:
    for r in result:
        print(f"  类: {r['class_fqn']}")
        print(f"  实现接口: {r['interface_fqn']}")
        if r['interface_fqn'] == 'com.yupaopao.yuer.chatroom.official.api.NobleRemoteService':
            print(f"  状态: 正确")
        else:
            print(f"  状态: 错误！期望 com.yupaopao.yuer.chatroom.official.api.NobleRemoteService")
else:
    print("  未找到 IMPLEMENTS 关系")

# 2.2 检查 NobleRemoteService.openNoble 的 RpcEndpoint
print("\n2.2 检查 NobleRemoteService.openNoble 的 RpcEndpoint:")
result = storage.execute_query("""
    MATCH (i:INTERFACE {fqn: 'com.yupaopao.yuer.chatroom.official.api.NobleRemoteService'})
    MATCH (i)-[:DECLARES]->(m:Method {name: 'openNoble'})
    OPTIONAL MATCH (m)-[:EXPOSES]->(ep:RpcEndpoint)
    RETURN m.signature as signature, ep.path as path, ep.http_method as http_method
""")

if result:
    r = result[0]
    print(f"  方法签名: {r['signature']}")
    print(f"  Endpoint 路径: {r['path']}")
    print(f"  HTTP 方法: {r['http_method']}")
    if r['path']:
        print(f"  状态: RpcEndpoint 已创建")
    else:
        print(f"  状态: RpcEndpoint 未创建！")
else:
    print("  未找到方法")

# 3. 测试 MCP 查询
print("\n步骤 3: 测试 MCP 查询...")
mcp_url = "http://localhost:18000/api/mcp/query"
mcp_response = requests.post(mcp_url, json={
    "method_signature": "yuer-chatroom-service.com.yupaopao.chatroom.controller.NobleController.openNoble"
})

if mcp_response.status_code == 200:
    mcp_data = mcp_response.json()
    endpoints = mcp_data.get('endpoints', [])
    
    print(f"  找到 {len(endpoints)} 个前端入口:")
    for ep in endpoints:
        print(f"\n    项目: {ep.get('project')}")
        print(f"    类: {ep.get('class_fqn')}")
        print(f"    方法: {ep.get('method')}")
        print(f"    路径: {ep.get('path')}")
        print(f"    HTTP方法: {ep.get('http_method')}")
    
    if endpoints:
        print(f"\n  状态: 成功找到前端入口！")
    else:
        print(f"\n  状态: 未找到前端入口")
else:
    print(f"  MCP 查询失败: {mcp_response.status_code}")

print("\n" + "=" * 100)
print("测试完成")
print("=" * 100)
