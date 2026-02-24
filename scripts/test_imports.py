#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试导入路径是否正确
"""

import sys
import io
from pathlib import Path

# 设置 UTF-8 编码（Windows 兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("测试导入路径")
print("=" * 60)

# 测试 Java 解析器模块导入
print("\n1. 测试 Java 解析器模块导入...")
try:
    from src.parsers.java import JavaParser, JavaParserConfig, get_java_parser_config
    print("   [OK] Java 解析器模块导入成功")
except Exception as e:
    print(f"   [FAIL] Java 解析器模块导入失败: {e}")
    sys.exit(1)

# 测试 jQAssistant 模块导入
print("\n2. 测试 jQAssistant 模块导入...")
try:
    from src.jqassistant import JQAssistantScanner, JQAssistantQuerier, JQAssistantConfig
    print("   [OK] jQAssistant 模块导入成功")
except Exception as e:
    print(f"   [WARN] jQAssistant 模块导入失败（可选）: {e}")

# 测试查询层导入
print("\n3. 测试查询层导入...")
try:
    from src.query import Neo4jQuerier
    print("   [OK] 查询层导入成功")
except Exception as e:
    print(f"   [FAIL] 查询层导入失败: {e}")
    sys.exit(1)

# 测试 Neo4j 存储导入
print("\n4. 测试 Neo4j 存储导入...")
try:
    from src.storage.neo4j import Neo4jStorage
    print("   [OK] Neo4j 存储导入成功")
except Exception as e:
    print(f"   [FAIL] Neo4j 存储导入失败: {e}")
    sys.exit(1)

# 测试后端 API 导入
print("\n5. 测试后端 API 导入...")
try:
    from backend.main import app
    print("   [OK] 后端 API 导入成功")
except Exception as e:
    print(f"   [WARN] 后端 API 导入失败（可选）: {e}")

# 测试核心接口和模型导入
print("\n6. 测试核心接口和模型导入...")
try:
    from src.core import CodeInput, CodeParser, GraphStorage, CodeEntity, CodeRelationship, ParseResult
    print("   [OK] 核心接口和模型导入成功")
except Exception as e:
    print(f"   [FAIL] 核心接口和模型导入失败: {e}")
    sys.exit(1)

# 测试输入层导入
print("\n7. 测试输入层导入...")
try:
    from src.inputs import GitCodeInput, FileSystemCodeInput
    print("   [OK] 输入层导入成功")
except Exception as e:
    print(f"   [FAIL] 输入层导入失败: {e}")
    sys.exit(1)

# 测试服务层导入
print("\n8. 测试服务层导入...")
try:
    from src.services import ScanService
    print("   [OK] 服务层导入成功")
except Exception as e:
    print(f"   [FAIL] 服务层导入失败: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("[SUCCESS] 所有导入测试通过！")
print("=" * 60)
