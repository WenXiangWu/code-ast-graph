#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试解析 NobleRemoteService 接口"""
import javalang
from pathlib import Path

file_path = Path("d:/cursor/code-ast-graph/git-repos/official-room-pro-web/official-web-api/src/main/java/com/yupaopao/yuer/chatroom/official/api/NobleRemoteService.java")

print("=" * 100)
print(f"解析文件: {file_path.name}")
print("=" * 100)

# 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 解析
tree = javalang.parse.parse(content)

# 查找接口
for path, node in tree.filter(javalang.tree.InterfaceDeclaration):
    print(f"\n接口: {node.name}")
    
    # 查找方法
    if node.methods:
        print(f"  方法数量: {len(node.methods)}")
        
        for method in node.methods:
            if method.name == 'openNoble':
                print(f"\n  找到 openNoble 方法:")
                print(f"    返回类型: {method.return_type}")
                print(f"    参数数量: {len(method.parameters) if method.parameters else 0}")
                
                # 检查是否有 annotations 属性
                print(f"    hasattr(method, 'annotations'): {hasattr(method, 'annotations')}")
                
                if hasattr(method, 'annotations'):
                    print(f"    method.annotations: {method.annotations}")
                    
                    if method.annotations:
                        print(f"    注解数量: {len(method.annotations)}")
                        for ann in method.annotations:
                            print(f"\n      注解:")
                            print(f"        name: {ann.name}")
                            print(f"        element: {ann.element}")
                            
                            if ann.name == 'MobileAPI':
                                print(f"        ✅ 找到 @MobileAPI 注解!")
                                if ann.element:
                                    if isinstance(ann.element, list):
                                        for elem in ann.element:
                                            if hasattr(elem, 'name') and elem.name == 'path':
                                                print(f"          path = {elem.value.value}")
                    else:
                        print(f"    ❌ method.annotations 是空列表")
                else:
                    print(f"    ❌ method 没有 annotations 属性")
                
                break
    else:
        print(f"  ❌ 接口没有 methods 属性")

print("\n" + "=" * 100)
