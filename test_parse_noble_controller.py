#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试解析 NobleController 的 implements"""
import javalang
from pathlib import Path

file_path = Path("d:/cursor/code-ast-graph/git-repos/official-room-pro-web/official-web/src/main/java/com/yupaopao/chatroom/official/room/web/controller/NobleController.java")

print("=" * 100)
print(f"解析文件: {file_path.name}")
print("=" * 100)

# 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 解析
tree = javalang.parse.parse(content)

# 提取包名
package_name = tree.package.name if tree.package else ''
print(f"\n包名: {package_name}")

# 提取 imports
imports = {}
if tree.imports:
    for imp in tree.imports:
        if imp.path:
            parts = imp.path.split('.')
            class_name = parts[-1]
            imports[class_name] = imp.path
            if 'Noble' in class_name:
                print(f"  import: {class_name} -> {imp.path}")

# 查找类
for path, node in tree.filter(javalang.tree.ClassDeclaration):
    if node.name == 'NobleController':
        print(f"\n找到类: {node.name}")
        
        # 检查 implements
        if node.implements:
            print(f"  implements 数量: {len(node.implements)}")
            for impl in node.implements:
                print(f"\n  implements:")
                print(f"    type: {type(impl)}")
                print(f"    impl: {impl}")
                
                if hasattr(impl, 'name'):
                    print(f"    name type: {type(impl.name)}")
                    print(f"    name: {impl.name}")
                    
                    if isinstance(impl.name, list):
                        impl_name = '.'.join(impl.name)
                    else:
                        impl_name = str(impl.name)
                    
                    print(f"    extracted name: {impl_name}")
                    
                    # 尝试解析 FQN
                    if '.' in impl_name:
                        # 已经是 FQN
                        fqn = impl_name
                    elif impl_name in imports:
                        # 在 imports 中
                        fqn = imports[impl_name]
                    else:
                        # 同包
                        fqn = f"{package_name}.{impl_name}"
                    
                    print(f"    resolved FQN: {fqn}")
        else:
            print(f"  没有 implements")

print("\n" + "=" * 100)
