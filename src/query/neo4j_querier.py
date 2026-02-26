"""
Neo4j 查询器
提供知识图谱查询功能
更新：修复了 max_depth 参数问题
"""

from typing import Dict, List, Optional
import logging

from ..storage.neo4j.storage import Neo4jStorage

logger = logging.getLogger(__name__)


class Neo4jQuerier:
    """Neo4j 查询器"""
    
    def __init__(self, storage: Optional[Neo4jStorage] = None):
        """
        初始化查询器
        
        Args:
            storage: Neo4j 存储
        """
        if storage is None:
            storage = Neo4jStorage()
        self.storage = storage
        # 兼容性：保留 client 属性
        self.client = storage
    
    def get_call_graph_sync(
        self,
        project: str,
        start_class: Optional[str] = None,
        max_depth: int = 3,
        filter_mode: str = 'moderate'
    ) -> Dict:
        """
        同步获取调用图，供 run_in_executor 使用，避免阻塞事件循环
        """
        return self._do_get_call_graph(project, start_class, max_depth, filter_mode)

    def _do_get_call_graph(
        self,
        project: str,
        start_class: Optional[str] = None,
        max_depth: int = 3,
        filter_mode: str = 'moderate'
    ) -> Dict:
        """
        获取服务调用图
        
        Args:
            project: 项目名称
            start_class: 起始类名（可选）
            max_depth: 最大深度
            filter_mode: 过滤模式
                - 'none': 不过滤
                - 'loose': 宽松模式，只过滤JDK核心类
                - 'moderate': 适中模式，过滤JDK和工具类（默认）
                - 'strict': 严格模式，过滤所有噪音（包括DTO、Entity）
        
        Returns:
            调用图数据
        """
        try:
            if not self.storage.is_connected():
                self.storage.connect()
            
            # 导入过滤函数
            import sys
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent / 'config'
            if str(config_path) not in sys.path:
                sys.path.insert(0, str(config_path))
            
            from noise_filter import get_noise_filter_function
            filter_func = get_noise_filter_function(filter_mode)
            
            params = {"project": project}
            
            # 如果指定了起始类，从该类开始扩展
            if start_class:
                # 从指定类开始，展开多层依赖关系
                query = f"""
                MATCH (p:Project {{name: $project}})
                MATCH (start:Type)
                WHERE (start.name = $start_class OR start.fqn CONTAINS $start_class)
                  AND ((p)-[:CONTAINS]->(start) OR start.project = $project)
                MATCH path = (start)-[:DEPENDS_ON*0..{max_depth}]->(end:Type)
                WHERE (p)-[:CONTAINS]->(end) OR end.project = $project OR end.project IS NULL
                WITH path, relationships(path) as rels, nodes(path) as path_nodes
                UNWIND range(0, size(rels)-1) as idx
                WITH rels[idx] as rel, path_nodes[idx] as n1, path_nodes[idx+1] as n2
                RETURN DISTINCT 
                    n1.fqn as from, 
                    n2.fqn as to, 
                    n1.name as from_name, 
                    n2.name as to_name
                LIMIT 2000
                """
                params["start_class"] = start_class
            else:
                # 不指定起始类，查询所有依赖关系（限制深度以避免过多数据）
                query = f"""
                MATCH (p:Project {{name: $project}})
                MATCH path = (from:Type)-[:DEPENDS_ON*1..{max_depth}]->(to:Type)
                WHERE (from.project = $project OR (p)-[:CONTAINS]->(from))
                  AND ((to.project = $project OR (p)-[:CONTAINS]->(to)) OR to.project IS NULL)
                WITH path, relationships(path) as rels, nodes(path) as path_nodes
                UNWIND range(0, size(rels)-1) as idx
                WITH rels[idx] as rel, path_nodes[idx] as n1, path_nodes[idx+1] as n2
                RETURN DISTINCT 
                    n1.fqn as from, 
                    n2.fqn as to, 
                    n1.name as from_name, 
                    n2.name as to_name
                LIMIT 2000
                """
            
            logger.info(f"执行查询，max_depth={max_depth}, start_class={start_class}, filter_mode={filter_mode}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Params: {params}")
            
            results = self.storage.execute_query(query, params)
            
            logger.info(f"Neo4j 返回 {len(results)} 条关系记录")
            
            # 构建节点和边（应用过滤）
            nodes_set = set()
            edges = []
            edges_set = set()  # 用于去重
            node_names = {}  # 存储节点的简称
            filtered_count = 0
            
            for r in results:
                from_fqn = r.get('from')
                to_fqn = r.get('to')
                from_name = r.get('from_name')
                to_name = r.get('to_name')
                
                # 应用过滤规则
                if not from_fqn or not to_fqn:
                    continue
                
                # 过滤噪音节点
                from_keep = filter_func(from_fqn, from_name or '')
                to_keep = filter_func(to_fqn, to_name or '')
                
                if not (from_keep and to_keep):
                    filtered_count += 1
                    continue
                
                # 添加节点
                if from_fqn:
                    nodes_set.add(from_fqn)
                    node_names[from_fqn] = from_name or (from_fqn.split('.')[-1] if from_fqn else '')
                if to_fqn:
                    nodes_set.add(to_fqn)
                    node_names[to_fqn] = to_name or (to_fqn.split('.')[-1] if to_fqn else '')
                
                # 添加边（去重）
                if from_fqn and to_fqn:
                    edge_key = (from_fqn, to_fqn)
                    if edge_key not in edges_set:
                        edges_set.add(edge_key)
                        edges.append({
                            'from': from_fqn,
                            'to': to_fqn,
                            'depth': 1
                        })
            
            nodes = [{'id': n, 'name': node_names.get(n, n.split('.')[-1] if n else '')} for n in nodes_set]
            
            logger.info(f"处理结果: {len(nodes)} 个节点, {len(edges)} 条边 (过滤了 {filtered_count} 条关系)")
            
            return {
                'nodes': nodes,
                'edges': edges,
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'filtered_count': filtered_count,
                'filter_mode': filter_mode
            }
        except Exception as e:
            logger.error(f"查询调用图失败: {e}", exc_info=True)
            return {
                'nodes': [],
                'edges': [],
                'total_nodes': 0,
                'total_edges': 0,
                'error': str(e)
            }

    async def get_call_graph(
        self,
        project: str,
        start_class: Optional[str] = None,
        max_depth: int = 3,
        filter_mode: str = 'moderate'
    ) -> Dict:
        """异步封装：在线程池中执行同步查询"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.get_call_graph_sync(project, start_class, max_depth, filter_mode),
        )
    
    async def get_database_schema(self, project: str) -> Dict:
        """
        获取数据库表结构
        
        Args:
            project: 项目名称
        
        Returns:
            数据库表列表
        """
        try:
            if not self.storage.is_connected():
                self.storage.connect()
            
            # 查询可能的实体类（简化版，基于文件路径或类名）- 使用正确的字段名
            query = """
            MATCH (p:Project {name: $project})-[:CONTAINS]->(t:Type)
            WHERE t.file_path CONTAINS 'entity' 
               OR t.file_path CONTAINS 'model'
               OR t.file_path CONTAINS 'domain'
               OR t.name ENDS WITH 'Entity'
               OR t.name ENDS WITH 'Model'
            RETURN t.fqn as entity_class, t.name as name, t.file_path as file_path
            LIMIT 100
            """
            
            results = self.storage.execute_query(query, {"project": project})
            
            tables = [
                {
                    'table_name': r['name'],
                    'entity_class': r['entity_class'],
                    'field_count': 0,  # Python AST 暂不支持字段提取
                    'file_path': r.get('file_path', '')
                }
                for r in results
            ]
            
            return {'tables': tables}
        except Exception as e:
            logger.error(f"查询数据库表失败: {e}", exc_info=True)
            return {'error': str(e), 'tables': []}
    
    async def analyze_impact(
        self,
        project: str,
        class_name: str,
        max_depth: int = 5
    ) -> Dict:
        """
        分析类的影响面
        
        Args:
            project: 项目名称
            class_name: 类名
            max_depth: 最大深度
        
        Returns:
            影响面分析结果
        """
        try:
            if not self.storage.is_connected():
                self.storage.connect()
            
            # 查询依赖该类的所有类 - max_depth 必须直接嵌入查询字符串
            query = f"""
            MATCH (p:Project {{name: $project}})
            MATCH (target:Type)
            WHERE (target.name = $class_name OR target.fqn CONTAINS $class_name)
              AND ((p)-[:CONTAINS]->(target) OR target.project = $project)
            MATCH (dependent:Type)-[:DEPENDS_ON*1..{max_depth}]->(target)
            WHERE (p)-[:CONTAINS]->(dependent) OR dependent.project = $project
            RETURN DISTINCT dependent.fqn as affected_class, dependent.name as name
            LIMIT 200
            """
            
            results = self.storage.execute_query(query, {
                "project": project,
                "class_name": class_name
            })
            
            affected_classes = [
                {
                    'name': r['name'],
                    'class': r['affected_class']
                }
                for r in results
            ]
            
            total_affected = len(affected_classes)
            
            # 评估风险等级
            if total_affected == 0:
                risk_level = "none"
            elif total_affected < 5:
                risk_level = "low"
            elif total_affected < 20:
                risk_level = "medium"
            else:
                risk_level = "high"
            
            return {
                'total_affected': total_affected,
                'risk_level': risk_level,
                'impact_by_level': {
                    '1': affected_classes[:50]  # 简化处理，只返回前50个
                }
            }
        except Exception as e:
            logger.error(f"分析影响面失败: {e}", exc_info=True)
            return {'error': str(e)}
