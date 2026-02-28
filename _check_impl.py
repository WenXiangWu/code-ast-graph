#!/usr/bin/env python3
"""深度查实现类 Terminal 267-274"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", encoding="utf-8")
from src.storage.neo4j.storage import Neo4jStorage

s = Neo4jStorage()
if not s.connect(): sys.exit(1)

PROJ = "yuer-chatroom-service"

print("1. yuer-chatroom-service 中所有 IMPLEMENTS 关系（全量）:")
r = s.execute_query("""
    MATCH (proj:Project {name:$proj})-[:CONTAINS]->(cls:CLASS)
    MATCH (cls)-[:IMPLEMENTS]->(iface)
    WHERE iface.name CONTAINS 'Noble' OR iface.name CONTAINS 'Remote'
    RETURN cls.fqn AS class_fqn, iface.fqn AS iface_fqn
    ORDER BY cls.name
""", {"proj": PROJ})
for row in r:
    print(f"  {row['class_fqn']} IMPLEMENTS {row['iface_fqn']}")
if not r:
    print("  (无 Noble/Remote 相关 IMPLEMENTS)")

print()
print("2. yuer-chatroom-service 中名字含 Facade/Impl/Provider 的 Noble 相关类:")
r2 = s.execute_query("""
    MATCH (proj:Project {name:$proj})-[:CONTAINS]->(cls:CLASS)
    WHERE (cls.name CONTAINS 'Facade' OR cls.name CONTAINS 'Provider'
           OR cls.name ENDS WITH 'Impl')
      AND cls.name CONTAINS 'Noble'
    RETURN cls.fqn AS fqn, cls.arch_layer AS layer
""", {"proj": PROJ})
for row in r2:
    print(f"  [{row['layer']}] {row['fqn']}")
if not r2:
    print("  (无)")

print()
print("3. NobleRemoteService 接口上所有方法 及 IMPLEMENTS 情况（全库）:")
r3 = s.execute_query("""
    MATCH (iface:INTERFACE {fqn:'com.yupaopao.yuer.chatroom.api.NobleRemoteService'})
    OPTIONAL MATCH (cls:CLASS)-[:IMPLEMENTS]->(iface)
    OPTIONAL MATCH (proj:Project)-[:CONTAINS]->(cls)
    RETURN cls.fqn AS impl_fqn, proj.name AS impl_proj
""")
for row in r3:
    print(f"  impl: {row['impl_proj']} | {row['impl_fqn']}")
if all(r['impl_fqn'] is None for r in r3):
    print("  → 全库无任何 CLASS IMPLEMENTS 此接口")

print()
print("4. yuer-chatroom-service 中有 CALLS 到 NobleManager.changeNobleInfo 的方法:")
r4 = s.execute_query("""
    MATCH (caller:Method)-[:CALLS]->(m:Method)
    WHERE m.signature CONTAINS 'NobleManager.changeNobleInfo'
    OPTIONAL MATCH (proj:Project)-[:CONTAINS]->(cls)
    WHERE (cls)-[:DECLARES]->(caller)
    RETURN DISTINCT caller.signature AS caller_sig, proj.name AS proj
    LIMIT 10
""")
for row in r4:
    print(f"  [{row['proj']}] {row['caller_sig']}")
if not r4:
    print("  (无)")

print()
print("5. 接口 NobleRemoteService 的 openNoble 方法是否有被 CALLS（任何方向）:")
r5 = s.execute_query("""
    MATCH (m:Method)
    WHERE m.signature CONTAINS 'NobleRemoteService.openNoble'
    OPTIONAL MATCH (caller)-[:CALLS]->(m)
    OPTIONAL MATCH (m)-[:CALLS]->(callee)
    RETURN m.signature AS sig,
           collect(DISTINCT caller.signature)[..3] AS callers,
           collect(DISTINCT callee.signature)[..3] AS callees
""")
for row in r5:
    print(f"  sig: {row['sig']}")
    print(f"    callers: {row['callers']}")
    print(f"    callees: {row['callees']}")
