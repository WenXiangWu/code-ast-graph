#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试修复后的 _extract_type_name"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import javalang
from src.parsers.java.scanner_v2 import JavaASTScannerV2

file_path = Path("d:/cursor/code-ast-graph/git-repos/official-room-pro-web/official-web/src/main/java/com/yupaopao/chatroom/official/room/web/controller/NobleController.java")

print("=" * 100)
print(f"测试修复后的 _extract_type_name")
print("=" * 100)

# 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 解析
tree = javalang.parse.parse(content)

# 创建扫描器实例
scanner = JavaASTScannerV2()

# 查找类
for path, node in tree.filter(javalang.tree.ClassDeclaration):
    if node.name == 'NobleController':
        print(f"\n找到类: {node.name}")
        
        # 检查 implements
        if node.implements:
            print(f"  implements 数量: {len(node.implements)}")
            for impl in node.implements:
                print(f"\n  implements:")
                print(f"    原始结构: {impl}")
                
                # 使用修复后的方法提取类型名称
                impl_name = scanner._extract_type_name(impl)
                print(f"    提取的名称: {impl_name}")
                
                if impl_name == 'com.yupaopao.yuer.chatroom.official.api.NobleRemoteService':
                    print(f"    成功！正确提取了完整的 FQN")
                else:
                    print(f"    失败！期望: com.yupaopao.yuer.chatroom.official.api.NobleRemoteService")

print("\n" + "=" * 100)
