#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理错误的 Java 标准库方法调用"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage(uri="bolt://localhost:17687", user="neo4j", password="jqassistant123")
storage.connect()

print("=" * 100)
print("清理错误的 Java 标准库方法调用")
print("=" * 100)

# Java 标准库常见方法
stdlib_methods = [
    'stream', 'collect', 'map', 'filter', 'forEach', 'reduce', 'flatMap',
    'orElse', 'orElseGet', 'ifPresent', 'isPresent', 'get', 'of', 'empty',
    'equals', 'hashCode', 'toString', 'clone', 'finalize',
    'wait', 'notify', 'notifyAll', 'getClass',
    'findFirst', 'findAny', 'anyMatch', 'allMatch', 'noneMatch',
    'sorted', 'distinct', 'limit', 'skip', 'peek', 'count',
    'max', 'min', 'sum', 'average', 'toArray',
    'join', 'split', 'replace', 'substring', 'trim', 'toLowerCase', 'toUpperCase',
    'contains', 'startsWith', 'endsWith', 'indexOf', 'lastIndexOf',
    'add', 'remove', 'clear', 'size', 'isEmpty', 'iterator',
    'put', 'putAll', 'containsKey', 'containsValue', 'keySet', 'values', 'entrySet',
    'equalsIgnoreCase', 'compareTo', 'compareToIgnoreCase'
]

# 1. 查找错误的调用
print("\n1. 查找错误的 Internal 调用:")
result = storage.execute_query("""
    MATCH (m:Method)-[r:CALLS]->(called:Method)
    WHERE r.call_type = 'Internal'
      AND called.name IN $stdlib_methods
    RETURN count(r) as count
""", {'stdlib_methods': stdlib_methods})

print(f"  找到 {result[0]['count']} 个错误的调用")

# 2. 删除这些调用关系
if result[0]['count'] > 0:
    print("\n2. 删除错误的调用关系...")
    delete_result = storage.execute_query("""
        MATCH (m:Method)-[r:CALLS]->(called:Method)
        WHERE r.call_type = 'Internal'
          AND called.name IN $stdlib_methods
        DELETE r
        RETURN count(r) as deleted_count
    """, {'stdlib_methods': stdlib_methods})
    
    print(f"  [OK] 已删除 {delete_result[0]['deleted_count']} 个错误的调用关系")

# 3. 清理孤立的方法节点（没有任何关系的简化签名方法）
print("\n3. 清理孤立的方法节点:")
result = storage.execute_query("""
    MATCH (m:Method)
    WHERE m.signature ENDS WITH '(...)'
      AND NOT (m)<-[:CALLS]-()
      AND NOT (m)-[:CALLS]->()
      AND NOT (m)<-[:DUBBO_CALLS]-()
      AND NOT (m)<-[:DECLARES]-()
    DELETE m
    RETURN count(m) as deleted_count
""")

if result:
    print(f"  [OK] 已删除 {result[0]['deleted_count']} 个孤立的方法节点")

# 4. 统计清理后的 Unknown 节点
print("\n4. 统计清理后的 Unknown 节点:")
result = storage.execute_query("""
    MATCH (c)
    WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER)
    AND NOT (:Project)-[:CONTAINS]->(c)
    RETURN count(c) as count
""")
print(f"  剩余 Unknown 节点: {result[0]['count']} 个")

print("\n" + "=" * 100)
print("清理完成")
print("=" * 100)
