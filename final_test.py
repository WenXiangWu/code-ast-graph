#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终测试 - 完整验证 Noble 调用链"""
import sys
import time
import requests
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.storage.neo4j.storage import Neo4jStorage

print("=" * 100)
print("最终测试 - Noble 调用链")
print("=" * 100)

# 等待后端启动
print("\n等待后端启动...")
time.sleep(10)

# 1. 重新扫描 official-room-pro-web
print("\n步骤 1: 重新扫描 official-room-pro-web...")
url = "http://localhost:18000/api/projects/official-room-pro-web/scan"
response = requests.post(url, json={
    "project_path": "d:/cursor/code-ast-graph/git-repos/official-room-pro-web",
    "force": True
})

if response.status_code == 202:
    data = response.json()
    task_id = data.get('task_id')
    print(f"  任务 ID: {task_id}")
    
    # 等待扫描完成
    status_url = f"http://localhost:18000/api/scan/tasks/{task_id}"
    while True:
        time.sleep(5)
        status_response = requests.get(status_url)
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get('status')
            print(f"  状态: {status}")
            
            if status == 'completed':
                print(f"  扫描完成！")
                break
            elif status == 'failed':
                print(f"  扫描失败: {status_data.get('error')}")
                sys.exit(1)
else:
    print(f"  触发扫描失败: {response.status_code}")
    sys.exit(1)

# 2. 验证 IMPLEMENTS 关系
print("\n步骤 2: 验证 NobleController 的 IMPLEMENTS 关系...")
storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

result = storage.execute_query("""
    MATCH (p:Project {name: 'official-room-pro-web'})-[:CONTAINS]->(c:CLASS {name: 'NobleController'})
    MATCH (c)-[:IMPLEMENTS]->(i:INTERFACE)
    RETURN c.fqn as class_fqn, i.fqn as interface_fqn
""")

if result:
    success = False
    for r in result:
        print(f"  类: {r['class_fqn']}")
        print(f"  实现接口: {r['interface_fqn']}")
        if r['interface_fqn'] == 'com.yupaopao.yuer.chatroom.official.api.NobleRemoteService':
            print(f"  状态: 正确")
            success = True
        else:
            print(f"  状态: 错误！")
    
    if not success:
        print("\n  IMPLEMENTS 关系仍然不正确，测试失败")
        sys.exit(1)
else:
    print("  未找到 IMPLEMENTS 关系，测试失败")
    sys.exit(1)

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
        # 检查是否有正确的 endpoint
        found_correct = False
        for ep in endpoints:
            if ep.get('path') == '/official/open/noble':
                found_correct = True
                break
        
        if found_correct:
            print(f"\n  状态: 成功！找到正确的前端入口")
        else:
            print(f"\n  状态: 失败！未找到 /official/open/noble endpoint")
            sys.exit(1)
    else:
        print(f"\n  状态: 失败！未找到任何前端入口")
        sys.exit(1)
else:
    print(f"  MCP 查询失败: {mcp_response.status_code}")
    sys.exit(1)

print("\n" + "=" * 100)
print("所有测试通过！")
print("=" * 100)
