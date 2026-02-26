#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新扫描 yuer-chatroom-service"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import time

# 1. 触发扫描
print("=" * 100)
print("重新扫描 yuer-chatroom-service")
print("=" * 100)

print("\n1. 触发强制扫描...")
response = requests.post(
    "http://localhost:18000/api/projects/yuer-chatroom-service/scan",
    json={
        "project_path": "d:/cursor/code-ast-graph/git-repos/yuer-chatroom-service",
        "force": True
    }
)

if response.status_code in [200, 202]:
    print(f"  [OK] 扫描已启动 (状态码: {response.status_code})")
    result = response.json()
    if result.get('task_id'):
        print(f"  任务 ID: {result['task_id']}")
else:
    print(f"  [ERROR] 扫描失败: {response.status_code}")
    print(f"  {response.text}")
    sys.exit(1)

# 2. 等待扫描完成
print("\n2. 等待扫描完成...")
max_wait = 300  # 最多等待 5 分钟
start_time = time.time()

while time.time() - start_time < max_wait:
    time.sleep(5)
    
    # 检查项目状态
    response = requests.get("http://localhost:18000/api/projects")
    if response.status_code == 200:
        data = response.json()
        projects = data if isinstance(data, list) else data.get('projects', [])
        yuer_project = next((p for p in projects if p.get('name') == 'yuer-chatroom-service'), None)
        
        if yuer_project and yuer_project.get('status') == 'built':
            print(f"  [OK] 扫描完成！")
            print(f"  节点数: {yuer_project.get('node_count', 0)}")
            print(f"  关系数: {yuer_project.get('edge_count', 0)}")
            break
        else:
            elapsed = int(time.time() - start_time)
            print(f"  等待中... ({elapsed}s)")
    else:
        print(f"  [ERROR] 查询项目状态失败: {response.status_code}")
        break
else:
    print(f"  [TIMEOUT] 扫描超时")

print("\n" + "=" * 100)
print("完成")
print("=" * 100)
