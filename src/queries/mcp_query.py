#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 标准化查询接口
提供结构化的全链路分析结果

深度定义（统一）：
  - 深度 = 从起点到目标的「边」数（CALLS 关系数）
  - A → B：1 层（1 条边）
  - A → B → C：2 层（2 条边）
  - max_depth=10 表示最多追溯 10 层（10 条边）
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class EndpointInfo:
    """前端用户入口信息"""
    project: str
    class_fqn: str
    method: str
    path: str
    http_method: str
    
    def __eq__(self, other):
        """比较时忽略 project 字段（只用于去重）"""
        if not isinstance(other, EndpointInfo):
            return False
        return (self.class_fqn == other.class_fqn and
                self.method == other.method and
                self.path == other.path and
                self.http_method == other.http_method)
    
    def __hash__(self):
        """哈希时忽略 project 字段"""
        return hash((self.class_fqn, self.method, self.path, self.http_method))


@dataclass
class InternalClassInfo:
    """内部类信息（非外部 Dubbo）"""
    project: str
    class_fqn: str
    class_name: str
    arch_layer: str


@dataclass
class DubboCallInfo:
    """外部 Dubbo 调用信息"""
    caller_project: str
    caller_class: str
    caller_method: str
    dubbo_interface: str
    dubbo_method: str
    via_field: str
    target_project: str = 'Unknown'  # 目标服务的项目名称
    
    def __eq__(self, other):
        """比较时忽略 caller_project 和 target_project 字段（只用于去重）"""
        if not isinstance(other, DubboCallInfo):
            return False
        return (self.caller_class == other.caller_class and
                self.caller_method == other.caller_method and
                self.dubbo_interface == other.dubbo_interface and
                self.dubbo_method == other.dubbo_method and
                self.via_field == other.via_field)
    
    def __hash__(self):
        """哈希时忽略 caller_project 和 target_project 字段"""
        return hash((self.caller_class, self.caller_method, 
                    self.dubbo_interface, self.dubbo_method, self.via_field))


@dataclass
class TableInfo:
    """数据库表信息"""
    project: str
    mapper_fqn: str
    mapper_name: str
    table_name: str


@dataclass
class AriesJobInfo:
    """Aries Job 信息"""
    project: str
    class_fqn: str
    class_name: str
    job_type: str
    cron_expr: Optional[str] = None


@dataclass
class MQInfo:
    """MQ 信息"""
    project: str
    class_fqn: str
    class_name: str
    mq_type: str  # kafka/rocket
    topic: str
    role: str  # consumer/producer
    method: Optional[str] = None  # 消费方法或发送方法


