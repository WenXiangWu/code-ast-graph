#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查具体方法的项目关联"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("检查具体方法的项目关联")
print("=" * 100)

# 1. 查找 HomeShowCardService.collectNoble 方法
print("\n1. 查找 HomeShowCardService.collectNoble 方法:")
result = storage.execute_query("""
    MATCH (c)-[:DECLARES]->(m:Method)
    WHERE c.name = 'HomeShowCardService' AND m.name = 'collectNoble'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN 
        p.name as project,
        c.fqn as class_fqn,
        labels(c) as labels,
        m.signature as signature,
        c.arch_layer as arch_layer
""")

if result:
    print(f"  找到 {len(result)} 个方法:")
    for r in result:
        print(f"    项目: {r['project'] or 'Unknown'}")
        print(f"    类: {r['class_fqn']} ({r['labels'][0]})")
        print(f"    签名: {r['signature']}")
        print(f"    架构层: {r['arch_layer']}")
        print()
else:
    print("  未找到")

# 2. 查找 NobleMessageSendManager.sendNobleChangeMessage 方法
print("\n2. 查找 NobleMessageSendManager.sendNobleChangeMessage 方法:")
result = storage.execute_query("""
    MATCH (c)-[:DECLARES]->(m:Method)
    WHERE c.name = 'NobleMessageSendManager' AND m.name = 'sendNobleChangeMessage'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
    RETURN 
        p.name as project,
        c.fqn as class_fqn,
        labels(c) as labels,
        m.signature as signature,
        c.arch_layer as arch_layer
""")

if result:
    print(f"  找到 {len(result)} 个方法:")
    for r in result:
        print(f"    项目: {r['project'] or 'Unknown'}")
        print(f"    类: {r['class_fqn']} ({r['labels'][0]})")
        print(f"    签名: {r['signature']}")
        print(f"    架构层: {r['arch_layer']}")
        print()
else:
    print("  未找到")

# 3. 检查这些类是否在扫描报告中
print("\n3. 检查扫描报告中是否有这些类:")
import json
from pathlib import Path

report_files = list(Path('git-repos/scan_reports').glob('yuer-chatroom-service_*.json'))
if report_files:
    latest_report = sorted(report_files)[-1]
    print(f"  最新报告: {latest_report.name}")
    
    with open(latest_report, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    # 查找这些类
    found_home = False
    found_noble_msg = False
    
    for module_name, module_data in report.get('modules', {}).items():
        for package_name, package_data in module_data.get('packages', {}).items():
            for class_info in package_data.get('classes', []):
                if class_info['name'] == 'HomeShowCardService':
                    found_home = True
                    print(f"\n  找到 HomeShowCardService:")
                    print(f"    模块: {module_name}")
                    print(f"    包: {package_name}")
                    print(f"    类型: {class_info.get('kind', 'N/A')}")
                    print(f"    架构层: {class_info.get('arch_layer', 'N/A')}")
                
                if class_info['name'] == 'NobleMessageSendManager':
                    found_noble_msg = True
                    print(f"\n  找到 NobleMessageSendManager:")
                    print(f"    模块: {module_name}")
                    print(f"    包: {package_name}")
                    print(f"    类型: {class_info.get('kind', 'N/A')}")
                    print(f"    架构层: {class_info.get('arch_layer', 'N/A')}")
    
    if not found_home:
        print(f"\n  [WARNING] HomeShowCardService 不在扫描报告中（可能被过滤）")
    if not found_noble_msg:
        print(f"\n  [WARNING] NobleMessageSendManager 不在扫描报告中（可能被过滤）")
else:
    print("  未找到扫描报告")

print("\n" + "=" * 100)
