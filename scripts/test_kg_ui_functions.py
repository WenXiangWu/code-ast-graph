"""
测试知识图谱管理和查询功能
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

from src.storage.neo4j import Neo4jStorage
from src.services.scan_service import ScanService
from src.parsers.java import JavaParser
from src.inputs.filesystem_input import FileSystemCodeInput
import pandas as pd
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_neo4j_connection():
    """测试 Neo4j 连接"""
    print("=" * 60)
    print("测试 1: Neo4j 连接")
    print("=" * 60)
    
    client = Neo4jStorage()
    if client.connect():
        print("[OK] Neo4j 连接成功")
        return True
    else:
        print("[FAIL] Neo4j 连接失败")
        print("      请检查 Neo4j 是否运行，以及用户名密码是否正确")
        return False


def test_get_projects():
    """测试获取项目列表"""
    print("\n" + "=" * 60)
    print("测试 2: 获取项目列表（知识图谱管理）")
    print("=" * 60)
    
    client = Neo4jStorage()
    if not client.is_connected():
        if not client.connect():
            print("[SKIP] Neo4j 未连接，无法测试")
            return False
    
    try:
        # 使用新架构：直接查询 Neo4j
        result = client.execute_query("""
            MATCH (p:Project)
            RETURN p.name as name, COALESCE(p.path, '') as path
            ORDER BY p.name ASC
        """)
        
        import pandas as pd
        df = pd.DataFrame([
            {
                "项目名称": r.get('name'),
                "项目路径": r.get('path', ''),
                "状态": "已构建 ✅"
            }
            for r in result if r.get('name')
        ])
        print(f"\n[OK] 成功获取项目列表")
        print(f"   项目数量: {len(df)}")
        
        if not df.empty:
            print("\n   项目详情:")
            for idx, row in df.iterrows():
                print(f"   {idx + 1}. {row['项目名称']}")
                print(f"      路径: {row['项目路径']}")
                print(f"      状态: {row['状态']}")
        else:
            print("   [WARN] Neo4j 中没有项目")
        
        return True
    except Exception as e:
        print(f"[FAIL] 获取项目列表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_scanned_projects_list():
    """测试获取已扫描项目列表（用于查询页面）"""
    print("\n" + "=" * 60)
    print("测试 3: 获取已扫描项目列表（知识图谱查询）")
    print("=" * 60)
    
    client = Neo4jStorage()
    if not client.is_connected():
        if not client.connect():
            print("[SKIP] Neo4j 未连接，无法测试")
            return False
    
    try:
        # 使用新架构：直接查询 Neo4j
        result = client.execute_query("""
            MATCH (p:Project)
            RETURN p.name as name
            ORDER BY p.name ASC
        """)
        projects = [r['name'] for r in result if r.get('name')]
        print(f"\n[OK] 成功获取已扫描项目列表")
        print(f"   项目数量: {len(projects)}")
        
        if projects:
            print("\n   项目列表:")
            for idx, name in enumerate(projects, 1):
                print(f"   {idx}. {name}")
        else:
            print("   [WARN] 没有已扫描的项目")
        
        return True
    except Exception as e:
        print(f"[FAIL] 获取已扫描项目列表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_call_graph():
    """测试查询调用图"""
    print("\n" + "=" * 60)
    print("测试 4: 查询调用图")
    print("=" * 60)
    
    ui_manager = get_python_ast_ui_manager()
    
    if not ui_manager.is_initialized():
        print("[SKIP] Neo4j 未连接，无法测试")
        return False
    
    # 先获取项目列表
    projects = ui_manager.get_scanned_projects_list()
    if not projects:
        print("[SKIP] 没有可用的项目，跳过测试")
        return True
    
    project = projects[0]
    print(f"\n使用项目: {project}")
    
    try:
        # 查询调用图
        query = """
        MATCH (p:Project {name: $project})
        MATCH (from:Type)-[r:DEPENDS_ON|CALLS|IMPORTS]->(to:Type)
        WHERE from.project = $project AND (to.project = $project OR to.project IS NULL)
        RETURN from.fullName as from, to.fullName as to, type(r) as relType
        LIMIT 20
        """
        
        results = client.execute_query(query, {"project": project})
        
        print(f"\n[OK] 查询调用图成功")
        print(f"   找到 {len(results)} 个调用关系")
        
        if results:
            print("\n   调用关系示例（前5个）:")
            for idx, r in enumerate(results[:5], 1):
                from_class = r['from'].split('.')[-1] if r['from'] else 'Unknown'
                to_class = r['to'].split('.')[-1] if r['to'] else 'Unknown'
                rel_type = r.get('relType', 'DEPENDS_ON')
                print(f"   {idx}. {from_class} --[{rel_type}]--> {to_class}")
        
        return True
    except Exception as e:
        print(f"[FAIL] 查询调用图失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_impact_analysis():
    """测试影响面分析"""
    print("\n" + "=" * 60)
    print("测试 5: 影响面分析")
    print("=" * 60)
    
    ui_manager = get_python_ast_ui_manager()
    
    if not ui_manager.is_initialized():
        print("[SKIP] Neo4j 未连接，无法测试")
        return False
    
    # 先获取项目列表
    projects = ui_manager.get_scanned_projects_list()
    if not projects:
        print("[SKIP] 没有可用的项目，跳过测试")
        return True
    
    project = projects[0]
    print(f"\n使用项目: {project}")
    
    try:
        # 先找到一个类
        query_class = """
        MATCH (p:Project {name: $project})-[:CONTAINS]->(t:Type)
        RETURN t.name as name, t.fullName as fullName
        LIMIT 1
        """
        
        class_result = client.execute_query(query_class, {"project": project})
        
        if not class_result:
            print("[SKIP] 项目中找不到类，跳过测试")
            return True
        
        class_name = class_result[0].get('fullName') or class_result[0].get('name')
        print(f"使用类: {class_name}")
        
        # 查询影响面
        query = """
        MATCH (p:Project {name: $project})
        MATCH (target:Type)
        WHERE target.fullName = $class_name OR target.name = $class_name
        MATCH (dependent:Type)-[:DEPENDS_ON*1..3]->(target)
        WHERE dependent.project = $project
        RETURN DISTINCT dependent.fullName as affected_class, dependent.name as name
        LIMIT 20
        """
        
        results = client.execute_query(query, {
            "project": project,
            "class_name": class_name,
            "max_depth": 3
        })
        
        print(f"\n[OK] 影响面分析成功")
        print(f"   找到 {len(results)} 个受影响的类")
        
        if results:
            print("\n   受影响的类示例（前5个）:")
            for idx, r in enumerate(results[:5], 1):
                print(f"   {idx}. {r['name']} ({r['affected_class']})")
        
        return True
    except Exception as e:
        print(f"[FAIL] 影响面分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_statistics():
    """测试统计信息"""
    print("\n" + "=" * 60)
    print("测试 6: 获取统计信息")
    print("=" * 60)
    
    client = Neo4jStorage()
    if not client.is_connected():
        if not client.connect():
            print("[SKIP] Neo4j 未连接，无法测试")
            return False
    
    try:
        # 使用新架构：直接查询统计信息
        result = client.execute_query("""
            MATCH (p:Project)
            WITH count(DISTINCT p) as project_count
            MATCH (p2:Project)
            OPTIONAL MATCH (p2)-[:CONTAINS]->(t:Type)
            OPTIONAL MATCH (t)-[:DEPENDS_ON|CALLS|IMPORTS]->(dep)
            RETURN project_count,
                   count(DISTINCT t) as type_count,
                   count(dep) as dependency_count
        """)
        stats = result[0] if result else {'project_count': 0, 'type_count': 0, 'dependency_count': 0}
        print(f"\n[OK] 获取统计信息成功")
        print(f"   项目数: {stats.get('project_count', 0)}")
        print(f"   类型数: {stats.get('type_count', 0)}")
        print(f"   依赖关系数: {stats.get('dependency_count', 0)}")
        
        return True
    except Exception as e:
        print(f"[FAIL] 获取统计信息失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("知识图谱功能测试")
    print("=" * 60)
    
    results = []
    
    # 测试 1: Neo4j 连接
    results.append(("Neo4j 连接", test_neo4j_connection()))
    
    # 测试 2: 获取项目列表（管理页面）
    results.append(("获取项目列表（管理）", test_get_projects()))
    
    # 测试 3: 获取已扫描项目列表（查询页面）
    results.append(("获取已扫描项目列表（查询）", test_get_scanned_projects_list()))
    
    # 测试 4: 查询调用图
    results.append(("查询调用图", test_query_call_graph()))
    
    # 测试 5: 影响面分析
    results.append(("影响面分析", test_query_impact_analysis()))
    
    # 测试 6: 统计信息
    results.append(("统计信息", test_statistics()))
    
    # 输出测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {test_name}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！")
    else:
        print(f"\n[WARN] 有 {total - passed} 个测试失败，请检查日志")


if __name__ == "__main__":
    main()
