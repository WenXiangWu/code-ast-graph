#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""监控扫描进度"""
import sys
import io
import requests
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

task_id = "44a55313-e195-4e30-af57-9ef7a4eef83b"

print("=" * 100)
print(f"监控扫描进度: {task_id}")
print("=" * 100)

while True:
    try:
        response = requests.get(f"http://localhost:18000/api/scan/tasks/{task_id}")
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            progress = data.get('progress', 0)
            message = data.get('message', '')
            
            print(f"\r状态: {status} | 进度: {progress}% | {message}", end='', flush=True)
            
            if status in ['completed', 'failed']:
                print()  # 换行
                if status == 'completed':
                    print("\n✓ 扫描完成！")
                    result = data.get('result', {})
                    print(f"  类数量: {result.get('class_count', 0)}")
                    print(f"  方法数量: {result.get('method_count', 0)}")
                else:
                    print("\n✗ 扫描失败")
                    print(f"  错误: {data.get('error', 'Unknown')}")
                break
        else:
            print(f"\n✗ 获取进度失败: {response.status_code}")
            break
    except Exception as e:
        print(f"\n✗ 请求失败: {e}")
        break
    
    time.sleep(2)

print("\n" + "=" * 100)
