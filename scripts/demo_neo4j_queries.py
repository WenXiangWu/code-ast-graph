#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Neo4j知识图谱查询示例
演示三种场景：
1. 查询接口定义和实现
2. 追踪 Dubbo 调用关系
3. 分析模块间的依赖关系
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.neo4j import Neo4jStorage
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demo_interface_queries(client):
    """场景1: 查询接口定义和实现"""
    logger.info("=" * 80)
    logger.info("场景1: 查询接口定义和实现")
    logger.info("=" * 80)
    
    # 示例1.1: 查找所有接口及其实现的类
    logger.info("\n【示例1.1】查找所有接口及其实现的类")
    logger.info("-" * 80)
    query1 = """
    MATCH (iface:Type)
    WHERE iface.kind = 'INTERFACE' OR iface.is_interface = true
    OPTIONAL MATCH (impl:Type)-[:IMPLEMENTS]->(iface)
    RETURN
      iface.fqn AS InterfaceFQN,
      iface.name AS InterfaceName,
      iface.file_path AS InterfaceFilePath,
      COLLECT(DISTINCT impl.fqn) AS ImplementingClasses,
      SIZE(COLLECT(DISTINCT impl.fqn)) AS ImplementationCount
    ORDER BY ImplementationCount DESC, InterfaceFQN
    LIMIT 20
    """
    
    try:
        results = client.execute_query(query1)
        logger.info(f"找到 {len(results)} 个接口（显示前20个）:\n")
        for i, record in enumerate(results, 1):
            impl_classes = [c for c in record['ImplementingClasses'] if c]
            logger.info(f"{i}. 接口: {record['InterfaceName']}")
            logger.info(f"   FQN: {record['InterfaceFQN']}")
            logger.info(f"   实现类数量: {record['ImplementationCount']}")
            if impl_classes:
                logger.info(f"   实现类: {', '.join(impl_classes[:3])}")
                if len(impl_classes) > 3:
                    logger.info(f"   ... 还有 {len(impl_classes) - 3} 个实现类")
            else:
                logger.info("   实现类: 无")
            logger.info("")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
    
    # 示例1.2: 查找特定接口的所有实现（以router-gateway-api中的接口为例）
    logger.info("\n【示例1.2】查找特定接口的所有实现")
    logger.info("-" * 80)
    query2 = """
    MATCH (iface:Type)
    WHERE iface.kind = 'INTERFACE' 
      AND iface.fqn CONTAINS 'chatroom.router.gateway'
    MATCH (impl:Type)-[:IMPLEMENTS]->(iface)
    RETURN
      iface.fqn AS InterfaceFQN,
      iface.name AS InterfaceName,
      impl.fqn AS ImplementingClassFQN,
      impl.name AS ImplementingClassName,
      impl.file_path AS ImplementingClassFilePath
    ORDER BY InterfaceFQN, impl.fqn
    LIMIT 10
    """
    
    try:
        results = client.execute_query(query2)
        if results:
            logger.info(f"找到 {len(results)} 个接口实现关系:\n")
            for i, record in enumerate(results, 1):
                logger.info(f"{i}. 接口: {record['InterfaceName']} ({record['InterfaceFQN']})")
                logger.info(f"   实现类: {record['ImplementingClassName']} ({record['ImplementingClassFQN']})")
                logger.info(f"   文件: {record['ImplementingClassFilePath']}")
                logger.info("")
        else:
            logger.info("未找到匹配的接口实现关系")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
    
    # 示例1.3: 查找接口的所有方法定义
    logger.info("\n【示例1.3】查找接口的所有方法定义")
    logger.info("-" * 80)
    query3 = """
    MATCH (iface:Type)
    WHERE iface.kind = 'INTERFACE'
    MATCH (iface)-[:DECLARES]->(m:Method)
    RETURN
      iface.fqn AS InterfaceFQN,
      iface.name AS InterfaceName,
      m.name AS MethodName,
      m.signature AS MethodSignature,
      m.return_type AS ReturnType,
      m.parameter_count AS ParameterCount
    ORDER BY InterfaceFQN, m.name
    LIMIT 15
    """
    
    try:
        results = client.execute_query(query3)
        logger.info(f"找到 {len(results)} 个接口方法（显示前15个）:\n")
        current_interface = None
        for record in results:
            if current_interface != record['InterfaceFQN']:
                current_interface = record['InterfaceFQN']
                logger.info(f"\n接口: {record['InterfaceName']} ({record['InterfaceFQN']})")
            logger.info(f"  - {record['MethodName']}({record['ParameterCount']} 参数) -> {record['ReturnType']}")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)


