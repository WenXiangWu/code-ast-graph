"""修复 NobleController 的 CONTAINS 归属：yuer-chatroom-pro-web -> yuer-chatroom-service"""
import sys
sys.path.insert(0, 'd:/cursor/code-ast-graph')
from dotenv import load_dotenv
load_dotenv('d:/cursor/code-ast-graph/.env', encoding='utf-8')
from src.storage.neo4j.storage import Neo4jStorage

s = Neo4jStorage()
s.connect()

CLS_FQN = 'com.yupaopao.chatroom.controller.NobleController'

# 1. 删除错误的 CONTAINS（yuer-chatroom-pro-web）
s.execute_query("""
    MATCH (proj:Project {name:'yuer-chatroom-pro-web'})-[r:CONTAINS]->(c:CLASS {fqn: $fqn})
    DELETE r
""", {'fqn': CLS_FQN})
print(f"[FIX] 已删除 yuer-chatroom-pro-web -[:CONTAINS]-> {CLS_FQN}")

# 2. 创建正确的 CONTAINS（yuer-chatroom-service）
s.execute_query("""
    MATCH (proj:Project {name:'yuer-chatroom-service'})
    MATCH (c:CLASS {fqn: $fqn})
    MERGE (proj)-[:CONTAINS]->(c)
""", {'fqn': CLS_FQN})
print(f"[FIX] 已创建 yuer-chatroom-service -[:CONTAINS]-> {CLS_FQN}")

# 3. 验证结果
r = s.execute_query("""
    MATCH (c:CLASS {fqn: $fqn})
    OPTIONAL MATCH (proj:Project)-[:CONTAINS]->(c)
    OPTIONAL MATCH (c)-[:IMPLEMENTS]->(iface)
    RETURN proj.name AS project, iface.fqn AS implements
""", {'fqn': CLS_FQN})
print("\n=== 验证结果 ===")
for row in r:
    print(f"  project={row['project']}  implements={row['implements']}")

s.disconnect()
print("完成")
