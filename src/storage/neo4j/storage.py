"""
Neo4j 存储实现
实现 GraphStorage 接口
"""

import os
import logging
from typing import List, Dict, Optional, Any
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from ...core.interfaces import GraphStorage
from ...core.models import CodeEntity, CodeRelationship, EntityType, RelationshipType

logger = logging.getLogger(__name__)


class Neo4jStorage(GraphStorage):
    """Neo4j 图数据库存储实现"""
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        初始化存储
        
        Args:
            uri: Neo4j URI，默认从环境变量读取
            user: Neo4j 用户名，默认从环境变量读取
            password: Neo4j 密码，默认从环境变量读取
        """
        self.uri = uri or os.getenv('NEO4J_URI') or os.getenv('JQASSISTANT_NEO4J_URI', 'bolt://localhost:7687')
        self.user = user or os.getenv('NEO4J_USER') or os.getenv('JQASSISTANT_NEO4J_USER', 'neo4j')
        self.password = password or os.getenv('NEO4J_PASSWORD') or os.getenv('JQASSISTANT_NEO4J_PASSWORD', 'password')
        
        self.driver = None
        self._connected = False
    
    def connect(self) -> bool:
        """连接数据库"""
        logger.info("=" * 60)
        logger.info("[Neo4j Storage] 尝试连接到 Neo4j...")
        logger.info(f"  URI: {self.uri}")
        logger.info(f"  User: {self.user}")
        
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            
            # 测试连接
            logger.info("[Neo4j Storage] 测试连接...")
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()
                logger.info(f"[Neo4j Storage] 测试查询返回: {test_value}")
            
            self._connected = True
            logger.info(f"✅ [Neo4j Storage] 成功连接到 Neo4j: {self.uri}")
            logger.info("=" * 60)
            return True
            
        except AuthError as e:
            logger.error(f"❌ [Neo4j Storage] 认证失败: {e}")
            logger.error(f"   请检查用户名({self.user})和密码是否正确")
            self._connected = False
            logger.info("=" * 60)
            return False
            
        except ServiceUnavailable as e:
            logger.error(f"❌ [Neo4j Storage] 服务不可用: {e}")
            logger.error(f"   请检查 Neo4j 是否运行在 {self.uri}")
            self._connected = False
            logger.info("=" * 60)
            return False
            
        except Exception as e:
            logger.error(f"❌ [Neo4j Storage] 连接失败: {e}", exc_info=True)
            self._connected = False
            logger.info("=" * 60)
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.driver:
            self.driver.close()
            self._connected = False
            logger.info("Neo4j 连接已关闭")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    def create_entities(self, entities: List[CodeEntity]) -> int:
        """
        批量创建实体
        
        Returns:
            创建的实体数量
        """
        if not self.is_connected():
            if not self.connect():
                raise RuntimeError("无法连接到 Neo4j")
        
        created_count = 0
        
        try:
            with self.driver.session() as session:
                # 按类型分组处理
                for entity in entities:
                    try:
                        self._create_entity(session, entity)
                        created_count += 1
                    except Exception as e:
                        logger.warning(f"创建实体失败 {entity.id}: {e}")
                        continue
                # Neo4j session 在 with 块结束时自动提交
        
        except Exception as e:
            logger.error(f"批量创建实体失败: {e}", exc_info=True)
            raise
        
        return created_count
    
    def create_relationships(self, relationships: List[CodeRelationship]) -> int:
        """
        批量创建关系
        
        Returns:
            创建的关系数量
        """
        if not self.is_connected():
            if not self.connect():
                raise RuntimeError("无法连接到 Neo4j")
        
        created_count = 0
        
        try:
            with self.driver.session() as session:
                for relationship in relationships:
                    try:
                        self._create_relationship(session, relationship)
                        created_count += 1
                    except Exception as e:
                        logger.warning(f"创建关系失败 {relationship.id}: {e}")
                        continue
                # Neo4j session 在 with 块结束时自动提交
        
        except Exception as e:
            logger.error(f"批量创建关系失败: {e}", exc_info=True)
            raise
        
        return created_count
    
    def project_exists(self, project_name: str) -> bool:
        """检查项目是否存在"""
        if not self.is_connected():
            if not self.connect():
                return False
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    "MATCH (p:Project {name: $name}) RETURN count(p) as count",
                    {"name": project_name}
                )
                record = result.single()
                return record['count'] > 0 if record else False
        except Exception:
            return False
    
    def begin_transaction(self):
        """开始事务（Neo4j 自动管理事务，此方法为空实现）"""
        # Neo4j 的 session 自动管理事务，不需要显式开始
        pass
    
    def commit_transaction(self):
        """提交事务（Neo4j 自动管理事务，此方法为空实现）"""
        # Neo4j 的 session 自动管理事务，在 with 块结束时自动提交
        pass
    
    def rollback_transaction(self):
        """回滚事务（Neo4j 自动管理事务，此方法为空实现）"""
        # Neo4j 的 session 自动管理事务，异常时自动回滚
        pass
    
    def _create_entity(self, session, entity: CodeEntity):
        """创建单个实体"""
        # 根据实体类型选择标签
        label = self._get_entity_label(entity.type)
        
        # 构建属性（排除 None 值）
        properties = {
            'name': entity.name,
            'qualified_name': entity.qualified_name,
            'file_path': entity.file_path or '',
            'start_line': entity.start_line,
            'end_line': entity.end_line,
            'language': entity.language,
            'project': entity.project
        }
        
        # 添加元数据（排除 None 值）
        for key, value in entity.metadata.items():
            if value is not None:
                properties[key] = value
        
        # 根据实体类型使用不同的主键
        if entity.type == EntityType.PROJECT:
            # Project 使用 name 作为主键，需要设置 path、scanned_at、scanned_commit_id 和 scanner
            query = f"""
                MERGE (e:{label} {{name: $name}})
                SET e.path = $path,
                    e.scanned_at = datetime(),
                    e.scanned_commit_id = $scanned_commit_id,
                    e.scanner = 'python-ast',
                    e += $properties
            """
            session.run(query, {
                'name': entity.name,
                'path': entity.metadata.get('path', ''),
                'scanned_commit_id': entity.metadata.get('scanned_commit_id', '') or '',
                'properties': {k: v for k, v in properties.items() if k not in ['path', 'scanned_commit_id']}
            })
        elif entity.type == EntityType.PACKAGE:
            # Package 使用 fqn 作为主键，需要设置 name 属性
            query = f"""
                MERGE (e:{label} {{fqn: $qualified_name}})
                SET e.name = $name,
                    e += $properties
            """
            session.run(query, {
                'qualified_name': entity.qualified_name,
                'name': entity.name,
                'properties': properties
            })
        elif entity.type == EntityType.TYPE:
            # Type 使用 fqn 作为主键，需要设置 scanned_at 和 super_class
            query = f"""
                MERGE (e:{label} {{fqn: $qualified_name}})
                SET e.name = $name,
                    e.kind = $kind,
                    e.visibility = $visibility,
                    e.is_abstract = $is_abstract,
                    e.is_final = $is_final,
                    e.super_class = $super_class,
                    e.file_path = $file_path,
                    e.scanned_at = datetime(),
                    e += $properties
            """
            session.run(query, {
                'qualified_name': entity.qualified_name,
                'name': entity.name,
                'kind': entity.metadata.get('kind', 'CLASS'),
                'visibility': entity.metadata.get('visibility', 'PACKAGE'),
                'is_abstract': entity.metadata.get('is_abstract', False),
                'is_final': entity.metadata.get('is_final', False),
                'super_class': entity.metadata.get('super_class', '') or '',
                'file_path': entity.file_path or '',
                'properties': {k: v for k, v in properties.items() if k not in ['name', 'kind', 'visibility', 'is_abstract', 'is_final', 'super_class', 'file_path']}
            })
        elif entity.type == EntityType.METHOD:
            # Method 使用 signature 作为主键
            query = f"""
                MERGE (e:{label} {{signature: $qualified_name}})
                SET e.name = $name,
                    e.return_type = $return_type,
                    e.visibility = $visibility,
                    e.is_static = $is_static,
                    e.is_abstract = $is_abstract,
                    e.parameter_count = $parameter_count,
                    e.line_number = $line_number,
                    e += $properties
            """
            session.run(query, {
                'qualified_name': entity.qualified_name,
                'name': entity.name,
                'return_type': entity.metadata.get('return_type', 'void'),
                'visibility': entity.metadata.get('visibility', 'PACKAGE'),
                'is_static': entity.metadata.get('is_static', False),
                'is_abstract': entity.metadata.get('is_abstract', False),
                'parameter_count': entity.metadata.get('parameter_count', 0),
                'line_number': entity.start_line,
                'properties': {k: v for k, v in properties.items() if k not in ['name', 'return_type', 'visibility', 'is_static', 'is_abstract', 'parameter_count']}
            })
        elif entity.type == EntityType.FIELD:
            # Field 使用 signature 作为主键
            query = f"""
                MERGE (e:{label} {{signature: $qualified_name}})
                SET e.name = $name,
                    e.type = $type,
                    e.visibility = $visibility,
                    e.is_static = $is_static,
                    e.is_final = $is_final,
                    e += $properties
            """
            session.run(query, {
                'qualified_name': entity.qualified_name,
                'name': entity.name,
                'type': entity.metadata.get('type', 'Object'),
                'visibility': entity.metadata.get('visibility', 'PACKAGE'),
                'is_static': entity.metadata.get('is_static', False),
                'is_final': entity.metadata.get('is_final', False),
                'properties': {k: v for k, v in properties.items() if k not in ['name', 'type', 'visibility', 'is_static', 'is_final']}
            })
        elif entity.type == EntityType.MQ_TOPIC:
            # MQTopic 使用 name 和 mq_type 作为主键
            query = f"""
                MERGE (e:{label} {{name: $name, mq_type: $mq_type}})
                SET e.group_id = $group_id,
                    e += $properties
            """
            session.run(query, {
                'name': entity.name,
                'mq_type': entity.metadata.get('mq_type', 'KAFKA'),
                'group_id': entity.metadata.get('group_id', ''),
                'properties': {k: v for k, v in properties.items() if k not in ['group_id']}
            })
        elif entity.type == EntityType.TABLE:
            # Table 使用 name 作为主键
            query = f"""
                MERGE (e:{label} {{name: $name}})
                SET e.entity_fqn = $entity_fqn,
                    e += $properties
            """
            session.run(query, {
                'name': entity.name,
                'entity_fqn': entity.metadata.get('entity_fqn'),
                'properties': {k: v for k, v in properties.items() if k not in ['entity_fqn']}
            })
        elif entity.type == EntityType.ANNOTATION:
            # Annotation 使用 fqn 作为主键
            query = f"""
                MERGE (e:{label} {{fqn: $qualified_name}})
                SET e.name = $name,
                    e += $properties
            """
            session.run(query, {
                'qualified_name': entity.qualified_name,
                'name': entity.name,
                'properties': properties
            })
        else:
            # 其他类型使用 qualified_name 作为主键
            query = f"""
                MERGE (e:{label} {{qualified_name: $qualified_name}})
                SET e += $properties
            """
            session.run(query, {
                'qualified_name': entity.qualified_name,
                'properties': properties
            })
        
        # 创建项目关系
        if entity.type != EntityType.PROJECT and entity.project:
            # 根据实体类型选择匹配字段
            if entity.type == EntityType.PACKAGE:
                match_condition = "e.fqn = $qualified_name"
            elif entity.type in [EntityType.TYPE, EntityType.ANNOTATION]:
                match_condition = "e.fqn = $qualified_name"
            elif entity.type in [EntityType.METHOD, EntityType.FIELD, EntityType.PARAMETER]:
                match_condition = "e.signature = $qualified_name"
            elif entity.type == EntityType.MQ_TOPIC:
                match_condition = "e.name = $name AND e.mq_type = $mq_type"
            elif entity.type == EntityType.TABLE:
                match_condition = "e.name = $name"
            else:
                match_condition = "e.qualified_name = $qualified_name OR e.name = $name"
            
            query = f"""
                MATCH (p:Project {{name: $project_name}})
                MATCH (e:{label})
                WHERE {match_condition}
                MERGE (p)-[:CONTAINS]->(e)
            """
            params = {
                'project_name': entity.project,
                'qualified_name': entity.qualified_name,
                'name': entity.name
            }
            if entity.type == EntityType.MQ_TOPIC:
                params['mq_type'] = entity.metadata.get('mq_type', 'KAFKA')
            session.run(query, params)
        
        # 创建包-类型关系（如果类型有包信息）
        if entity.type == EntityType.TYPE and entity.metadata.get('package'):
            package_name = entity.metadata.get('package')
            query = f"""
                MATCH (pkg:Package {{fqn: $package_name}})
                MATCH (t:Type {{fqn: $qualified_name}})
                MERGE (pkg)-[:CONTAINS]->(t)
            """
            session.run(query, {
                'package_name': package_name,
                'qualified_name': entity.qualified_name
            })
    
    def _create_relationship(self, session, relationship: CodeRelationship):
        """创建单个关系"""
        rel_type = relationship.type.value
        
        # 构建关系属性（排除 None 值）
        rel_properties = {}
        for key, value in relationship.metadata.items():
            if value is not None:
                rel_properties[key] = value
        
        # 提取源和目标 ID（去掉前缀）
        source_id_clean = relationship.source_id.split(':', 1)[-1] if ':' in relationship.source_id else relationship.source_id
        target_id_clean = relationship.target_id.split(':', 1)[-1] if ':' in relationship.target_id else relationship.target_id
        
        # 根据 ID 格式推断节点标识符类型
        source_field = self._infer_id_field(relationship.source_id)
        target_field = self._infer_id_field(relationship.target_id)
        
        # 特殊处理 MQTopic（需要 name 和 mq_type）
        if relationship.target_id.startswith('MQTopic:'):
            # MQTopic ID 格式: MQTopic:KAFKA:topic_name
            parts = relationship.target_id.split(':')
            if len(parts) >= 3:
                mq_type = parts[1]
                topic_name = ':'.join(parts[2:])
                query = f"""
                    MATCH (source)
                    WHERE source.{source_field} = $source_id
                    MATCH (target:MQTopic {{name: $topic_name, mq_type: $mq_type}})
                    MERGE (source)-[r:{rel_type}]->(target)
                """
                params = {
                    'source_id': source_id_clean,
                    'topic_name': topic_name,
                    'mq_type': mq_type
                }
            else:
                query = f"""
                    MATCH (source)
                    WHERE source.{source_field} = $source_id
                    MATCH (target)
                    WHERE target.{target_field} = $target_id
                    MERGE (source)-[r:{rel_type}]->(target)
                """
                params = {
                    'source_id': source_id_clean,
                    'target_id': target_id_clean
                }
        else:
            # 构建查询，根据关系类型可能需要特殊处理
            if rel_type == 'DUBBO_CALLS' and 'field_name' in rel_properties:
                # DUBBO_CALLS 关系需要设置 field_name 属性
                query = f"""
                    MATCH (source:Type)
                    WHERE source.{source_field} = $source_id
                    MATCH (target:Type)
                    WHERE target.{target_field} = $target_id
                    MERGE (source)-[r:{rel_type} {{field_name: $field_name}}]->(target)
                    SET target.name = $target_name
                """
                params = {
                    'source_id': source_id_clean,
                    'target_id': target_id_clean,
                    'field_name': rel_properties.get('field_name', ''),
                    'target_name': target_id_clean.split('.')[-1] if '.' in target_id_clean else target_id_clean
                }
            elif rel_type == 'DUBBO_PROVIDES':
                # DUBBO_PROVIDES 关系需要设置目标节点的 name
                query = f"""
                    MATCH (source:Type)
                    WHERE source.{source_field} = $source_id
                    MATCH (target:Type)
                    WHERE target.{target_field} = $target_id
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET target.name = $target_name
                """
                params = {
                    'source_id': source_id_clean,
                    'target_id': target_id_clean,
                    'target_name': target_id_clean.split('.')[-1] if '.' in target_id_clean else target_id_clean
                }
            elif rel_type in ['EXTENDS', 'IMPLEMENTS']:
                # 继承和实现关系需要设置目标节点的 name
                query = f"""
                    MATCH (source:Type)
                    WHERE source.{source_field} = $source_id
                    MATCH (target:Type)
                    WHERE target.{target_field} = $target_id
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET target.name = $target_name
                """
                params = {
                    'source_id': source_id_clean,
                    'target_id': target_id_clean,
                    'target_name': target_id_clean.split('.')[-1] if '.' in target_id_clean else target_id_clean
                }
            elif rel_type == 'DEPENDS_ON':
                # 依赖关系需要设置目标节点的 name
                query = f"""
                    MATCH (source:Type)
                    WHERE source.{source_field} = $source_id
                    MATCH (target:Type)
                    WHERE target.{target_field} = $target_id
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET target.name = $target_name
                """
                params = {
                    'source_id': source_id_clean,
                    'target_id': target_id_clean,
                    'target_name': target_id_clean.split('.')[-1] if '.' in target_id_clean else target_id_clean
                }
            else:
                query = f"""
                    MATCH (source)
                    WHERE source.{source_field} = $source_id
                    MATCH (target)
                    WHERE target.{target_field} = $target_id
                    MERGE (source)-[r:{rel_type}]->(target)
                """
                params = {
                    'source_id': source_id_clean,
                    'target_id': target_id_clean
                }
        
        # 添加其他关系属性
        if rel_properties and rel_type != 'DUBBO_CALLS':  # DUBBO_CALLS 已经在 MERGE 中设置了
            query += " SET r += $metadata"
            params['metadata'] = {k: v for k, v in rel_properties.items() if k != 'field_name'}
        
        session.run(query, params)
    
    def _infer_id_field(self, entity_id: str) -> str:
        """根据实体 ID 推断节点标识符字段"""
        if entity_id.startswith('Package:'):
            return 'fqn'
        elif entity_id.startswith('Type:'):
            return 'fqn'
        elif entity_id.startswith('Method:'):
            return 'signature'
        elif entity_id.startswith('Field:'):
            return 'signature'
        elif entity_id.startswith('Project:'):
            return 'name'
        elif entity_id.startswith('MQTopic:'):
            # MQTopic 需要 name 和 mq_type，这里简化处理
            return 'name'
        elif entity_id.startswith('Table:'):
            return 'name'
        elif entity_id.startswith('Annotation:'):
            return 'fqn'
        else:
            # 默认尝试多个字段
            return 'qualified_name'
    
    def _get_entity_label(self, entity_type: EntityType) -> str:
        """获取实体类型的 Neo4j 标签"""
        label_map = {
            EntityType.PROJECT: 'Project',
            EntityType.PACKAGE: 'Package',
            EntityType.MODULE: 'Module',
            EntityType.TYPE: 'Type',
            EntityType.METHOD: 'Method',
            EntityType.FIELD: 'Field',
            EntityType.VARIABLE: 'Variable',
            EntityType.FUNCTION: 'Function',
            EntityType.PARAMETER: 'Parameter',
            EntityType.ANNOTATION: 'Annotation',
            EntityType.MQ_TOPIC: 'MQTopic',
            EntityType.TABLE: 'Table'
        }
        return label_map.get(entity_type, 'Entity')
    
    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """
        执行 Cypher 查询（兼容旧接口）
        
        Args:
            query: Cypher 查询语句
            parameters: 查询参数
        
        Returns:
            查询结果列表
        """
        if not self.is_connected():
            if not self.connect():
                raise RuntimeError("无法连接到 Neo4j")
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            logger.error(f"查询: {query}")
            raise
    
    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        执行写入操作（兼容旧接口）
        
        Args:
            query: Cypher 写入语句
            parameters: 参数
        
        Returns:
            执行结果
        """
        if not self.is_connected():
            if not self.connect():
                raise RuntimeError("无法连接到 Neo4j")
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return result.consume()
        except Exception as e:
            logger.error(f"执行写入失败: {e}")
            logger.error(f"查询: {query}")
            raise
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
