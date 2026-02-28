#!/usr/bin/env python3
"""诊断 NobleController 的实现关系 Terminal 267-274"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", encoding="utf-8")
from src.storage.neo4j.storage import Neo4jStorage

s = Neo4jStorage()
if not s.connect(): print("[ERROR]"); sys.exit(1)

print("1. 所有项目中的 NobleController / NobleRemoteService 节点:")
r = s.execute_query("""
    MATCH (proj:Project)-[:CONTAINS]->(cls)
    WHERE cls.name IN ['NobleController','NobleRemoteService']
    RETURN proj.name AS project, cls.fqn AS fqn,
           labels(cls) AS labels, cls.arch_layer AS arch_layer
    ORDER BY proj.name, cls.name
""")
for row in r:
    print(f"  [{'/'.join(row['labels'])}] {row['project']} | {row['fqn']} | layer={row['arch_layer']}")

print()
print("2. NobleController 的 IMPLEMENTS 关系:")
r2 = s.execute_query("""
    MATCH (cls)-[:IMPLEMENTS]->(iface)
    WHERE cls.name = 'NobleController'
    OPTIONAL MATCH (proj:Project)-[:CONTAINS]->(cls)
    RETURN proj.name AS project, cls.fqn AS class_fqn,
           iface.fqn AS interface_fqn, labels(iface) AS iface_labels
""")
for row in r2:
    print(f"  {row['project']} | {row['class_fqn']} IMPLEMENTS {row['interface_fqn']}")
if not r2: print("  (无)")

print()
print("3. 所有 DUBBO_CALLS 指向含'Noble'的接口:")
r3 = s.execute_query("""
    MATCH (m:Method)-[rel:DUBBO_CALLS]->(iface_m:Method)
    WHERE iface_m.signature CONTAINS 'Noble'
    MATCH (iface)-[:DECLARES]->(iface_m)
    OPTIONAL MATCH (proj:Project)-[:CONTAINS]->(iface)
    RETURN DISTINCT iface.fqn AS interface_fqn, iface_m.name AS method,
           proj.name AS iface_project, labels(iface) AS labels
""")
for row in r3:
    print(f"  [{'/'.join(row['labels'])}] {row['iface_project']} | {row['interface_fqn']}.{row['method']}")

print()
print("4. yuer-chatroom-service 中 NobleController 声明的方法:")
r4 = s.execute_query("""
    MATCH (proj:Project {name:'yuer-chatroom-service'})-[:CONTAINS]->(cls {name:'NobleController'})
    OPTIONAL MATCH (cls)-[:DECLARES]->(m:Method)
    RETURN cls.fqn AS class_fqn, labels(cls) AS labels,
           m.name AS method_name, m.signature AS method_sig
    ORDER BY m.name
""")
for row in r4:
    print(f"  [{'/'.join(row['labels'])}] {row['class_fqn']}.{row['method_name']}")
    print(f"      sig: {row['method_sig']}")
if not r4: print("  (无)")
