"""修复 Neo4j 中因 FQN 冲突导致丢失的 IMPLEMENTS 关系"""
import sys
sys.path.insert(0, 'd:/cursor/code-ast-graph')
from dotenv import load_dotenv
load_dotenv('d:/cursor/code-ast-graph/.env', encoding='utf-8')
from src.storage.neo4j.storage import Neo4jStorage

s = Neo4jStorage()
s.connect()

FIXES = [
    # (CLASS FQN, INTERFACE FQN)
    (
        'com.yupaopao.chatroom.controller.NobleController',
        'com.yupaopao.yuer.chatroom.api.NobleRemoteService',
    ),
]

for cls_fqn, iface_fqn in FIXES:
    # 检查节点是否存在
    r_cls = s.execute_query(
        "MATCH (c:CLASS {fqn: $fqn}) RETURN c.fqn AS fqn",
        {'fqn': cls_fqn}
    )
    r_iface = s.execute_query(
        "MATCH (i:INTERFACE {fqn: $fqn}) RETURN i.fqn AS fqn",
        {'fqn': iface_fqn}
    )
    if not r_cls:
        print(f"[SKIP] CLASS 节点不存在: {cls_fqn}")
        continue
    if not r_iface:
        print(f"[SKIP] INTERFACE 节点不存在: {iface_fqn}")
        continue

    # 检查是否已有 IMPLEMENTS
    existing = s.execute_query("""
        MATCH (c:CLASS {fqn: $cls_fqn})-[:IMPLEMENTS]->(i:INTERFACE {fqn: $iface_fqn})
        RETURN count(*) AS cnt
    """, {'cls_fqn': cls_fqn, 'iface_fqn': iface_fqn})
    if existing and existing[0]['cnt'] > 0:
        print(f"[SKIP] IMPLEMENTS 已存在: {cls_fqn} --> {iface_fqn}")
        continue

    # 创建 IMPLEMENTS 关系
    s.execute_query("""
        MATCH (c:CLASS {fqn: $cls_fqn})
        MATCH (i:INTERFACE {fqn: $iface_fqn})
        MERGE (c)-[:IMPLEMENTS]->(i)
    """, {'cls_fqn': cls_fqn, 'iface_fqn': iface_fqn})
    print(f"[FIXED] 已创建 IMPLEMENTS: {cls_fqn} --> {iface_fqn}")

    # 同时确保 yuer-chatroom-service CONTAINS 这个 CLASS
    s.execute_query("""
        MATCH (proj:Project {name: 'yuer-chatroom-service'})
        MATCH (c:CLASS {fqn: $cls_fqn})
        MERGE (proj)-[:CONTAINS]->(c)
    """, {'cls_fqn': cls_fqn})
    print(f"[FIXED] 已添加 CONTAINS: yuer-chatroom-service --> {cls_fqn}")

print()
print("=== 验证修复结果 ===")
r = s.execute_query("""
    MATCH (c:CLASS {fqn:'com.yupaopao.chatroom.controller.NobleController'})
    OPTIONAL MATCH (c)-[:IMPLEMENTS]->(iface)
    OPTIONAL MATCH (proj:Project)-[:CONTAINS]->(c)
    RETURN proj.name AS project, iface.fqn AS implements
""")
for row in r:
    print(f"  project={row['project']}  implements={row['implements']}")

s.disconnect()
print("完成")
