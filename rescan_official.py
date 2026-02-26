#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新扫描 official-room-pro-web"""
import requests
import time

url = "http://localhost:18000/api/projects/official-room-pro-web/scan"
print("触发强制重新扫描...")
response = requests.post(url, json={
    "project_path": "d:/cursor/code-ast-graph/git-repos/official-room-pro-web",
    "force": True
})

print(f"状态码: {response.status_code}")
print(f"响应: {response.text}")

if response.status_code in (200, 202):
    data = response.json()
    task_id = data.get('task_id')
    if task_id:
        print(f"\n任务 ID: {task_id}")
        print("等待扫描完成（每5秒检查一次）...")
        
        status_url = f"http://localhost:18000/api/scan/tasks/{task_id}"
        while True:
            time.sleep(5)
            status_response = requests.get(status_url)
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get('status')
                print(f"状态: {status}")
                
                if status == 'completed':
                    print("\n扫描完成！")
                    break
                elif status == 'failed':
                    print(f"\n扫描失败: {status_data.get('error')}")
                    break
