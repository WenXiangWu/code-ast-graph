#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快捷查询功能: 通过类名快速分析全链路依赖

功能:
1. 查询全链路操作的所有数据库表
2. 查询全链路调用的所有外部 Dubbo 服务
3. 查询全链路涉及的所有服务和类
"""
import logging
from typing import Dict, List, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class QuickAnalyzer:
    """快捷分析器"""
    
    def __init__(self, neo4j_client):
        """
        Args:
            neo4j_client: Neo4jStorage 实例
        """
        self.client = neo4j_client
    
    def analyze_class_full_chain(self, class_fqn: str, max_depth: int = 15) -> Dict:
        """
        分析类的全链路依赖
        
        Args:
            class_fqn: 类的全限定名
            max_depth: 最大追踪深度
            
        Returns:
            {
                'class_info': {...},  # 类基本信息
                'database_tables': [...],  # 操作的所有数据库表
                'dubbo_services': [...],  # 调用的所有外部 Dubbo 服务
                'involved_services': {...},  # 涉及的所有服务和类
                'call_chain_summary': {...}  # 调用链路摘要
            }
        """
        logger.info(f"开始分析类: {class_fqn}")
        
        # 1. 获取类基本信息
        class_info = self._get_class_info(class_fqn)
        if not class_info:
            return {'error': f'类不存在: {class_fqn}'}
        
        # 2. 查询全链路操作的数据库表
        database_tables = self._query_database_tables(class_fqn, max_depth)
        
        # 3. 查询全链路调用的外部 Dubbo 服务
        dubbo_services = self._query_dubbo_services(class_fqn, max_depth)
        
        # 4. 查询全链路涉及的所有服务和类
        involved_services = self._query_involved_services(class_fqn, max_depth)
        
        # 5. 生成调用链路摘要
        call_chain_summary = self._generate_call_chain_summary(
            class_fqn, database_tables, dubbo_services, involved_services
        )
        
        return {
            'class_info': class_info,
            'database_tables': database_tables,
            'dubbo_services': dubbo_services,
            'involved_services': involved_services,
            'call_chain_summary': call_chain_summary
        }
    
    def _get_class_info(self, class_fqn: str) -> Dict:
        """获取类基本信息"""
        result = self.client.execute_query("""
            MATCH (c) 
            WHERE (c:CLASS OR c:INTERFACE) AND c.fqn = $fqn
            OPTIONAL MATCH (project:Project)-[:CONTAINS]->(c)
            RETURN 
                labels(c) as labels,
                c.name as name,
                c.fqn as fqn,
                c.arch_layer as arch_layer,
                c.is_dubbo_service as is_dubbo_service,
                c.is_mapper as is_mapper,
                project.name as project_name
        """, {'fqn': class_fqn})
        
        if not result:
            return None
        
        r = result[0]
        return {
            'type': r['labels'][0] if r['labels'] else 'UNKNOWN',
            'name': r['name'],
            'fqn': r['fqn'],
            'arch_layer': r['arch_layer'],
            'is_dubbo_service': r['is_dubbo_service'],
            'is_mapper': r['is_mapper'],
            'project': r['project_name']
        }
    
    def _query_database_tables(self, class_fqn: str, max_depth: int) -> List[Dict]:
        """查询全链路操作的数据库表"""
        result = self.client.execute_query(f"""
            MATCH (c) WHERE (c:CLASS OR c:INTERFACE) AND c.fqn = $class_fqn
            
            // 如果是接口，追踪到实现类
            OPTIONAL MATCH (impl)-[:IMPLEMENTS]->(c)
            WITH COALESCE(impl, c) as start_class
            
            MATCH (start_class)-[:DECLARES]->(m:Method)
            
            // 追踪到 Mapper
            MATCH path = (m)-[:CALLS*1..{max_depth}]->(mapper_method:Method)
            MATCH (mapper_class)-[:DECLARES]->(mapper_method)
            WHERE mapper_class.is_mapper = true
            
            // 获取 Mapper 操作的表
            MATCH (mapper_class)-[:MAPPER_FOR_TABLE]->(table:Table)
            
            RETURN DISTINCT
                table.name as table_name,
                table.comment as table_comment,
                mapper_class.name as mapper_name,
                mapper_method.name as mapper_method,
                length(path) as call_depth
            ORDER BY table_name, call_depth
        """, {'class_fqn': class_fqn})
        
        # 按表分组
        tables_dict = {}
        for r in result:
            table_name = r['table_name']
            if table_name not in tables_dict:
                tables_dict[table_name] = {
                    'table_name': table_name,
                    'table_comment': r['table_comment'],
                    'operations': []
                }
            
            tables_dict[table_name]['operations'].append({
                'mapper': r['mapper_name'],
                'method': r['mapper_method'],
                'depth': r['call_depth']
            })
        
        return list(tables_dict.values())
    
    def _query_dubbo_services(self, class_fqn: str, max_depth: int) -> List[Dict]:
        """查询全链路调用的外部 Dubbo 服务"""
        result = self.client.execute_query(f"""
            MATCH (c) WHERE (c:CLASS OR c:INTERFACE) AND c.fqn = $class_fqn
            
            // 如果是接口，追踪到实现类
            OPTIONAL MATCH (impl)-[:IMPLEMENTS]->(c)
            WITH COALESCE(impl, c) as start_class
            
            MATCH (start_class)-[:DECLARES]->(m:Method)
            
            // 追踪到 Dubbo 调用
            MATCH path = (m)-[:CALLS*1..{max_depth}]->(dubbo_method:Method)
            WHERE ANY(rel IN relationships(path) WHERE rel.call_type IN ['Reference', 'DubboReference'])
            
            // 获取 Dubbo 服务类
            MATCH (dubbo_class)-[:DECLARES]->(dubbo_method)
            WHERE dubbo_class.is_external = true OR NOT exists((project:Project)-[:CONTAINS]->(dubbo_class))
            
            // 获取 via_field
            WITH dubbo_class, dubbo_method, path,
                 [rel IN relationships(path) WHERE rel.call_type IN ['Reference', 'DubboReference'] | rel.via_field][0] as via_field
            
            RETURN DISTINCT
                dubbo_class.fqn as service_fqn,
                dubbo_class.name as service_name,
                dubbo_method.name as method_name,
                length(path) as call_depth,
                via_field
            ORDER BY service_fqn, method_name
        """, {'class_fqn': class_fqn})
        
        # 按服务分组
        services_dict = {}
        for r in result:
            service_fqn = r['service_fqn']
            if service_fqn not in services_dict:
                services_dict[service_fqn] = {
                    'service_fqn': service_fqn,
                    'service_name': r['service_name'],
                    'methods': []
                }
            
            services_dict[service_fqn]['methods'].append({
                'method': r['method_name'],
                'depth': r['call_depth'],
                'via_field': r['via_field']
            })
        
        return list(services_dict.values())
    
    def _query_involved_services(self, class_fqn: str, max_depth: int) -> Dict:
        """查询全链路涉及的所有服务和类"""
        result = self.client.execute_query(f"""
            MATCH (c) WHERE (c:CLASS OR c:INTERFACE) AND c.fqn = $class_fqn
            
            // 如果是接口，追踪到实现类
            OPTIONAL MATCH (impl)-[:IMPLEMENTS]->(c)
            WITH COALESCE(impl, c) as start_class
            
            MATCH (start_class)-[:DECLARES]->(m:Method)
            
            // 追踪所有调用
            MATCH path = (m)-[:CALLS*1..{max_depth}]->(target_method:Method)
            MATCH (target_class)-[:DECLARES]->(target_method)
            
            // 获取项目信息
            OPTIONAL MATCH (project:Project)-[:CONTAINS]->(target_class)
            
            RETURN DISTINCT
                project.name as project_name,
                target_class.fqn as class_fqn,
                target_class.name as class_name,
                target_class.arch_layer as arch_layer,
                target_class.is_mapper as is_mapper,
                target_class.is_dubbo_service as is_dubbo_service,
                target_class.is_external as is_external,
                min(length(path)) as min_depth
            ORDER BY project_name, arch_layer, class_name
        """, {'class_fqn': class_fqn})
        
        # 按项目和架构层分组
        services = defaultdict(lambda: defaultdict(list))
        
        for r in result:
            project = r['project_name'] or 'external'
            layer = r['arch_layer'] or 'unknown'
            
            class_info = {
                'fqn': r['class_fqn'],
                'name': r['class_name'],
                'depth': r['min_depth'],
                'is_mapper': r['is_mapper'],
                'is_dubbo_service': r['is_dubbo_service'],
                'is_external': r['is_external']
            }
            
            services[project][layer].append(class_info)
        
        return dict(services)
    
    def _generate_call_chain_summary(
        self, 
        class_fqn: str, 
        database_tables: List[Dict],
        dubbo_services: List[Dict],
        involved_services: Dict
    ) -> Dict:
        """生成调用链路摘要"""
        
        # 统计各项目的类数量
        project_stats = {}
        for project, layers in involved_services.items():
            total_classes = sum(len(classes) for classes in layers.values())
            project_stats[project] = {
                'total_classes': total_classes,
                'layers': {layer: len(classes) for layer, classes in layers.items()}
            }
        
        return {
            'total_tables': len(database_tables),
            'total_dubbo_services': len(dubbo_services),
            'total_projects': len(involved_services),
            'project_stats': project_stats,
            'tables': [t['table_name'] for t in database_tables],
            'dubbo_services': [s['service_name'] for s in dubbo_services]
        }
    
    def format_analysis_result(self, analysis: Dict) -> str:
        """格式化分析结果为可读文本"""
        if 'error' in analysis:
            return f"❌ 错误: {analysis['error']}"
        
        lines = []
        lines.append("=" * 100)
        lines.append(f"类全链路依赖分析: {analysis['class_info']['name']}")
        lines.append("=" * 100)
        
        # 1. 类基本信息
        info = analysis['class_info']
        lines.append(f"\n【基本信息】")
        lines.append(f"  类型: {info['type']}")
        lines.append(f"  全限定名: {info['fqn']}")
        lines.append(f"  架构层: {info['arch_layer'] or '未知'}")
        lines.append(f"  所属项目: {info['project'] or '未知'}")
        if info['is_dubbo_service']:
            lines.append(f"  Dubbo 服务: 是")
        if info['is_mapper']:
            lines.append(f"  Mapper: 是")
        
        # 2. 调用链路摘要
        summary = analysis['call_chain_summary']
        lines.append(f"\n【调用链路摘要】")
        lines.append(f"  操作数据库表: {summary['total_tables']} 个")
        lines.append(f"  调用外部 Dubbo 服务: {summary['total_dubbo_services']} 个")
        lines.append(f"  涉及项目: {summary['total_projects']} 个")
        
        # 3. 数据库表
        if analysis['database_tables']:
            lines.append(f"\n【操作的数据库表】({len(analysis['database_tables'])} 个)")
            for i, table in enumerate(analysis['database_tables'], 1):
                lines.append(f"\n  {i}. {table['table_name']}")
                if table['table_comment']:
                    lines.append(f"     说明: {table['table_comment']}")
                lines.append(f"     操作方式 ({len(table['operations'])} 个):")
                for op in table['operations'][:5]:  # 最多显示 5 个
                    lines.append(f"       - {op['mapper']}.{op['method']} (深度: {op['depth']})")
                if len(table['operations']) > 5:
                    lines.append(f"       ... 还有 {len(table['operations']) - 5} 个操作")
        else:
            lines.append(f"\n【操作的数据库表】")
            lines.append(f"  无")
        
        # 4. Dubbo 服务
        if analysis['dubbo_services']:
            lines.append(f"\n【调用的外部 Dubbo 服务】({len(analysis['dubbo_services'])} 个)")
            for i, service in enumerate(analysis['dubbo_services'], 1):
                lines.append(f"\n  {i}. {service['service_name']}")
                lines.append(f"     全限定名: {service['service_fqn']}")
                lines.append(f"     调用方法 ({len(service['methods'])} 个):")
                for method in service['methods'][:5]:  # 最多显示 5 个
                    via = f" (via {method['via_field']})" if method['via_field'] else ""
                    lines.append(f"       - {method['method']}{via} (深度: {method['depth']})")
                if len(service['methods']) > 5:
                    lines.append(f"       ... 还有 {len(service['methods']) - 5} 个方法")
        else:
            lines.append(f"\n【调用的外部 Dubbo 服务】")
            lines.append(f"  无")
        
        # 5. 涉及的服务和类
        lines.append(f"\n【涉及的服务和类】")
        for project, layers in analysis['involved_services'].items():
            total = sum(len(classes) for classes in layers.values())
            lines.append(f"\n  项目: {project} ({total} 个类)")
            for layer, classes in sorted(layers.items()):
                lines.append(f"    {layer or 'unknown'} ({len(classes)} 个):")
                for cls in classes[:10]:  # 最多显示 10 个
                    flags = []
                    if cls['is_mapper']:
                        flags.append('Mapper')
                    if cls['is_dubbo_service']:
                        flags.append('Dubbo')
                    if cls['is_external']:
                        flags.append('External')
                    flag_str = f" [{', '.join(flags)}]" if flags else ""
                    lines.append(f"      - {cls['name']}{flag_str} (深度: {cls['depth']})")
                if len(classes) > 10:
                    lines.append(f"      ... 还有 {len(classes) - 10} 个类")
        
        lines.append("\n" + "=" * 100)
        return "\n".join(lines)
    
    def get_quick_summary(self, class_fqn: str, max_depth: int = 15) -> Dict:
        """
        获取快速摘要 (只返回统计数据，不包含详细列表)
        
        适用于前端快捷查询，返回轻量级数据
        """
        class_info = self._get_class_info(class_fqn)
        if not class_info:
            return {'error': f'类不存在: {class_fqn}'}
        
        # 统计数据库表数量
        table_count = self.client.execute_query(f"""
            MATCH (c) WHERE (c:CLASS OR c:INTERFACE) AND c.fqn = $class_fqn
            MATCH (c)-[:DECLARES]->(m:Method)
            MATCH (m)-[:CALLS*1..{max_depth}]->(mapper_method:Method)
            MATCH (mapper_class)-[:DECLARES]->(mapper_method)
            WHERE mapper_class.is_mapper = true
            MATCH (mapper_class)-[:MAPPER_FOR_TABLE]->(table:Table)
            RETURN count(DISTINCT table) as count
        """, {'class_fqn': class_fqn})
        
        # 统计 Dubbo 服务数量
        dubbo_count = self.client.execute_query(f"""
            MATCH (c) WHERE (c:CLASS OR c:INTERFACE) AND c.fqn = $class_fqn
            MATCH (c)-[:DECLARES]->(m:Method)
            MATCH path = (m)-[:CALLS*1..{max_depth}]->(dubbo_method:Method)
            WHERE ANY(rel IN relationships(path) WHERE rel.call_type IN ['Reference', 'DubboReference'])
            MATCH (dubbo_class)-[:DECLARES]->(dubbo_method)
            WHERE dubbo_class.is_external = true OR NOT exists((:Project)-[:CONTAINS]->(dubbo_class))
            RETURN count(DISTINCT dubbo_class) as count
        """, {'class_fqn': class_fqn})
        
        # 统计涉及的类数量
        class_count = self.client.execute_query(f"""
            MATCH (c) WHERE (c:CLASS OR c:INTERFACE) AND c.fqn = $class_fqn
            MATCH (c)-[:DECLARES]->(m:Method)
            MATCH (m)-[:CALLS*1..{max_depth}]->(target_method:Method)
            MATCH (target_class)-[:DECLARES]->(target_method)
            RETURN count(DISTINCT target_class) as count
        """, {'class_fqn': class_fqn})
        
        return {
            'class_info': class_info,
            'summary': {
                'database_tables': table_count[0]['count'] if table_count else 0,
                'dubbo_services': dubbo_count[0]['count'] if dubbo_count else 0,
                'involved_classes': class_count[0]['count'] if class_count else 0
            }
        }
