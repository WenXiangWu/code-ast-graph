#!/usr/bin/env python3
"""直接查 Neo4j Terminal 267-274"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", encoding="utf-8")
from src.storage.neo4j.storage import Neo4jStorage

s = Neo4jStorage()
if not s.connect(): print("[ERROR]"); sys.exit(1)

print("1. yuer-chatroom-service 下所有 CLASS 节点数量及样例:")
r = s.execute_query("""
    MATCH (p:Project {name:'yuer-chatroom-service'})-[:CONTAINS]->(cls:CLASS)
    RETURN count(cls) AS total
""")
print(f"  CLASS 总数: {r[0]['total'] if r else 0}")

r2 = s.execute_query("""
    MATCH (p:Project {name:'yuer-chatroom-service'})-[:CONTAINS]->(cls:CLASS)
    RETURN cls.name AS name, cls.fqn AS fqn
    ORDER BY cls.name LIMIT 20
""")
for row in r2:
    print(f"  {row['fqn']}")

print()
print("2. yuer-chatroom-service 下名字含 Noble 的所有节点:")
r3 = s.execute_query("""
    MATCH (p:Project {name:'yuer-chatroom-service'})-[:CONTAINS]->(cls)
    WHERE cls.name CONTAINS 'Noble'
    RETURN cls.fqn AS fqn, labels(cls) AS labels
""")
for row in r3:
    print(f"  [{'/'.join(row['labels'])}] {row['fqn']}")
if not r3: print("  (无)")

print()
print("3. 所有项目中名字含 NobleController 的 CLASS:")
r4 = s.execute_query("""
    MATCH (p:Project)-[:CONTAINS]->(cls:CLASS)
    WHERE cls.name CONTAINS 'NobleController'
    RETURN p.name AS project, cls.fqn AS fqn, labels(cls) AS labels
""")
for row in r4:
    print(f"  {row['project']} | [{'/'.join(row['labels'])}] {row['fqn']}")
if not r4: print("  (无)")

print()
print("4. yuer-chatroom-service 中 IMPLEMENTS NobleRemoteService 的类（任何包路径）:")
r5 = s.execute_query("""
    MATCH (cls)-[:IMPLEMENTS]->(iface)
    WHERE iface.name = 'NobleRemoteService'
    OPTIONAL MATCH (p:Project)-[:CONTAINS]->(cls)
    RETURN p.name AS project, cls.fqn AS fqn, labels(cls) AS labels, iface.fqn AS iface_fqn
""")
for row in r5:
    print(f"  {row['project']} | {row['fqn']} IMPLEMENTS {row['iface_fqn']}")
if not r5: print("  (无)")

print()
print("5. 关键：查 yuer-chatroom-service 项目下有哪些标签类型的节点:")
r6 = s.execute_query("""
    MATCH (p:Project {name:'yuer-chatroom-service'})-[:CONTAINS]->(n)
    RETURN DISTINCT labels(n) AS labels, count(n) AS cnt
    ORDER BY cnt DESC
""")
for row in r6:
    print(f"  {row['labels']} → {row['cnt']} 个")
