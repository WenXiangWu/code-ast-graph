#!/usr/bin/env python3
"""
诊断：yuer-chatroom-service 中是否存在 openNoble 实现方法
Terminal 267-274
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", encoding="utf-8")
from src.storage.neo4j.storage import Neo4jStorage

s = Neo4jStorage()
if not s.connect():
    print("[ERROR] Neo4j 连接失败"); sys.exit(1)

IFACE_FQN = "com.yupaopao.yuer.chatroom.api.NobleRemoteService"

print("1. yuer-chatroom-service 中所有名为 openNoble 的方法:")
r = s.execute_query("""
    MATCH (proj:Project {name:'yuer-chatroom-service'})-[:CONTAINS]->(cls)
    MATCH (cls)-[:DECLARES]->(m:Method)
    WHERE m.name = 'openNoble'
    RETURN cls.fqn AS class_fqn, cls.name AS class_name,
           labels(cls) AS labels, m.signature AS method_sig
""")
for row in r:
    print(f"  [{'/'.join(row['labels'])}] {row['class_fqn']}.{row['method_name'] if 'method_name' in row else 'openNoble'}")
    print(f"      sig: {row['method_sig']}")
if not r:
    print("  (无)")

print()
print("2. 所有 IMPLEMENTS NobleRemoteService 的节点（跨项目）:")
r2 = s.execute_query("""
    MATCH (iface:INTERFACE {fqn: $fqn})
    OPTIONAL MATCH (cls)-[:IMPLEMENTS]->(iface)
    RETURN cls.fqn AS cls_fqn, labels(cls) AS labels
""", {"fqn": IFACE_FQN})
for row in r2:
    print(f"  {row}")
if not r2:
    print("  (无)")

print()
print("3. yuer-chatroom-service 中 Manager/Service 层级含 openNoble 的类:")
r3 = s.execute_query("""
    MATCH (proj:Project {name:'yuer-chatroom-service'})-[:CONTAINS]->(cls)
    MATCH (cls)-[:DECLARES]->(m:Method {name:'openNoble'})
    WHERE cls.arch_layer IN ['Manager','Service','Controller','Provider']
       OR cls.name ENDS WITH 'Impl' OR cls.name ENDS WITH 'ServiceImpl'
    RETURN cls.fqn, cls.name, cls.arch_layer, m.signature
""")
for row in r3:
    print(f"  {row}")
if not r3:
    print("  (无)")

print()
print("4. NobleController 在 yuer-chatroom-service 中是否存在 openNoble:")
r4 = s.execute_query("""
    MATCH (proj:Project {name:'yuer-chatroom-service'})-[:CONTAINS]->(cls)
    WHERE cls.name CONTAINS 'Noble'
    MATCH (cls)-[:DECLARES]->(m:Method)
    WHERE m.name = 'openNoble'
    RETURN cls.fqn, cls.name, labels(cls) AS labels, m.signature
""")
for row in r4:
    print(f"  {row}")
if not r4:
    print("  (无)")
