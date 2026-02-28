#!/usr/bin/env python3
"""
诊断脚本：查明 Dubbo 接口实现链为何 impl_signature=NULL
Terminal 267-274
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", encoding="utf-8")

from src.storage.neo4j.storage import Neo4jStorage

storage = Neo4jStorage()
if not storage.connect():
    print("[ERROR] Neo4j 连接失败")
    sys.exit(1)

METHOD_SIG = ("com.yupaopao.chatroom.official.room.web.controller"
              ".NobleController.openNoble(MobileContext,NobleOpenRequest)")

print("=" * 60)
print("1. 查询 DUBBO_CALLS 边 及目标接口信息")
print("=" * 60)
r1 = storage.execute_query("""
    MATCH (m:Method {signature: $sig})-[rel:DUBBO_CALLS]->(iface_method:Method)
    MATCH (iface:INTERFACE)-[:DECLARES]->(iface_method)
    RETURN
        iface.fqn          AS dubbo_interface,
        iface_method.name  AS dubbo_method_name,
        iface_method.signature AS iface_method_sig,
        rel.via_field      AS via_field
""", {"sig": METHOD_SIG})
for row in r1:
    print(json.dumps(dict(row), ensure_ascii=False, indent=2))

print()
print("=" * 60)
print("2. 查询实现类（CLASS IMPLEMENTS 上述接口）")
print("=" * 60)
for row in r1:
    iface_fqn = row["dubbo_interface"]
    r2 = storage.execute_query("""
        MATCH (iface:INTERFACE {fqn: $fqn})
        OPTIONAL MATCH (impl:CLASS)-[:IMPLEMENTS]->(iface)
        OPTIONAL MATCH (proj:Project)-[:CONTAINS]->(impl)
        RETURN
            impl.fqn   AS impl_class_fqn,
            impl.name  AS impl_class_name,
            proj.name  AS impl_project
    """, {"fqn": iface_fqn})
    for r in r2:
        print(json.dumps(dict(r), ensure_ascii=False, indent=2))

print()
print("=" * 60)
print("3. 查询实现类声明的方法（DECLARES）")
print("=" * 60)
for row in r1:
    iface_fqn = row["dubbo_interface"]
    target_method = row["dubbo_method_name"]
    r3 = storage.execute_query("""
        MATCH (iface:INTERFACE {fqn: $fqn})
        MATCH (impl:CLASS)-[:IMPLEMENTS]->(iface)
        OPTIONAL MATCH (impl)-[:DECLARES]->(m:Method)
        RETURN
            impl.fqn   AS impl_class_fqn,
            m.name     AS method_name,
            m.signature AS method_sig
        ORDER BY m.name
    """, {"fqn": iface_fqn})
    for r in r3:
        marker = " <<<< TARGET" if r["method_name"] == target_method else ""
        print(f"  {r['impl_class_fqn']}.{r['method_name']}{marker}")
        if r["method_sig"]:
            print(f"      sig: {r['method_sig']}")

print()
print("=" * 60)
print("4. 完整 Dubbo 查询（修复后 WITH 版本）")
print("=" * 60)
r4 = storage.execute_query("""
    MATCH (m:Method {signature: $sig})-[dubbo_rel:DUBBO_CALLS]->(dubbo_iface_method:Method)
    MATCH (dubbo_iface:INTERFACE)-[:DECLARES]->(dubbo_iface_method)
    OPTIONAL MATCH (impl_class:CLASS)-[:IMPLEMENTS]->(dubbo_iface)
    WITH dubbo_iface, dubbo_iface_method, dubbo_rel, impl_class
    OPTIONAL MATCH (impl_class)-[:DECLARES]->(impl_method:Method)
        WHERE impl_method.name = dubbo_iface_method.name
    OPTIONAL MATCH (impl_project:Project)-[:CONTAINS]->(impl_class)
    OPTIONAL MATCH (iface_project:Project)-[:CONTAINS]->(dubbo_iface)
    RETURN DISTINCT
        dubbo_iface.fqn        AS dubbo_interface,
        dubbo_iface_method.name AS dubbo_method,
        dubbo_rel.via_field    AS via_field,
        impl_method.signature  AS impl_signature,
        impl_project.name      AS impl_project,
        impl_class.fqn         AS impl_class_fqn,
        impl_class.name        AS impl_class_name,
        iface_project.name     AS iface_project
""", {"sig": METHOD_SIG})
for r in r4:
    print(json.dumps(dict(r), ensure_ascii=False, indent=2))

storage.close()