def demo_dubbo_queries(client):
    """场景2: 追踪 Dubbo 调用关系"""
    logger.info("\n" + "=" * 80)
    logger.info("场景2: 追踪 Dubbo 调用关系")
    logger.info("=" * 80)
    
    # 示例2.1: 查找所有 Dubbo 调用方及其调用的 Dubbo 服务
    logger.info("\n【示例2.1】查找所有 Dubbo 调用方及其调用的 Dubbo 服务")
    logger.info("-" * 80)
    query1 = """
    MATCH (caller:Type)-[calls:DUBBO_CALLS]->(service:Type)
    RETURN
      caller.fqn AS CallerFQN,
      caller.name AS CallerName,
      calls.field_name AS CalledThroughField,
      service.fqn AS ServiceFQN,
      service.name AS ServiceName,
      service.kind AS ServiceKind
    ORDER BY CallerFQN, ServiceFQN
    """
    
    try:
        results = client.execute_query(query1)
        logger.info(f"找到 {len(results)} 个Dubbo调用关系:\n")
        for i, record in enumerate(results, 1):
            logger.info(f"{i}. 调用方: {record['CallerName']} ({record['CallerFQN']})")
            logger.info(f"   通过字段: {record['CalledThroughField']}")
            logger.info(f"   调用服务: {record['ServiceName']} ({record['ServiceFQN']})")
            logger.info(f"   服务类型: {record['ServiceKind']}")
            logger.info("")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
    
    # 示例2.2: 查找特定 Dubbo 服务接口的提供者
    logger.info("\n【示例2.2】查找 Dubbo 服务接口的提供者")
    logger.info("-" * 80)
    query2 = """
    MATCH (service_interface:Type)
    MATCH (provider:Type)-[:DUBBO_PROVIDES]->(service_interface)
    RETURN
      service_interface.fqn AS ServiceInterfaceFQN,
      service_interface.name AS ServiceInterfaceName,
      provider.fqn AS ServiceProviderFQN,
      provider.name AS ServiceProviderName,
      provider.file_path AS ServiceProviderFilePath
    ORDER BY ServiceInterfaceFQN
    """
    
    try:
        results = client.execute_query(query2)
        if results:
            logger.info(f"找到 {len(results)} 个Dubbo服务提供关系:\n")
            for i, record in enumerate(results, 1):
                logger.info(f"{i}. 服务接口: {record['ServiceInterfaceName']} ({record['ServiceInterfaceFQN']})")
                logger.info(f"   提供者: {record['ServiceProviderName']} ({record['ServiceProviderFQN']})")
                logger.info(f"   文件: {record['ServiceProviderFilePath']}")
                logger.info("")
        else:
            logger.info("未找到Dubbo服务提供关系")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
    
    # 示例2.3: 查找某个类调用的所有 Dubbo 服务
    logger.info("\n【示例2.3】查找某个类调用的所有 Dubbo 服务")
    logger.info("-" * 80)
    query3 = """
    MATCH (caller:Type)-[r:DUBBO_CALLS]->(service:Type)
    WHERE caller.fqn CONTAINS 'chatroom.router'
    RETURN
      caller.fqn AS CallerFQN,
      caller.name AS CallerName,
      COLLECT({
        field: r.field_name,
        service: service.name,
        serviceFQN: service.fqn
      }) AS CalledServices
    ORDER BY CallerFQN
    LIMIT 10
    """
    
    try:
        results = client.execute_query(query3)
        if results:
            logger.info(f"找到 {len(results)} 个调用Dubbo服务的类:\n")
            for i, record in enumerate(results, 1):
                logger.info(f"{i}. 调用方: {record['CallerName']} ({record['CallerFQN']})")
                for svc in record['CalledServices']:
                    logger.info(f"   - 通过字段 '{svc['field']}' 调用: {svc['service']} ({svc['serviceFQN']})")
                logger.info("")
        else:
            logger.info("未找到调用Dubbo服务的类")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
    
    # 示例2.4: 完整的Dubbo调用链（调用方 -> 服务接口 -> 服务提供者）
    logger.info("\n【示例2.4】完整的Dubbo调用链（调用方 -> 服务接口 -> 服务提供者）")
    logger.info("-" * 80)
    query4 = """
    MATCH (caller:Type)-[calls:DUBBO_CALLS]->(service_iface:Type)
    OPTIONAL MATCH (provider:Type)-[:DUBBO_PROVIDES]->(service_iface)
    RETURN
      caller.name AS CallerName,
      calls.field_name AS FieldName,
      service_iface.name AS ServiceInterfaceName,
      provider.name AS ProviderName,
      provider.fqn AS ProviderFQN
    ORDER BY CallerName, ServiceInterfaceName
    LIMIT 10
    """
    
    try:
        results = client.execute_query(query4)
        if results:
            logger.info(f"找到 {len(results)} 个完整的Dubbo调用链:\n")
            for i, record in enumerate(results, 1):
                logger.info(f"{i}. 调用方: {record['CallerName']}")
                logger.info(f"   通过字段: {record['FieldName']}")
                logger.info(f"   服务接口: {record['ServiceInterfaceName']}")
                if record['ProviderName']:
                    logger.info(f"   服务提供者: {record['ProviderName']} ({record['ProviderFQN']})")
                else:
                    logger.info(f"   服务提供者: 未找到")
                logger.info("")
        else:
            logger.info("未找到完整的Dubbo调用链")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)


