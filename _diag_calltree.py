"""诊断全库 CALLS 关系分布"""
import sys
sys.path.insert(0, 'd:/cursor/code-ast-graph')
from dotenv import load_dotenv
load_dotenv('d:/cursor/code-ast-graph/.env', encoding='utf-8')
from src.storage.neo4j.storage import Neo4jStorage

s = Neo4jStorage()
s.connect()

print('=== 1. yuer-chatroom-service 下有多少方法有 CALLS 关系 ===')
r1 = s.execute_query("""
    MATCH (proj:Project {name:'yuer-chatroom-service'})-[:CONTAINS]->(cls)
    MATCH (cls)-[:DECLARES]->(m:Method)-[:CALLS]->()
    RETURN count(DISTINCT m) AS methods_with_calls
""")
print(f"  有 CALLS 的方法数: {r1[0]['methods_with_calls'] if r1 else 0}")

print()
print('=== 2. official-room-pro-web 下有多少方法有 CALLS 关系 ===')
r2 = s.execute_query("""
    MATCH (proj:Project {name:'official-room-pro-web'})-[:CONTAINS]->(cls)
    MATCH (cls)-[:DECLARES]->(m:Method)-[:CALLS]->()
    RETURN count(DISTINCT m) AS methods_with_calls
""")
print(f"  有 CALLS 的方法数: {r2[0]['methods_with_calls'] if r2 else 0}")

print()
print('=== 3. 全库中所有项目的 CALLS 关系数量 ===')
r3 = s.execute_query("""
    MATCH (proj:Project)-[:CONTAINS]->(cls)-[:DECLARES]->(m:Method)-[:CALLS]->(called)
    RETURN proj.name AS project, count(*) AS calls_count
    ORDER BY calls_count DESC
    LIMIT 20
""")
for row in r3:
    print(f"  {row['project']}: {row['calls_count']} CALLS")
if not r3:
    print('  (全库没有任何 CALLS 关系!)')

print()
print('=== 4. 全库 CALLS 关系总数 ===')
r4 = s.execute_query("MATCH ()-[r:CALLS]->() RETURN count(r) AS total")
print(f"  总数: {r4[0]['total'] if r4 else 0}")

s.disconnect()
