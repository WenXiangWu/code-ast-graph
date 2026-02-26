#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 javalang 如何解析链式调用"""
import javalang

code = """
public class Test {
    private List<String> list;
    
    public void test() {
        list.stream().collect(Collectors.toList());
        this.method1();
        method2();
    }
}
"""

tree = javalang.parse.parse(code)

for path, node in tree.filter(javalang.tree.MethodInvocation):
    print(f"方法调用: {node.member}")
    print(f"  qualifier: {node.qualifier}")
    if node.qualifier:
        print(f"  qualifier type: {type(node.qualifier)}")
        if hasattr(node.qualifier, 'member'):
            print(f"  qualifier.member: {node.qualifier.member}")
        if hasattr(node.qualifier, 'value'):
            print(f"  qualifier.value: {node.qualifier.value}")
        if hasattr(node.qualifier, 'qualifier'):
            print(f"  qualifier.qualifier: {node.qualifier.qualifier}")
    print()
