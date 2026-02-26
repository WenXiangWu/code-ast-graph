#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试环境变量配置"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
project_root = Path(__file__).parent
env_file = project_root / '.env'

print(f"环境文件路径: {env_file}")
print(f"文件是否存在: {env_file.exists()}")

load_dotenv(env_file)

print("\n" + "=" * 100)
print("环境变量配置")
print("=" * 100)

# 检查关键配置
configs = [
    'NEO4J_URI',
    'NEO4J_USER',
    'NEO4J_PASSWORD',
    'BACKEND_PORT',
    'FRONTEND_PORT',
    'GENERATE_SCAN_REPORT',
    'PYTHON_AST_ENABLED'
]

for config in configs:
    value = os.getenv(config)
    print(f"{config}: {value}")

print("\n" + "=" * 100)
print("测试 GENERATE_SCAN_REPORT 解析")
print("=" * 100)

generate_report = os.getenv('GENERATE_SCAN_REPORT', 'false').lower()
should_generate = generate_report in ('true', '1', 'yes', 'on')

print(f"原始值: {os.getenv('GENERATE_SCAN_REPORT')}")
print(f"转小写: {generate_report}")
print(f"是否生成报告: {should_generate}")
