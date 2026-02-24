"""
Java AST Transformer
将 javalang 解析结果转换为统一的数据模型
"""

import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from ...core.models import (
    CodeEntity, CodeRelationship, EntityType, RelationshipType,
    ParseResult
)

logger = logging.getLogger(__name__)


class JavaASTTransformer:
    """将 javalang AST 转换为统一模型"""
    
    def __init__(self, project_name: str, project_path: str):
        """
        初始化转换器
        
        Args:
            project_name: 项目名称
            project_path: 项目路径
        """
        self.project_name = project_name
        self.project_path = project_path
    
    def transform_parse_result(
        self,
        classes: List[Dict],
        methods: List[Dict],
        fields: List[Dict],
        calls: List[Dict],
        imports: List[Dict],
        packages: List[str],
        dubbo_references: List[Dict] = None,
        dubbo_services: List[Dict] = None,
        mq_listeners: List[Dict] = None,
        mq_senders: List[Dict] = None,
        mapper_tables: List[Dict] = None
    ) -> ParseResult:
        """
        转换解析结果为统一模型
        
        Args:
            classes: 类列表
            methods: 方法列表
            fields: 字段列表
            calls: 调用列表
            imports: 导入列表
            packages: 包列表
            dubbo_references: Dubbo引用列表
            dubbo_services: Dubbo服务列表
            mq_listeners: MQ监听列表
            mq_senders: MQ发送列表
            mapper_tables: Mapper表关系列表
        
        Returns:
            ParseResult: 统一的解析结果
        """
        entities: List[CodeEntity] = []
        relationships: List[CodeRelationship] = []
        
        # 转换包（去重）
        package_set = set(packages)
        for package_name in package_set:
            if package_name:
                entities.append(self._create_package_entity(package_name))
        
        # 转换类
        class_map = {}  # fqn -> entity_id
        for cls in classes:
            entity = self._create_type_entity(cls)
            entities.append(entity)
            class_map[cls['fqn']] = entity.id
            
            # 创建包关系
            if cls.get('package'):
                pkg_id = self._package_id(cls['package'])
                relationships.append(CodeRelationship(
                    id=f"{pkg_id}:CONTAINS:{entity.id}",
                    type=RelationshipType.CONTAINS,
                    source_id=pkg_id,
                    target_id=entity.id
                ))
            
            # 创建继承关系
            if cls.get('extends'):
                parent_id = self._type_id(cls['extends'])
                relationships.append(CodeRelationship(
                    id=f"{entity.id}:EXTENDS:{parent_id}",
                    type=RelationshipType.EXTENDS,
                    source_id=entity.id,
                    target_id=parent_id
                ))
            
            # 创建实现关系
            for impl in cls.get('implements', []):
                interface_id = self._type_id(impl)
                relationships.append(CodeRelationship(
                    id=f"{entity.id}:IMPLEMENTS:{interface_id}",
                    type=RelationshipType.IMPLEMENTS,
                    source_id=entity.id,
                    target_id=interface_id
                ))
            
            # 创建注解关系和注解实体
            for ann in cls.get('annotations', []):
                ann_name = ann.get('fqn', ann.get('name', ''))
                ann_id = self._annotation_id(ann_name)
                
                # 创建注解实体
                entities.append(CodeEntity(
                    id=ann_id,
                    type=EntityType.ANNOTATION,
                    name=ann_name.split('.')[-1],
                    qualified_name=ann_name,
                    file_path='',
                    start_line=0,
                    end_line=0,
                    language='java',
                    project=self.project_name,
                    metadata={}
                ))
                
                # 创建注解关系
                relationships.append(CodeRelationship(
                    id=f"{entity.id}:ANNOTATED_BY:{ann_id}",
                    type=RelationshipType.ANNOTATED_BY,
                    source_id=entity.id,
                    target_id=ann_id
                ))
        
        # 转换字段
        field_map = {}  # signature -> entity_id
        for field in fields:
            entity = self._create_field_entity(field)
            entities.append(entity)
            field_signature = f"{field['class_fqn']}.{field['name']}"
            field_map[field_signature] = entity.id
            
            # 创建类-字段关系（使用 DECLARES）
            if field['class_fqn'] in class_map:
                relationships.append(CodeRelationship(
                    id=f"{class_map[field['class_fqn']]}:DECLARES:{entity.id}",
                    type=RelationshipType.DECLARES,
                    source_id=class_map[field['class_fqn']],
                    target_id=entity.id
                ))
            
            # 创建注解关系和注解实体
            for ann in field.get('annotations', []):
                ann_name = ann.get('fqn', ann.get('name', ''))
                ann_id = self._annotation_id(ann_name)
                
                # 创建注解实体（如果不存在）
                if not any(e.id == ann_id for e in entities):
                    entities.append(CodeEntity(
                        id=ann_id,
                        type=EntityType.ANNOTATION,
                        name=ann_name.split('.')[-1],
                        qualified_name=ann_name,
                        file_path='',
                        start_line=0,
                        end_line=0,
                        language='java',
                        project=self.project_name,
                        metadata={}
                    ))
                
                # 创建注解关系
                relationships.append(CodeRelationship(
                    id=f"{entity.id}:ANNOTATED_BY:{ann_id}",
                    type=RelationshipType.ANNOTATED_BY,
                    source_id=entity.id,
                    target_id=ann_id
                ))
        
        # 转换方法
        method_map = {}  # signature -> entity_id
        for method in methods:
            entity = self._create_method_entity(method)
            entities.append(entity)
            signature = method.get('signature', f"{method['class_fqn']}.{method['name']}")
            method_map[signature] = entity.id
            
            # 创建类-方法关系（使用 DECLARES）
            if method.get('class_fqn') in class_map:
                relationships.append(CodeRelationship(
                    id=f"{class_map[method['class_fqn']]}:DECLARES:{entity.id}",
                    type=RelationshipType.DECLARES,
                    source_id=class_map[method['class_fqn']],
                    target_id=entity.id
                ))
            
            # 创建参数关系
            for param in method.get('parameters', []):
                param_entity = self._create_parameter_entity(method, param)
                entities.append(param_entity)
                relationships.append(CodeRelationship(
                    id=f"{entity.id}:HAS_PARAMETER:{param_entity.id}",
                    type=RelationshipType.HAS_PARAMETER,
                    source_id=entity.id,
                    target_id=param_entity.id
                ))
            
            # 创建返回类型关系
            if method.get('return_type') and method['return_type'] != 'void':
                return_type_id = self._type_id(method['return_type'])
                relationships.append(CodeRelationship(
                    id=f"{entity.id}:RETURNS:{return_type_id}",
                    type=RelationshipType.RETURNS,
                    source_id=entity.id,
                    target_id=return_type_id
                ))
            
            # 创建注解关系和注解实体
            for ann in method.get('annotations', []):
                ann_name = ann.get('fqn', ann.get('name', ''))
                ann_id = self._annotation_id(ann_name)
                
                # 创建注解实体（如果不存在）
                if not any(e.id == ann_id for e in entities):
                    entities.append(CodeEntity(
                        id=ann_id,
                        type=EntityType.ANNOTATION,
                        name=ann_name.split('.')[-1],
                        qualified_name=ann_name,
                        file_path='',
                        start_line=0,
                        end_line=0,
                        language='java',
                        project=self.project_name,
                        metadata={}
                    ))
                
                # 创建注解关系
                relationships.append(CodeRelationship(
                    id=f"{entity.id}:ANNOTATED_BY:{ann_id}",
                    type=RelationshipType.ANNOTATED_BY,
                    source_id=entity.id,
                    target_id=ann_id
                ))
        
        # 转换调用关系
        import_map = {}
        for imp in imports:
            if imp.get('path') and not imp.get('wildcard', False):
                imported_class = imp['path'].split('.')[-1]
                import_map[imported_class] = imp['path']
        
        for call in calls:
            if call.get('caller_class') and call.get('callee'):
                caller_id = class_map.get(call['caller_class'])
                if not caller_id:
                    continue
                
                # 尝试匹配被调用的类
                callee_class = None
                if call.get('target'):
                    callee_class = call['target']
                elif call['callee'] in import_map:
                    callee_class = import_map[call['callee']]
                
                if callee_class:
                    callee_id = self._type_id(callee_class)
                    relationships.append(CodeRelationship(
                        id=f"{caller_id}:DEPENDS_ON:{callee_id}",
                        type=RelationshipType.DEPENDS_ON,
                        source_id=caller_id,
                        target_id=callee_id,
                        metadata={'method': call.get('callee')}
                    ))
        
        # 转换导入关系
        for imp in imports:
            if imp.get('path') and not imp.get('wildcard', False):
                imp_path = imp['path']
                # 找到导入的类
                imported_class = imp_path.split('.')[-1]
                if imported_class in import_map:
                    # 找到导入所在的类（从文件路径推断）
                    file_path = imp.get('file_path', '')
                    # 简化处理：为每个导入创建依赖关系
                    # 实际应该找到导入所在的类
                    pass  # TODO: 需要更精确的导入关系
        
        
        # 转换 Dubbo 关系（使用特殊关系类型）
        if dubbo_references:
            for ref in dubbo_references:
                caller_id = class_map.get(ref['class_fqn'])
                if caller_id:
                    service_id = self._type_id(ref['service_interface'])
                    relationships.append(CodeRelationship(
                        id=f"{caller_id}:DUBBO_CALLS:{service_id}",
                        type=RelationshipType.DUBBO_CALLS,
                        source_id=caller_id,
                        target_id=service_id,
                        metadata={'field_name': ref.get('field_name', '')}
                    ))
        
        if dubbo_services:
            for svc in dubbo_services:
                provider_id = class_map.get(svc['class_fqn'])
                if provider_id:
                    service_id = self._type_id(svc['service_interface'])
                    relationships.append(CodeRelationship(
                        id=f"{provider_id}:DUBBO_PROVIDES:{service_id}",
                        type=RelationshipType.DUBBO_PROVIDES,
                        source_id=provider_id,
                        target_id=service_id,
                        metadata={}
                    ))
        
        # 转换 MQ 关系
        if mq_listeners:
            for listener in mq_listeners:
                method_signature = listener.get('method_signature')
                if method_signature in method_map:
                    method_id = method_map[method_signature]
                    topic_name = listener.get('topic')
                    mq_type = listener.get('mq_type', 'KAFKA')
                    topic_id = self._mq_topic_id(topic_name, mq_type)
                    
                    # 创建 MQTopic 实体
                    entities.append(CodeEntity(
                        id=topic_id,
                        type=EntityType.MQ_TOPIC,
                        name=topic_name,
                        qualified_name=f"{mq_type}:{topic_name}",
                        file_path='',
                        start_line=0,
                        end_line=0,
                        language='java',
                        project=self.project_name,
                        metadata={
                            'mq_type': mq_type,
                            'group_id': listener.get('group_id', '')
                        }
                    ))
                    
                    # 创建监听关系
                    relationships.append(CodeRelationship(
                        id=f"{method_id}:LISTENS_TO_MQ:{topic_id}",
                        type=RelationshipType.LISTENS_TO_MQ,
                        source_id=method_id,
                        target_id=topic_id,
                        metadata={}
                    ))
        
        if mq_senders:
            for sender in mq_senders:
                method_signature = sender.get('method_signature')
                if method_signature in method_map:
                    method_id = method_map[method_signature]
                    topic_name = sender.get('topic')
                    mq_type = sender.get('mq_type', 'KAFKA')
                    topic_id = self._mq_topic_id(topic_name, mq_type)
                    
                    # 创建 MQTopic 实体（如果不存在）
                    if not any(e.id == topic_id for e in entities):
                        entities.append(CodeEntity(
                            id=topic_id,
                            type=EntityType.MQ_TOPIC,
                            name=topic_name,
                            qualified_name=f"{mq_type}:{topic_name}",
                            file_path='',
                            start_line=0,
                            end_line=0,
                            language='java',
                            project=self.project_name,
                            metadata={
                                'mq_type': mq_type
                            }
                        ))
                    
                    # 创建发送关系
                    relationships.append(CodeRelationship(
                        id=f"{method_id}:SENDS_TO_MQ:{topic_id}",
                        type=RelationshipType.SENDS_TO_MQ,
                        source_id=method_id,
                        target_id=topic_id,
                        metadata={}
                    ))
        
        # 转换 Mapper 关系
        if mapper_tables:
            for mapper_table in mapper_tables:
                mapper_id = class_map.get(mapper_table['mapper_fqn'])
                if mapper_id:
                    table_name = mapper_table['table_name']
                    table_id = self._table_id(table_name)
                    
                    # 创建 Table 实体
                    entities.append(CodeEntity(
                        id=table_id,
                        type=EntityType.TABLE,
                        name=table_name,
                        qualified_name=table_name,
                        file_path='',
                        start_line=0,
                        end_line=0,
                        language='java',
                        project=self.project_name,
                        metadata={
                            'entity_fqn': mapper_table.get('entity_fqn')
                        }
                    ))
                    
                    # 创建 Mapper 关系
                    relationships.append(CodeRelationship(
                        id=f"{mapper_id}:MAPPER_FOR_TABLE:{table_id}",
                        type=RelationshipType.MAPPER_FOR_TABLE,
                        source_id=mapper_id,
                        target_id=table_id,
                        metadata={}
                    ))
        
        return ParseResult(
            entities=entities,
            relationships=relationships,
            errors=[],
            metadata={
                'packages': len(packages),
                'classes': len(classes),
                'methods': len(methods),
                'fields': len(fields),
                'calls': len(calls),
                'imports': len(imports)
            }
        )
    
    def _create_package_entity(self, package_name: str) -> CodeEntity:
        """创建包实体"""
        return CodeEntity(
            id=self._package_id(package_name),
            type=EntityType.PACKAGE,
            name=package_name.split('.')[-1],
            qualified_name=package_name,
            file_path='',
            start_line=0,
            end_line=0,
            language='java',
            project=self.project_name,
            metadata={'package': package_name}
        )
    
    def _create_type_entity(self, cls: Dict) -> CodeEntity:
        """创建类型实体（类/接口）"""
        return CodeEntity(
            id=self._type_id(cls['fqn']),
            type=EntityType.TYPE,
            name=cls['name'],
            qualified_name=cls['fqn'],
            file_path=cls.get('file_path', ''),
            start_line=0,  # TODO: 从 AST 中提取
            end_line=0,    # TODO: 从 AST 中提取
            language='java',
            project=self.project_name,
            metadata={
                'kind': cls.get('kind', 'CLASS'),
                'visibility': cls.get('visibility', 'PACKAGE'),
                'is_abstract': cls.get('is_abstract', False),
                'is_final': cls.get('is_final', False),
                'is_interface': cls.get('is_interface', False),
                'package': cls.get('package', ''),
                'super_class': cls.get('extends') or '',  # 添加 super_class
                'modifiers': cls.get('modifiers', [])
            }
        )
    
    def _create_field_entity(self, field: Dict) -> CodeEntity:
        """创建字段实体"""
        signature = f"{field['class_fqn']}.{field['name']}"
        return CodeEntity(
            id=self._field_id(signature),
            type=EntityType.FIELD,
            name=field['name'],
            qualified_name=signature,
            file_path=field.get('file_path', ''),
            start_line=0,  # TODO: 从 AST 中提取
            end_line=0,    # TODO: 从 AST 中提取
            language='java',
            project=self.project_name,
            metadata={
                'type': field.get('type', 'Object'),
                'visibility': field.get('visibility', 'PACKAGE'),
                'is_static': field.get('is_static', False),
                'is_final': field.get('is_final', False),
                'class_fqn': field['class_fqn']
            }
        )
    
    def _create_method_entity(self, method: Dict) -> CodeEntity:
        """创建方法实体"""
        signature = method.get('signature', f"{method['class_fqn']}.{method['name']}")
        return CodeEntity(
            id=self._method_id(signature),
            type=EntityType.METHOD,
            name=method['name'],
            qualified_name=signature,
            file_path=method.get('file_path', ''),
            start_line=method.get('line_number', 0),
            end_line=method.get('line_number', 0),  # TODO: 从 AST 中提取结束行
            language='java',
            project=self.project_name,
            metadata={
                'return_type': method.get('return_type', 'void'),
                'visibility': method.get('visibility', 'PACKAGE'),
                'is_static': method.get('is_static', False),
                'is_abstract': method.get('is_abstract', False),
                'parameter_count': method.get('parameter_count', 0),
                'class_fqn': method.get('class_fqn', ''),
                'parameters': method.get('parameters', [])
            }
        )
    
    def _create_parameter_entity(self, method: Dict, param: Dict) -> CodeEntity:
        """创建参数实体"""
        method_signature = method.get('signature', f"{method['class_fqn']}.{method['name']}")
        param_signature = f"{method_signature}.{param['name']}"
        return CodeEntity(
            id=self._parameter_id(param_signature),
            type=EntityType.PARAMETER,
            name=param['name'],
            qualified_name=param_signature,
            file_path=method.get('file_path', ''),
            start_line=0,
            end_line=0,
            language='java',
            project=self.project_name,
            metadata={
                'type': param.get('type', 'Object'),
                'position': param.get('position', 0),
                'method_signature': method_signature
            }
        )
    
    # ID 生成辅助方法
    def _package_id(self, package_name: str) -> str:
        return f"Package:{package_name}"
    
    def _type_id(self, fqn: str) -> str:
        return f"Type:{fqn}"
    
    def _field_id(self, signature: str) -> str:
        return f"Field:{signature}"
    
    def _method_id(self, signature: str) -> str:
        return f"Method:{signature}"
    
    def _parameter_id(self, signature: str) -> str:
        return f"Parameter:{signature}"
    
    def _annotation_id(self, fqn: str) -> str:
        return f"Annotation:{fqn}"
    
    def _mq_topic_id(self, topic_name: str, mq_type: str) -> str:
        return f"MQTopic:{mq_type}:{topic_name}"
    
    def _table_id(self, table_name: str) -> str:
        return f"Table:{table_name}"
