#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""触发重新扫描"""
import sys
import io
import requests
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 100)
print("触发重新扫描 yuer-chatroom-service")
print("=" * 100)

print("\n发送扫描请求...")
try:
    response = requests.post(
        "http://localhost:18000/api/projects/yuer-chatroom-service/scan",
        json={
            "project_path": r"d:\cursor\code-ast-graph\git-repos\yuer-chatroom-service",
            "force": True
        },
        timeout=600
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ 扫描请求已发送")
        print(f"  状态: {data.get('status')}")
        print(f"  消息: {data.get('message')}")
    else:
        print(f"✗ 扫描失败: {response.status_code}")
        print(f"  响应: {response.text}")
except Exception as e:
    print(f"✗ 请求失败: {e}")

print("\n" + "=" * 100)
