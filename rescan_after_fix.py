#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新扫描项目以应用修复后的类型推断逻辑"""
import sys
import io
import requests
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 100)
print("重新扫描项目以应用修复")
print("=" * 100)

# 1. 重启后端服务
print("\n1. 请先重启后端服务:")
print("   - 停止当前的 backend/main.py")
print("   - 重新启动: python backend/main.py")
print("   按 Enter 继续...")
input()

# 2. 重新扫描 yuer-chatroom-service
print("\n2. 重新扫描 yuer-chatroom-service:")
print("   发送扫描请求...")

try:
    response = requests.post(
        "http://localhost:18000/api/scan",
        json={
            "project_path": r"d:\cursor\code-ast-graph\git-repos\yuer-chatroom-service",
            "force": True
        },
        timeout=300
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ 扫描成功")
        print(f"   状态: {data.get('status')}")
        print(f"   消息: {data.get('message')}")
    else:
        print(f"   ✗ 扫描失败: {response.status_code}")
        print(f"   响应: {response.text}")
except Exception as e:
    print(f"   ✗ 请求失败: {e}")

print("\n等待扫描完成...")
time.sleep(5)

# 3. 检查扫描状态
print("\n3. 检查扫描状态:")
try:
    response = requests.get("http://localhost:18000/api/projects")
    if response.status_code == 200:
        data = response.json()
        projects = data if isinstance(data, list) else data.get('projects', [])
        
        for project in projects:
            if project['name'] == 'yuer-chatroom-service':
                print(f"   项目: {project['name']}")
                print(f"   状态: {project['status']}")
                print(f"   类数量: {project.get('class_count', 0)}")
                print(f"   方法数量: {project.get('method_count', 0)}")
                break
    else:
        print(f"   ✗ 获取项目状态失败: {response.status_code}")
except Exception as e:
    print(f"   ✗ 请求失败: {e}")

print("\n" + "=" * 100)
print("扫描完成！")
print("=" * 100)