@dataclass
class CallNode:
    """调用链节点（树形结构）"""
    node_type: str  # method/dubbo_call/db_call/mq/aries_job
    project: str
    class_fqn: str
    class_name: str
    method_name: Optional[str] = None
    method_signature: Optional[str] = None
    arch_layer: Optional[str] = None
    
    # Dubbo 调用特有字段
    dubbo_interface: Optional[str] = None
    dubbo_method: Optional[str] = None
    via_field: Optional[str] = None
    
    # 数据库调用特有字段
    table_name: Optional[str] = None
    mapper_name: Optional[str] = None
    
    # MQ 特有字段
    mq_topic: Optional[str] = None
    mq_role: Optional[str] = None
    
    # Aries Job 特有字段
    job_type: Optional[str] = None
    cron_expr: Optional[str] = None
    
    # 子节点（递归结构）
    children: List['CallNode'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def to_dict(self):
        """转换为字典（用于 JSON 序列化）"""
        result = {
            'node_type': self.node_type,
            'project': self.project,
            'class_fqn': self.class_fqn,
            'class_name': self.class_name,
            'method_name': self.method_name,
            'method_signature': self.method_signature,
            'arch_layer': self.arch_layer,
            'children': [child.to_dict() for child in self.children]
        }
        
        # 添加特定类型的字段
        if self.node_type == 'dubbo_call':
            result.update({
                'dubbo_interface': self.dubbo_interface,
                'dubbo_method': self.dubbo_method,
                'via_field': self.via_field
            })
        elif self.node_type == 'db_call':
            result.update({
                'table_name': self.table_name,
                'mapper_name': self.mapper_name
            })
        elif self.node_type == 'mq':
            result.update({
                'mq_topic': self.mq_topic,
                'mq_role': self.mq_role
            })
        elif self.node_type == 'aries_job':
            result.update({
                'job_type': self.job_type,
                'cron_expr': self.cron_expr
            })
        
        return result


@dataclass
class MCPQueryResult:
    """MCP 查询结果"""
    success: bool
    message: str
    endpoints: List[EndpointInfo]
    internal_classes: List[InternalClassInfo]
    dubbo_calls: List[DubboCallInfo]
    tables: List[TableInfo]
    aries_jobs: List[AriesJobInfo]
    mq_info: List[MQInfo]
    call_tree: Optional[CallNode] = None  # 新增：调用链树形结构
    
    def to_dict(self):
        """转换为字典"""
        result = {
            'success': self.success,
            'message': self.message,
            'endpoints': [asdict(e) for e in self.endpoints],
            'internal_classes': [asdict(c) for c in self.internal_classes],
            'dubbo_calls': [asdict(d) for d in self.dubbo_calls],
            'tables': [asdict(t) for t in self.tables],
            'aries_jobs': [asdict(j) for j in self.aries_jobs],
            'mq_info': [asdict(m) for m in self.mq_info]
        }
        
        # 添加调用树
        if self.call_tree:
            result['call_tree'] = self.call_tree.to_dict()
        
        return result


def collect_call_statistics(result: MCPQueryResult) -> dict:
    """
    从 MCP 查询结果中汇总「调用统计」JSON，与前端 collectCallStatistics 结构一致。
    用于对外接口直接返回调用统计。
    
    Returns:
        {
            "class_stats": [ {"class": fqn, "call_count": n, "methods": [...], "project": "..."} ],
            "tables": [ "table_a", ... ],
            "mq_list": [ "topic1", ... ],
            "frontend_entries": [ {"project", "class_fqn", "method", "path", "http_method"}, ... ]
        }
    """
    class_map: Dict[str, dict] = {}  # fqn -> { count, methods set, project }
    tables_set = set()
    mq_list_set = set()

    def walk(node: CallNode):
        if node.node_type in ('method', 'interface', 'aries_job') and node.class_fqn:
            key = node.class_fqn
            if key not in class_map:
                class_map[key] = {'count': 0, 'methods': set(), 'project': node.project or ''}
            class_map[key]['count'] += 1
            if node.method_name:
                class_map[key]['methods'].add(node.method_name)
        if node.node_type == 'db_call' and node.table_name:
            tables_set.add(node.table_name)
        if node.node_type == 'mq' and node.mq_topic:
            mq_list_set.add(node.mq_topic)
        for child in node.children or []:
            walk(child)

    if result.call_tree:
        walk(result.call_tree)

    class_stats = [
        {
            'class': cls,
            'call_count': v['count'],
            'methods': sorted(v['methods']),
            'project': v['project'],
        }
        for cls, v in class_map.items()
    ]
    class_stats.sort(key=lambda x: -x['call_count'])

    return {
        'class_stats': class_stats,
        'tables': sorted(tables_set),
        'mq_list': sorted(mq_list_set),
        'frontend_entries': [asdict(e) for e in result.endpoints],
    }


class MCPQuerier:
    """MCP 标准化查询器"""
    
    def __init__(self, storage):
        """
        初始化查询器
        
        Args:
            storage: Neo4jStorage 实例
        """
        self.storage = storage
    
    def query_full_chain(
        self,
        project: str,
        class_fqn: str,
        method: str,
        max_depth: int = 10
    ) -> MCPQueryResult:
        """
        查询完整调用链路
        
        Args:
            project: 项目名称（必填）
            class_fqn: 类的全限定名（必填）
            method: 方法名（必填）
            max_depth: 最大查询深度（默认 10）。深度=边数：A→B 为 1 层，A→B→C 为 2 层。

        Returns:
            MCPQueryResult: 结构化的查询结果
        """
        if not project or not class_fqn or not method:
            return MCPQueryResult(
                success=False,
                message="参数不完整：project、class_fqn、method 都是必填项",
                endpoints=[],
                internal_classes=[],
                dubbo_calls=[],
                tables=[],
                aries_jobs=[],
                mq_info=[]
            )
        
        try:
            logger.info(f"开始 MCP 查询: {project}.{class_fqn}.{method}")
            
            # 1. 查询入口方法
            start_method = self._find_start_method(project, class_fqn, method)
            if not start_method:
                return MCPQueryResult(
                    success=False,
                    message=f"未找到方法: {project}.{class_fqn}.{method}",
                    endpoints=[],
                    internal_classes=[],
                    dubbo_calls=[],
                    tables=[],
                    aries_jobs=[],
                    mq_info=[]
                )
            
            # 1.1 检查是否是接口方法，如果是，找到所有实现类的方法
            impl_methods = self._find_implementation_methods(start_method)
            
            # 如果是接口方法，需要查询所有实现类的链路
            methods_to_query = [start_method] + impl_methods if impl_methods else [start_method]
            
            # 2. 查询前端入口（RPC Endpoint）
            endpoints = []
            for method_sig in methods_to_query:
                endpoints.extend(self._query_endpoints(method_sig))
            # 去重
            endpoints = list({ep for ep in endpoints})
            
            # 3. 查询涉及的内部类（非外部 Dubbo）
            internal_classes = []
            for method_sig in methods_to_query:
                internal_classes.extend(self._query_internal_classes(method_sig, max_depth))
            # 去重
            internal_classes = list({(ic.project, ic.class_fqn): ic for ic in internal_classes}.values())
            
            # 4. 查询外部 Dubbo 调用
            dubbo_calls = []
            for method_sig in methods_to_query:
                dubbo_calls.extend(self._query_dubbo_calls(method_sig, max_depth))
            # 去重
            dubbo_calls = list({dc for dc in dubbo_calls})
            
            # 4.1 递归查询 Dubbo 下游服务的完整链路
            downstream_methods = self._find_dubbo_downstream_methods(dubbo_calls)
            if downstream_methods:
                logger.info(f"找到 {len(downstream_methods)} 个 Dubbo 下游方法，开始递归查询...")
                methods_to_query.extend(downstream_methods)
            
            # 5. 查询涉及的数据库表（包括下游服务）
            tables = []
            for method_sig in methods_to_query:
                tables.extend(self._query_tables(method_sig, max_depth))
            # 去重
            tables = list({(t.project, t.mapper_fqn, t.table_name): t for t in tables}.values())
            
            # 6. 查询涉及的 Aries Job（包括下游服务）
            aries_jobs = []
            for method_sig in methods_to_query:
                aries_jobs.extend(self._query_aries_jobs(method_sig, max_depth))
            # 去重
            aries_jobs = list({(j.project, j.class_fqn): j for j in aries_jobs}.values())
            
            # 7. 查询涉及的 MQ（包括下游服务）
            mq_info = []
            for method_sig in methods_to_query:
                mq_info.extend(self._query_mq_info(method_sig, max_depth))
            # 去重
            mq_info = list({(m.project, m.class_fqn, m.topic): m for m in mq_info}.values())
            
            # 8. 重新查询内部类（包括下游服务的类）
            for method_sig in downstream_methods:
                internal_classes.extend(self._query_internal_classes(method_sig, max_depth))
            # 去重
            internal_classes = list({(ic.project, ic.class_fqn): ic for ic in internal_classes}.values())
            
            # 9. 构建调用树（与列表使用同一 max_depth，深度=边数）
            call_tree = self._build_call_tree(start_method, current_depth=0, max_depth=max_depth, visited=set())
            
            return MCPQueryResult(
                success=True,
                message=f"查询成功：共找到 {len(internal_classes)} 个内部类、{len(dubbo_calls)} 个 Dubbo 调用、{len(tables)} 个表",
                endpoints=endpoints,
                internal_classes=internal_classes,
                dubbo_calls=dubbo_calls,
                tables=tables,
                aries_jobs=aries_jobs,
                mq_info=mq_info,
                call_tree=call_tree
            )
        
        except Exception as e:
            logger.error(f"MCP 查询失败: {e}", exc_info=True)
            return MCPQueryResult(
                success=False,
                message=f"查询失败: {str(e)}",
                endpoints=[],
                internal_classes=[],
                dubbo_calls=[],
                tables=[],
                aries_jobs=[],
                mq_info=[]
            )
    
    def _find_dubbo_downstream_methods(self, dubbo_calls: List[DubboCallInfo]) -> List[str]:
        """
        从 Dubbo 调用信息中找到下游服务的实现类方法
        """
        downstream_methods = []
        
        for dc in dubbo_calls:
            # 查找 Dubbo 接口的实现类方法
            result = self.storage.execute_query("""
                MATCH (iface:INTERFACE {fqn: $dubbo_interface})
                MATCH (iface)-[:DECLARES]->(iface_method:Method {name: $dubbo_method})
                MATCH (impl_class:CLASS)-[:IMPLEMENTS]->(iface)
                MATCH (impl_class)-[:DECLARES]->(impl_method:Method)
                WHERE impl_method.name = iface_method.name
                OPTIONAL MATCH (impl_project:Project)-[:CONTAINS]->(impl_class)
                RETURN DISTINCT 
                    impl_method.signature as impl_signature,
                    impl_project.name as impl_project
            """, {
                'dubbo_interface': dc.dubbo_interface,
                'dubbo_method': dc.dubbo_method
            })
            
            for r in result:
                impl_sig = r['impl_signature']
                impl_proj = r['impl_project']
                if impl_sig and impl_sig not in downstream_methods:
                    downstream_methods.append(impl_sig)
                    logger.info(f"  找到下游实现: {impl_proj}.{impl_sig}")
        
        return downstream_methods
    
    def _find_implementation_methods(self, interface_method_sig: str) -> List[str]:
        """
        查找接口方法的所有实现类方法。
        支持完整签名与 scanner 生成的简化签名（class_fqn.methodName(...)），
        否则通过接口扫描得到的完整签名无法匹配，导致实现类（如 RewardServiceImpl.rewardGift）不会出现在树中。
        """
        # 先按完整签名匹配
        result = self.storage.execute_query("""
            MATCH (iface:INTERFACE)-[:DECLARES]->(iface_method:Method {signature: $method_sig})
            MATCH (impl_class:CLASS)-[:IMPLEMENTS]->(iface)
            MATCH (impl_class)-[:DECLARES]->(impl_method:Method)
            WHERE impl_method.name = iface_method.name
            RETURN DISTINCT impl_method.signature as impl_signature
        """, {'method_sig': interface_method_sig})
        impl_methods = [r['impl_signature'] for r in result]

        # 若未命中且为简化签名（xxx.methodName(...)），按「接口 FQN + 方法名」再查一次
        if not impl_methods and interface_method_sig.endswith('(...)'):
            # 解析出 class_fqn 与 method_name，例如 com.xxx.RewardService.rewardGift(...) -> RewardService FQN + rewardGift
            parts = interface_method_sig[:-5].rsplit('.', 1)  # 去掉 '(...)'
            if len(parts) == 2:
                iface_fqn, method_name = parts[0], parts[1]
                result = self.storage.execute_query("""
                    MATCH (iface:INTERFACE)
                    WHERE iface.fqn = $iface_fqn
                    MATCH (iface)-[:DECLARES]->(iface_method:Method)
                    WHERE iface_method.name = $method_name
                    MATCH (impl_class:CLASS)-[:IMPLEMENTS]->(iface)
                    MATCH (impl_class)-[:DECLARES]->(impl_method:Method)
                    WHERE impl_method.name = iface_method.name
                    RETURN DISTINCT impl_method.signature as impl_signature
                """, {'iface_fqn': iface_fqn, 'method_name': method_name})
                impl_methods = [r['impl_signature'] for r in result]
                if impl_methods:
                    logger.info(f"通过简化签名解析到接口 {iface_fqn}.{method_name}，找到 {len(impl_methods)} 个实现类方法")

        if impl_methods:
            logger.info(f"接口方法 {interface_method_sig} 有 {len(impl_methods)} 个实现类方法")
        return impl_methods
    
    def _find_start_method(self, project: str, class_fqn: str, method: str) -> Optional[str]:
        """查找起始方法的签名"""
        # 1. 尝试精确匹配 FQN
        result = self.storage.execute_query("""
            MATCH (p:Project {name: $project})-[:CONTAINS]->(c)
            WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER OR c:ARIES_JOB) AND c.fqn = $class_fqn
            MATCH (c)-[:DECLARES]->(m:Method)
            WHERE m.name = $method
            RETURN m.signature as signature
            LIMIT 1
        """, {
            'project': project,
            'class_fqn': class_fqn,
            'method': method
        })
        
        if result:
            return result[0]['signature']
        
        # 2. 尝试通过类名模糊匹配（支持简写）
        # 从 FQN 中提取类名（最后一段）
        class_name = class_fqn.split('.')[-1] if '.' in class_fqn else class_fqn
        
        result = self.storage.execute_query("""
            MATCH (p:Project {name: $project})-[:CONTAINS]->(c)
            WHERE (c:CLASS OR c:INTERFACE OR c:MAPPER OR c:ARIES_JOB) 
              AND c.name = $class_name
            MATCH (c)-[:DECLARES]->(m:Method)
            WHERE m.name = $method
            RETURN m.signature as signature, c.fqn as actual_fqn
            LIMIT 1
        """, {
            'project': project,
            'class_name': class_name,
            'method': method
        })
        
        if result:
            logger.info(f"通过类名匹配找到方法: {result[0]['actual_fqn']}.{method}")
            return result[0]['signature']
        
        # 3. 如果是接口，尝试查找实现类
        result = self.storage.execute_query("""
            MATCH (p:Project {name: $project})-[:CONTAINS]->(iface:INTERFACE)
            WHERE iface.fqn = $class_fqn OR iface.name = $class_name
            MATCH (impl)-[:IMPLEMENTS]->(iface)
            MATCH (impl)-[:DECLARES]->(m:Method)
            WHERE m.name = $method
            RETURN m.signature as signature, impl.fqn as actual_fqn
            LIMIT 1
        """, {
            'project': project,
            'class_fqn': class_fqn,
            'class_name': class_name,
            'method': method
        })
        
        if result:
            logger.info(f"通过接口实现类找到方法: {result[0]['actual_fqn']}.{method}")
            return result[0]['signature']
        
        return None
    
    def _query_endpoints(self, start_method: str) -> List[EndpointInfo]:
        """
        查询前端用户入口（RPC Endpoint）
        
        逻辑：
        1. 先查询方法自身的 RpcEndpoint
        2. 如果方法实现了接口，查询接口方法的 RpcEndpoint（@MobileAPI 可能在接口上）
        3. 反向查询：谁通过 DUBBO_CALLS 调用了这个方法，并查询调用方的 RpcEndpoint
           - 先查调用方自身的 RpcEndpoint
           - 如果调用方实现了接口，查询调用方接口的 RpcEndpoint
        """
        endpoints = []
        
        # 1. 查询方法自身的 RpcEndpoint
        result = self.storage.execute_query("""
            MATCH (m:Method {signature: $start_method})-[:EXPOSES]->(ep:RpcEndpoint)
            MATCH (c)-[:DECLARES]->(m)
            OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
            RETURN 
                p.name as project,
                c.fqn as class_fqn,
                m.name as method,
                ep.path as path,
                ep.http_method as http_method
        """, {'start_method': start_method})
        
        for r in result:
            endpoints.append(EndpointInfo(
                project=r['project'] or '',
                class_fqn=r['class_fqn'],
                method=r['method'],
                path=r['path'] or '',
                http_method=r['http_method'] or ''
            ))
        
        # 2. 如果方法所属的类实现了接口，查询接口方法的 RpcEndpoint
        # 场景：@MobileAPI 注解在接口上（Dubbo 服务接口）
        result = self.storage.execute_query("""
            MATCH (impl_class)-[:DECLARES]->(impl_method:Method {signature: $start_method})
            MATCH (impl_class)-[:IMPLEMENTS]->(iface:INTERFACE)
            MATCH (iface)-[:DECLARES]->(iface_method:Method)
            WHERE iface_method.name = impl_method.name
            OPTIONAL MATCH (iface_method)-[:EXPOSES]->(ep:RpcEndpoint)
            RETURN 
                iface.fqn as class_fqn,
                iface_method.name as method,
                ep.path as path,
                ep.http_method as http_method
        """, {'start_method': start_method})
        
        for r in result:
            if r['path']:  # 只添加有 RpcEndpoint 的
                endpoint = EndpointInfo(
                    project='',  # 接口可能不属于任何项目
                    class_fqn=r['class_fqn'],
                    method=r['method'],
                    path=r['path'],
                    http_method=r['http_method'] or ''
                )
                if endpoint not in endpoints:
                    endpoints.append(endpoint)
        
        # 3. 反向查询：谁通过 DUBBO_CALLS 调用了这个方法
        # 场景：从 Dubbo 服务实现类出发，查找上游调用方
        result = self.storage.execute_query("""
            MATCH (impl_class)-[:DECLARES]->(impl_method:Method {signature: $start_method})
            MATCH (impl_class)-[:IMPLEMENTS]->(iface:INTERFACE)
            MATCH (iface)-[:DECLARES]->(iface_method:Method)
            WHERE iface_method.name = impl_method.name
            MATCH (caller_method:Method)-[:DUBBO_CALLS]->(iface_method)
            MATCH (caller_class)-[:DECLARES]->(caller_method)
            
            // 先获取调用方的基本信息
            WITH DISTINCT caller_class, caller_method
            
            // 3.1 查调用方自身的 RpcEndpoint
            OPTIONAL MATCH (caller_method)-[:EXPOSES]->(ep1:RpcEndpoint)
            
            // 3.2 查询调用方实现的接口方法的 RpcEndpoint
            // 使用 WITH 限制笛卡尔积
            WITH caller_class, caller_method, 
                 ep1.path as ep1_path, 
                 ep1.http_method as ep1_http_method
            
            OPTIONAL MATCH (caller_class)-[:IMPLEMENTS]->(caller_iface:INTERFACE)
            WHERE NOT caller_iface.fqn CONTAINS 'java.util'  // 过滤错误的接口
            OPTIONAL MATCH (caller_iface)-[:DECLARES]->(caller_iface_method:Method)
            WHERE caller_iface_method.name = caller_method.name
            OPTIONAL MATCH (caller_iface_method)-[:EXPOSES]->(ep2:RpcEndpoint)
            
            // 获取项目信息
            OPTIONAL MATCH (p:Project)-[:CONTAINS]->(caller_class)
            
            // 返回调用方的信息，优先使用调用方自身的 RpcEndpoint，其次使用调用方接口的
            RETURN DISTINCT
                p.name as project,
                caller_class.fqn as class_fqn,
                caller_method.name as method,
                COALESCE(ep1_path, ep2.path) as path,
                COALESCE(ep1_http_method, ep2.http_method) as http_method
        """, {'start_method': start_method})
        
        for r in result:
            if r['path']:  # 只添加有 RpcEndpoint 的
                endpoint = EndpointInfo(
                    project=r['project'] or '',
                    class_fqn=r['class_fqn'],
                    method=r['method'],
                    path=r['path'],
                    http_method=r['http_method'] or ''
                )
                if endpoint not in endpoints:
                    endpoints.append(endpoint)
        
        return endpoints
    
    def _query_internal_classes(self, start_method: str, max_depth: int) -> List[InternalClassInfo]:
        """查询涉及的内部类（非外部 Dubbo）"""
        result = self.storage.execute_query(f"""
            MATCH (start:Method {{signature: $start_method}})
            MATCH path = (start)-[:CALLS|DB_CALL*0..{max_depth}]->(m:Method)
            MATCH (c)-[:DECLARES]->(m)
            WHERE c.is_external IS NULL OR c.is_external = false
            MATCH (p:Project)-[:CONTAINS]->(c)
            RETURN DISTINCT
                p.name as project,
                c.fqn as class_fqn,
                c.name as class_name,
                c.arch_layer as arch_layer
            ORDER BY p.name, c.fqn
        """, {'start_method': start_method})
        
        classes = []
        for r in result:
            classes.append(InternalClassInfo(
                project=r['project'],
                class_fqn=r['class_fqn'],
                class_name=r['class_name'],
                arch_layer=r['arch_layer'] or 'Other'
            ))
        
        return classes
    
    def _query_dubbo_calls(self, start_method: str, max_depth: int) -> List[DubboCallInfo]:
        """查询调用链中的 Dubbo 调用。深度=边数，*0..N 表示从起点出发 0～N 条 CALLS 边内的调用。"""
        result = self.storage.execute_query(f"""
            MATCH (start:Method {{signature: $start_method}})
            // 深度=边数：0 条边=起点自身，1 条边=起点直接调用的方法，N 条边=N 层
            MATCH path = (start)-[:CALLS*0..{max_depth}]->(caller:Method)-[dubbo_rel:DUBBO_CALLS]->(dubbo_iface_method:Method)
            MATCH (dubbo_iface:INTERFACE)-[:DECLARES]->(dubbo_iface_method)
            
            // 尝试找到实现类（可能不存在，外部服务）
            OPTIONAL MATCH (impl_class:CLASS)-[:IMPLEMENTS]->(dubbo_iface)
            OPTIONAL MATCH (impl_class)-[:DECLARES]->(impl_method:Method)
            WHERE impl_method IS NULL OR impl_method.name = dubbo_iface_method.name
            
            // 获取项目信息
            MATCH (caller_class)-[:DECLARES]->(caller)
            OPTIONAL MATCH (caller_project:Project)-[:CONTAINS]->(caller_class)
            OPTIONAL MATCH (impl_project:Project)-[:CONTAINS]->(impl_class)
            OPTIONAL MATCH (iface_project:Project)-[:CONTAINS]->(dubbo_iface)
            
            // 只返回跨项目的 Dubbo 调用（或者实现类不存在的外部服务）
            WHERE impl_project IS NULL OR caller_project.name <> impl_project.name
            
            RETURN DISTINCT
                caller_project.name as caller_project,
                caller_class.fqn as caller_class,
                caller.name as caller_method,
                dubbo_iface.fqn as dubbo_interface,
                dubbo_iface_method.name as dubbo_method,
                dubbo_rel.via_field as via_field,
                impl_project.name as target_project,
                iface_project.name as iface_project
            ORDER BY caller_project, caller_class, dubbo_interface
        """, {'start_method': start_method})
        
        dubbo_calls = []
        for r in result:
            dubbo_call = DubboCallInfo(
                caller_project=r['caller_project'],
                caller_class=r['caller_class'],
                caller_method=r['caller_method'],
                dubbo_interface=r['dubbo_interface'],
                dubbo_method=r['dubbo_method'],
                via_field=r['via_field'] or '',
                target_project=r['target_project'] or r['iface_project'] or 'External'
            )
            # 去重：只添加不重复的 Dubbo 调用
            if dubbo_call not in dubbo_calls:
                dubbo_calls.append(dubbo_call)
        
        return dubbo_calls
    
    def _query_tables(self, start_method: str, max_depth: int) -> List[TableInfo]:
        """查询涉及的数据库表（支持接口到实现类的跳转）"""
        # 优化策略：限制深度，只处理接口方法的跳转
        result = self.storage.execute_query(f"""
            MATCH (start:Method {{signature: $start_method}})
            
            // 查找调用链中的所有方法（限制深度为 8）
            MATCH path = (start)-[:CALLS*1..8]->(called_method:Method)
            
            WITH DISTINCT called_method
            MATCH (called_class)-[:DECLARES]->(called_method)
            
            // 只处理接口方法
            WHERE called_class:INTERFACE
            
            // 找实现类的同名方法
            MATCH (impl_class:CLASS)-[:IMPLEMENTS]->(called_class)
            MATCH (impl_class)-[:DECLARES]->(impl_method:Method {{name: called_method.name}})
            
            // 从实现类方法查找 DB_CALL（限制深度为 5）
            MATCH db_path = (impl_method)-[:CALLS|DB_CALL*1..5]->(mapper_method:Method)
            WHERE ANY(rel IN relationships(db_path) WHERE type(rel) = 'DB_CALL')
            
            WITH DISTINCT mapper_method
            MATCH (mapper:MAPPER)-[:DECLARES]->(mapper_method)
            MATCH (p:Project)-[:CONTAINS]->(mapper)
            OPTIONAL MATCH (mapper)-[:MAPPER_FOR_TABLE]->(table:Table)
            
            RETURN DISTINCT
                p.name as project,
                mapper.fqn as mapper_fqn,
                mapper.name as mapper_name,
                table.name as table_name
            ORDER BY p.name, mapper_fqn, table_name
        """, {'start_method': start_method})
        
        tables = []
        for r in result:
            tables.append(TableInfo(
                project=r['project'],
                mapper_fqn=r['mapper_fqn'],
                mapper_name=r['mapper_name'],
                table_name=r['table_name']
            ))
        
        return tables
    
    def _query_aries_jobs(self, start_method: str, max_depth: int) -> List[AriesJobInfo]:
        """查询涉及的 Aries Job"""
        result = self.storage.execute_query(f"""
            MATCH (start:Method {{signature: $start_method}})
            MATCH path = (start)-[:CALLS|DB_CALL|DUBBO_CALLS*0..{max_depth}]->(job_method:Method)
            MATCH (job_method)-[:EXECUTES_JOB]->(job:Job)
            MATCH (job_class:ARIES_JOB)-[:DECLARES]->(job_method)
            MATCH (p:Project)-[:CONTAINS]->(job_class)
            
            RETURN DISTINCT
                p.name as project,
                job_class.fqn as class_fqn,
                job_class.name as class_name,
                job.job_type as job_type,
                job.cron_expr as cron_expr
            ORDER BY p.name, class_fqn
        """, {'start_method': start_method})
        
        jobs = []
        for r in result:
            jobs.append(AriesJobInfo(
                project=r['project'],
                class_fqn=r['class_fqn'],
                class_name=r['class_name'],
                job_type=r['job_type'] or 'unknown',
                cron_expr=r['cron_expr']
            ))
        
        return jobs
    
    def _query_mq_info(self, start_method: str, max_depth: int) -> List[MQInfo]:
        """查询涉及的 MQ 信息（消费者和生产者）"""
        mq_list = []
        
        # 1. 查询 MQ 消费者（从 start_method 所在类开始）
        consumers = self.storage.execute_query(f"""
            MATCH (start:Method {{signature: $start_method}})
            MATCH (start_class)-[:DECLARES]->(start)
            MATCH (p:Project)-[:CONTAINS]->(start_class)
            
            MATCH path = (start)-[:CALLS|DB_CALL*0..{max_depth}]->(consumer_method:Method)
            MATCH (consumer_class)-[:DECLARES]->(consumer_method)
            WHERE consumer_class:CLASS OR consumer_class:MAPPER OR consumer_class:ARIES_JOB
            
            MATCH (consumer_class)-[consumer_rel]->(topic:MQ_TOPIC)
            WHERE type(consumer_rel) IN ['MQ_KAFKA_CONSUMER', 'MQ_ROCKET_CONSUMER']
            MATCH (topic)-[:MQ_CONSUMES_METHOD]->(consumer_method)
            
            MATCH (consumer_project:Project)-[:CONTAINS]->(consumer_class)
            
            RETURN DISTINCT
                consumer_project.name as project,
                consumer_class.fqn as class_fqn,
                consumer_class.name as class_name,
                topic.mq_type as mq_type,
                topic.name as topic_name,
                consumer_method.name as method_name,
                type(consumer_rel) as rel_type
        """, {'start_method': start_method})
        
        for r in consumers:
            mq_list.append(MQInfo(
                project=r['project'],
                class_fqn=r['class_fqn'],
                class_name=r['class_name'],
                mq_type=r['mq_type'],
                topic=r['topic_name'],
                role='consumer',
                method=r['method_name']
            ))
        
        # 2. 查询 MQ 生产者（从 start_method 开始的调用链中）
        producers = self.storage.execute_query(f"""
            MATCH (start:Method {{signature: $start_method}})
            MATCH path = (start)-[:CALLS|DB_CALL|DUBBO_CALLS*0..{max_depth}]->(producer_method:Method)
            MATCH (producer_method)-[producer_rel]->(topic:MQ_TOPIC)
            WHERE type(producer_rel) IN ['MQ_KAFKA_PRODUCER', 'MQ_ROCKET_PRODUCER']
            
            MATCH (producer_class)-[:DECLARES]->(producer_method)
            MATCH (producer_project:Project)-[:CONTAINS]->(producer_class)
            
            RETURN DISTINCT
                producer_project.name as project,
                producer_class.fqn as class_fqn,
                producer_class.name as class_name,
                topic.mq_type as mq_type,
                topic.name as topic_name,
                producer_method.name as method_name,
                type(producer_rel) as rel_type
        """, {'start_method': start_method})
        
        for r in producers:
            mq_list.append(MQInfo(
                project=r['project'],
                class_fqn=r['class_fqn'],
                class_name=r['class_name'],
                mq_type=r['mq_type'],
                topic=r['topic_name'],
                role='producer',
                method=r['method_name']
            ))
        
        return mq_list
    
    def _build_call_tree(self, method_sig: str, current_depth: int = 0, max_depth: int = 10, visited: set = None) -> Optional[CallNode]:
        """
        递归构建调用树。
        深度 = 从根到当前节点的边数：A→B 为 1 层，A→B→C 为 2 层。

        Args:
            method_sig: 方法签名
            current_depth: 当前节点距根的边数（0=根节点）
            max_depth: 允许的最大边数，超过则不再展开子节点
            visited: 已访问的方法（防止循环调用）

        Returns:
            CallNode: 调用树节点（current_depth > max_depth 时仍返回节点但不展开子节点）
        """
        if visited is None:
            visited = set()

        if method_sig in visited:
            return None

        visited.add(method_sig)
        
        # 查询方法信息（检查是接口还是类）
        result = self.storage.execute_query("""
            MATCH (c)-[:DECLARES]->(m:Method {signature: $method_sig})
            OPTIONAL MATCH (p:Project)-[:CONTAINS]->(c)
            RETURN 
                p.name as project,
                c.fqn as class_fqn,
                c.name as class_name,
                c.arch_layer as arch_layer,
                m.name as method_name,
                m.signature as method_signature,
                labels(c) as labels
        """, {'method_sig': method_sig})
        
        if not result:
            return None
        
        r = result[0]
        is_interface = 'INTERFACE' in r['labels']
        
        # 创建根节点
        root = CallNode(
            node_type='interface' if is_interface else 'method',
            project=r['project'] or 'Unknown',
            class_fqn=r['class_fqn'],
            class_name=r['class_name'],
            method_name=r['method_name'],
            method_signature=r['method_signature'],
            arch_layer=r['arch_layer'] or 'Other'
        )
        
        # 是否继续向下展开（深度=边数，未超过 max_depth 才展开）
        can_expand = current_depth < max_depth

        # 如果是接口方法，为每个实现类创建子树
        if is_interface and can_expand:
            impl_methods = self._find_implementation_methods(method_sig)
            for impl_sig in impl_methods:
                if impl_sig not in visited:
                    impl_tree = self._build_call_tree(impl_sig, current_depth + 1, max_depth, visited)
                    if impl_tree:
                        root.children.append(impl_tree)

        # 1. 查询 Dubbo 调用
        dubbo_result = self.storage.execute_query("""
            MATCH (m:Method {signature: $method_sig})-[dubbo_rel:DUBBO_CALLS]->(dubbo_iface_method:Method)
            MATCH (dubbo_iface:INTERFACE)-[:DECLARES]->(dubbo_iface_method)
            OPTIONAL MATCH (impl_class:CLASS)-[:IMPLEMENTS]->(dubbo_iface)
            OPTIONAL MATCH (impl_class)-[:DECLARES]->(impl_method:Method)
            WHERE impl_method IS NULL OR impl_method.name = dubbo_iface_method.name
            OPTIONAL MATCH (impl_project:Project)-[:CONTAINS]->(impl_class)
            OPTIONAL MATCH (iface_project:Project)-[:CONTAINS]->(dubbo_iface)
            RETURN DISTINCT
                dubbo_iface.fqn as dubbo_interface,
                dubbo_iface_method.name as dubbo_method,
                dubbo_rel.via_field as via_field,
                impl_method.signature as impl_signature,
                impl_project.name as impl_project,
                impl_class.fqn as impl_class_fqn,
                impl_class.name as impl_class_name,
                iface_project.name as iface_project
        """, {'method_sig': method_sig})
        
        for dr in dubbo_result:
            # 创建 Dubbo 调用节点
            # 如果有实现类，使用实现类信息；否则使用接口信息
            dubbo_node = CallNode(
                node_type='dubbo_call',
                project=dr['impl_project'] or dr['iface_project'] or 'External',
                class_fqn=dr['impl_class_fqn'] or dr['dubbo_interface'],
                class_name=dr['impl_class_name'] or dr['dubbo_interface'].split('.')[-1],
                dubbo_interface=dr['dubbo_interface'],
                dubbo_method=dr['dubbo_method'],
                via_field=dr['via_field']
            )
            
            # 递归查询下游实现类方法（如果有）
            if can_expand:
                impl_sig = dr.get('impl_signature')
                if impl_sig and impl_sig not in visited:
                    impl_tree = self._build_call_tree(impl_sig, current_depth + 1, max_depth, visited)
                    if impl_tree:
                        dubbo_node.children.append(impl_tree)

            root.children.append(dubbo_node)

        # 2. 查询内部方法调用（放宽：不按项目过滤，避免同仓库多模块时漏掉 Service 等；提高 LIMIT 避免截断核心下游）
        calls_result = self.storage.execute_query("""
            MATCH (m:Method {signature: $method_sig})-[:CALLS]->(called_method:Method)
            MATCH (called_class)-[:DECLARES]->(called_method)
            OPTIONAL MATCH (called_project:Project)-[:CONTAINS]->(called_class)
            RETURN DISTINCT
                called_method.signature as called_signature,
                called_project.name as called_project,
                called_class.fqn as called_class_fqn,
                called_class.name as called_class_name,
                called_class.arch_layer as called_arch_layer,
                called_method.name as called_method_name
            LIMIT 80
        """, {'method_sig': method_sig})
        
        for cr in calls_result:
            if not can_expand:
                break
            called_sig = cr['called_signature']
            if called_sig and called_sig not in visited:
                child_tree = self._build_call_tree(called_sig, current_depth + 1, max_depth, visited)
                if child_tree:
                    root.children.append(child_tree)

        # 3. 查询数据库调用
        db_result = self.storage.execute_query("""
            MATCH (m:Method {signature: $method_sig})-[:CALLS|DB_CALL*1..3]->(mapper_method:Method)
            MATCH (mapper:MAPPER)-[:DECLARES]->(mapper_method)
            MATCH (mapper)-[:MAPPER_FOR_TABLE]->(table:Table)
            OPTIONAL MATCH (mapper_project:Project)-[:CONTAINS]->(mapper)
            RETURN DISTINCT
                mapper_project.name as mapper_project,
                mapper.fqn as mapper_fqn,
                mapper.name as mapper_name,
                table.name as table_name
            LIMIT 5
        """, {'method_sig': method_sig})
        
        for dbr in db_result:
            db_node = CallNode(
                node_type='db_call',
                project=dbr['mapper_project'] or 'Unknown',
                class_fqn=dbr['mapper_fqn'],
                class_name=dbr['mapper_name'],
                table_name=dbr['table_name'],
                mapper_name=dbr['mapper_name']
            )
            root.children.append(db_node)
        
        return root
    
    def query_upstream(
        self,
        project: str,
        class_fqn: str,
        method: str,
        max_depth: int = 10
    ) -> MCPQueryResult:
        """
        查询上游调用链（谁调用了这个方法）
        
        Args:
            project: 项目名称
            class_fqn: 类的全限定名
            method: 方法名
            max_depth: 最大查询深度
        
        Returns:
            MCPQueryResult: 结构化的查询结果
        """
        # TODO: 实现上游查询逻辑
        return MCPQueryResult(
            success=False,
            message="上游查询功能待实现",
            endpoints=[],
            internal_classes=[],
            dubbo_calls=[],
            tables=[],
            aries_jobs=[],
            mq_info=[]
        )