def demo_module_dependency_queries(client):
    """场景3: 分析模块间的依赖关系"""
    logger.info("\n" + "=" * 80)
    logger.info("场景3: 分析模块间的依赖关系")
    logger.info("=" * 80)
    
    # 示例3.1: 查找模块之间直接的类型依赖关系
    logger.info("\n【示例3.1】查找模块之间直接的类型依赖关系")
    logger.info("-" * 80)
    query1 = """
    MATCH (p1:Project)-[:CONTAINS*]->(t1:Type)
    MATCH (p2:Project)-[:CONTAINS*]->(t2:Type)
    WHERE p1.name <> p2.name
      AND (t1)-[:DEPENDS_ON]->(t2)
    RETURN
      p1.name AS DependentModule,
      t1.fqn AS DependentType,
      p2.name AS DependencyModule,
      t2.fqn AS DependencyType
    ORDER BY DependentModule, DependencyModule
    LIMIT 20
    """
    
    try:
        results = client.execute_query(query1)
        logger.info(f"找到 {len(results)} 个跨模块依赖关系（显示前20个）:\n")
        current_module_pair = None
        count = 0
        for record in results:
            module_pair = f"{record['DependentModule']} -> {record['DependencyModule']}"
            if current_module_pair != module_pair:
                current_module_pair = module_pair
                count = 0
                logger.info(f"\n模块依赖: {module_pair}")
            count += 1
            if count <= 3:  # 每个模块对只显示前3个类型依赖
                logger.info(f"  {record['DependentType']} -> {record['DependencyType']}")
            elif count == 4:
                logger.info("  ...")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
    
    # 示例3.2: 聚合模块间的依赖数量
    logger.info("\n【示例3.2】聚合模块间的依赖数量（模块耦合度分析）")
    logger.info("-" * 80)
    query2 = """
    MATCH (p1:Project)-[:CONTAINS*]->(t1:Type)-[:DEPENDS_ON]->(t2:Type)<-[:CONTAINS*]-(p2:Project)
    WHERE p1.name <> p2.name
      AND p1.name STARTS WITH 'chatroom-router-service'
      AND p2.name STARTS WITH 'chatroom-router-service'
    RETURN
      p1.name AS DependentModule,
      p2.name AS DependencyModule,
      COUNT(DISTINCT t1) AS UniqueDependentTypes,
      COUNT(DISTINCT t2) AS UniqueDependencyTypes,
      COUNT(*) AS TotalDependencies
    ORDER BY TotalDependencies DESC
    """
    
    try:
        results = client.execute_query(query2)
        if results:
            logger.info(f"模块间依赖统计:\n")
            logger.info(f"{'依赖模块':<40} {'被依赖模块':<40} {'依赖类型数':<12} {'被依赖类型数':<12} {'总依赖数':<10}")
            logger.info("-" * 120)
            for record in results:
                logger.info(f"{record['DependentModule']:<40} {record['DependencyModule']:<40} "
                          f"{record['UniqueDependentTypes']:<12} {record['UniqueDependencyTypes']:<12} "
                          f"{record['TotalDependencies']:<10}")
        else:
            logger.info("未找到模块间依赖关系")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
    
    # 示例3.3: 查找某个模块依赖的所有其他模块
    logger.info("\n【示例3.3】查找某个模块依赖的所有其他模块")
    logger.info("-" * 80)
    query3 = """
    MATCH (p1:Project {name: 'chatroom-router-service-router-service'})-[:CONTAINS*]->(t1:Type)
    MATCH (t1)-[:DEPENDS_ON]->(t2:Type)<-[:CONTAINS*]-(p2:Project)
    WHERE p1.name <> p2.name
    RETURN
      p2.name AS DependencyModule,
      COUNT(DISTINCT t1) AS DependentTypesCount,
      COUNT(DISTINCT t2) AS DependencyTypesCount,
      COLLECT(DISTINCT t2.fqn)[0..5] AS SampleDependencyTypes
    ORDER BY DependencyTypesCount DESC
    """
    
    try:
        results = client.execute_query(query3)
        if results:
            logger.info(f"router-service 模块的依赖模块分析:\n")
            for i, record in enumerate(results, 1):
                logger.info(f"{i}. 依赖模块: {record['DependencyModule']}")
                logger.info(f"   依赖的类型数量: {record['DependencyTypesCount']}")
                logger.info(f"   依赖方类型数量: {record['DependentTypesCount']}")
                logger.info(f"   示例依赖类型: {', '.join(record['SampleDependencyTypes'])}")
                logger.info("")
        else:
            logger.info("未找到模块依赖关系")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
    
    # 示例3.4: 查找模块间的继承和实现关系
    logger.info("\n【示例3.4】查找模块间的继承和实现关系")
    logger.info("-" * 80)
    query4 = """
    MATCH (p1:Project)-[:CONTAINS*]->(t1:Type)
    MATCH (p2:Project)-[:CONTAINS*]->(t2:Type)
    WHERE p1.name <> p2.name
      AND (
        (t1)-[:EXTENDS]->(t2) OR
        (t1)-[:IMPLEMENTS]->(t2)
      )
    RETURN
      p1.name AS ChildModule,
      t1.name AS ChildType,
      t1.fqn AS ChildFQN,
      TYPE(RELATIONSHIPS(t1)[0]) AS RelationType,
      p2.name AS ParentModule,
      t2.name AS ParentType,
      t2.fqn AS ParentFQN
    ORDER BY ChildModule, ParentModule
    LIMIT 15
    """
    
    try:
        results = client.execute_query(query4)
        if results:
            logger.info(f"找到 {len(results)} 个跨模块继承/实现关系（显示前15个）:\n")
            for i, record in enumerate(results, 1):
                relation = "继承" if "EXTENDS" in str(record['RelationType']) else "实现"
                logger.info(f"{i}. {record['ChildModule']} 的 {record['ChildType']} {relation} "
                          f"{record['ParentModule']} 的 {record['ParentType']}")
                logger.info(f"   {record['ChildFQN']} -> {record['ParentFQN']}")
                logger.info("")
        else:
            logger.info("未找到跨模块继承/实现关系")
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)


def main():
    """主函数"""
    # 检查Neo4j连接
    try:
        # 尝试使用默认配置
        if not os.getenv('NEO4J_URI'):
            os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
        if not os.getenv('NEO4J_USER'):
            os.environ['NEO4J_USER'] = 'neo4j'
        if not os.getenv('NEO4J_PASSWORD'):
            os.environ['NEO4J_PASSWORD'] = 'jqassistant123'
        
        client = Neo4jStorage()
        if not client.is_connected():
            logger.info("正在连接Neo4j...")
            if not client.connect():
                logger.error("无法连接到Neo4j")
                return
        logger.info("✅ Neo4j连接成功\n")
        
        # 执行三个场景的查询演示
        demo_interface_queries(client)
        demo_dubbo_queries(client)
        demo_module_dependency_queries(client)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ 所有查询演示完成！")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"操作失败: {e}", exc_info=True)
    finally:
        if client.is_connected():
            client.close()


if __name__ == "__main__":
    main()
