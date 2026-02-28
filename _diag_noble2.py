import sys
sys.path.insert(0, 'd:/cursor/code-ast-graph')
from dotenv import load_dotenv
load_dotenv('d:/cursor/code-ast-graph/.env', encoding='utf-8')
from src.storage.neo4j.storage import Neo4jStorage

s = Neo4jStorage()
s.connect()

METHOD_SIG = ('com.yupaopao.chatroom.official.room.web.controller'
              '.NobleController.openNoble(MobileContext,NobleOpenRequest)')

print('=== 验证当前 Dubbo 查询（含修复后的逻辑）===')
r = s.execute_query("""
    MATCH (m:Method {signature: $sig})-[dubbo_rel:DUBBO_CALLS]->(dubbo_iface_method:Method)
    MATCH (dubbo_iface:INTERFACE)-[:DECLARES]->(dubbo_iface_method)
    OPTIONAL MATCH (iface_project:Project)-[:CONTAINS]->(dubbo_iface)

    OPTIONAL MATCH (impl_class_via_impl:CLASS)-[:IMPLEMENTS]->(dubbo_iface)
    WITH dubbo_iface, dubbo_iface_method, dubbo_rel, iface_project, impl_class_via_impl
    OPTIONAL MATCH (impl_class_via_impl)-[:DECLARES]->(impl_method_via_impl:Method)
        WHERE impl_method_via_impl.name = dubbo_iface_method.name

    WITH dubbo_iface, dubbo_iface_method, dubbo_rel, iface_project,
         impl_class_via_impl, impl_method_via_impl
    OPTIONAL MATCH (iface_project)-[:CONTAINS]->(fallback_class:CLASS)-[:DECLARES]->(fallback_method:Method)
        WHERE impl_class_via_impl IS NULL
          AND fallback_method.name = dubbo_iface_method.name

    WITH dubbo_iface, dubbo_iface_method, dubbo_rel, iface_project,
         COALESCE(impl_class_via_impl, fallback_class) AS impl_class,
         COALESCE(impl_method_via_impl, fallback_method) AS impl_method

    OPTIONAL MATCH (impl_project:Project)-[:CONTAINS]->(impl_class)
    RETURN DISTINCT
        dubbo_iface.fqn as dubbo_interface,
        dubbo_iface_method.name as dubbo_method,
        impl_method.signature as impl_signature,
        impl_project.name as impl_project,
        impl_class.fqn as impl_class_fqn,
        iface_project.name as iface_project
""", {'sig': METHOD_SIG})

for row in r:
    print(f"  dubbo_interface={row['dubbo_interface']}")
    print(f"  iface_project={row['iface_project']}")
    print(f"  impl_class={row['impl_class_fqn']}  impl_project={row['impl_project']}")
    print(f"  impl_signature={row['impl_signature']}")
    print()

if not r:
    print('  (未找到任何 Dubbo 调用)')

print()
print('=== 直接验证 IMPLEMENTS 关系 ===')
r2 = s.execute_query("""
    MATCH (c:CLASS {fqn:'com.yupaopao.chatroom.controller.NobleController'})-[:IMPLEMENTS]->(i)
    RETURN c.fqn AS cls, i.fqn AS iface
""")
for row in r2:
    print(f"  {row['cls']} --> {row['iface']}")
if not r2:
    print('  (无 IMPLEMENTS 关系)')

s.disconnect()
