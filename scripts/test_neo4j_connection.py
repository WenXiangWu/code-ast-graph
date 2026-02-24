"""
诊断 Neo4j 连接问题
"""

import sys
import os
from pathlib import Path

# 设置 UTF-8 编码（Windows 兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

import socket
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

print("=" * 60)
print("Neo4j 连接诊断")
print("=" * 60)

# 1. 检查环境变量
print("\n1. 检查环境变量配置:")
uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', 'password')
print(f"   URI: {uri}")
print(f"   User: {user}")
print(f"   Password: {'*' * len(password) if password else 'None'}")

# 2. 检查端口是否开放
print("\n2. 检查端口连接:")
try:
    if uri.startswith('bolt://'):
        host_port = uri.replace('bolt://', '').split(':')
        host = host_port[0] if len(host_port) > 0 else 'localhost'
        port = int(host_port[1]) if len(host_port) > 1 else 7687
    else:
        host = 'localhost'
        port = 7687
    
    print(f"   尝试连接 {host}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex((host, port))
    sock.close()
    
    if result == 0:
        print(f"   [OK] 端口 {port} 可以连接")
    else:
        print(f"   [FAIL] 端口 {port} 无法连接（错误代码: {result}）")
        print(f"   请检查:")
        print(f"   - Neo4j 服务是否运行")
        print(f"   - 端口是否正确")
        print(f"   - 防火墙是否阻止连接")
except Exception as e:
    print(f"   [ERROR] 检查端口时出错: {e}")

# 3. 尝试连接 Neo4j
print("\n3. 尝试连接 Neo4j:")
try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    # 测试连接
    with driver.session() as session:
        result = session.run("RETURN 1 as test")
        test_value = result.single()
        if test_value:
            print(f"   [OK] Neo4j 连接成功！")
            print(f"   测试查询返回: {test_value}")
            
            # 查询项目数量
            try:
                result = session.run("MATCH (p:Project) RETURN count(p) as count")
                count = result.single()['count']
                print(f"\n4. 查询项目数据:")
                print(f"   [OK] Neo4j 中有 {count} 个项目")
                
                if count > 0:
                    # 列出前5个项目
                    result = session.run("MATCH (p:Project) RETURN p.name as name LIMIT 5")
                    print(f"   项目列表（前5个）:")
                    for record in result:
                        print(f"     - {record['name']}")
            except Exception as e:
                print(f"   [WARN] 查询项目数据失败: {e}")
            
            driver.close()
        else:
            print(f"   [FAIL] 连接成功但测试查询失败")
            driver.close()
except AuthError as e:
    print(f"   [FAIL] 认证失败: {e}")
    print(f"\n   可能的原因:")
    print(f"   - 用户名或密码不正确")
    print(f"   - Neo4j 密码已更改")
    print(f"   - 请检查 .env 文件中的 NEO4J_PASSWORD")
    print(f"\n   建议:")
    print(f"   1. 访问 http://localhost:7474 使用 Neo4j Browser")
    print(f"   2. 尝试使用当前配置登录")
    print(f"   3. 如果失败，重置密码或更新 .env 文件")
except ServiceUnavailable as e:
    print(f"   [FAIL] 服务不可用: {e}")
    print(f"\n   可能的原因:")
    print(f"   - Neo4j 服务未运行")
    print(f"   - URI 配置错误")
    print(f"\n   建议:")
    print(f"   1. 检查 Neo4j 是否运行: docker ps | grep neo4j")
    print(f"   2. 启动 Neo4j: docker start <neo4j_container>")
    print(f"   3. 或访问 http://localhost:7474 检查服务状态")
except Exception as e:
    print(f"   [FAIL] 连接失败: {e}")
    print(f"   错误类型: {type(e).__name__}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
