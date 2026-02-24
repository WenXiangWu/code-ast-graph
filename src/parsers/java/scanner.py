"""
Java AST Scanner
使用 javalang 解析 Java 源码，无需 Java 运行时
注意：此类保留用于向后兼容，新代码应使用 JavaParser
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple

try:
    import javalang
except ImportError:
    javalang = None
    logging.warning("javalang module not found. Please install it with: pip install javalang")

from .config import JavaParserConfig
from ...storage.neo4j.storage import Neo4jStorage
from .dependency_tracker import DependencyTracker

logger = logging.getLogger(__name__)


class JavaASTScanner:
    """Python AST 扫描器（纯 Python，无需 Java）"""
    
    def __init__(
        self,
        config: Optional[JavaParserConfig] = None,
        client: Optional[Neo4jStorage] = None
    ):
        """
        初始化扫描器
        
        Args:
            config: Java 解析器配置
            client: Neo4j 存储（可选，主要用于依赖追踪）
        """
        if config is None:
            from .config import get_java_parser_config
            config = get_java_parser_config()
        
        self.config = config
        self.client = client  # 保留以兼容旧代码
        # 注意：dependency_tracker 需要 Neo4j 客户端
        # 如果提供了 client，创建依赖追踪器
        if client:
            self.dependency_tracker = DependencyTracker(client)
        else:
            self.dependency_tracker = None
    
    def scan_project(
        self,
        project_name: str,
        project_path: str,
        force_rescan: bool = False
    ) -> Dict:
        """
        扫描 Java 项目
        
        Args:
            project_name: 项目名称
            project_path: 项目路径
            force_rescan: 是否强制重新扫描
        
        Returns:
            扫描结果字典
        """
        logger.info(f"开始扫描项目（Python AST）: {project_name}")
        
        # 检查项目是否已扫描
        if not force_rescan and self.client and self.client.project_exists(project_name):
            logger.info(f"项目 {project_name} 已存在，跳过扫描")
            return {
                "success": True,
                "message": "项目已存在",
                "skipped": True
            }
        
        # 检查项目路径
        project_dir = Path(project_path)
        if not project_dir.exists():
            logger.error(f"项目路径不存在: {project_path}")
            return {
                "success": False,
                "error": f"项目路径不存在: {project_path}"
            }
        
        try:
            # 扫描 Java 文件
            java_files = self._find_java_files(project_dir)
            logger.info(f"找到 {len(java_files)} 个 Java 文件")
            
            # 解析所有文件
            classes = []
            methods = []
            fields = []
            calls = []
            imports = []
            packages = set()  # 收集所有包名
            
            dubbo_references = []
            dubbo_services = []
            mq_listeners = []
            mq_senders = []
            mapper_tables = []
            
            total_files = len(java_files)
            for idx, java_file in enumerate(java_files, 1):
                try:
                    # 打印进度日志
                    if idx % 10 == 0 or idx == total_files:
                        logger.info(f"正在解析文件 [{idx}/{total_files}]: {java_file.name}")
                    
                    file_result = self._parse_java_file(java_file)
                    (file_classes, file_methods, file_fields, file_calls, file_imports, file_package,
                     file_dubbo_refs, file_dubbo_svcs, file_mq_listeners, file_mq_senders, file_mapper_tables) = file_result
                    classes.extend(file_classes)
                    methods.extend(file_methods)
                    fields.extend(file_fields)
                    calls.extend(file_calls)
                    imports.extend(file_imports)
                    dubbo_references.extend(file_dubbo_refs)
                    dubbo_services.extend(file_dubbo_svcs)
                    mq_listeners.extend(file_mq_listeners)
                    mq_senders.extend(file_mq_senders)
                    mapper_tables.extend(file_mapper_tables)
                    if file_package:
                        packages.add(file_package)
                    
                    if file_classes or file_methods:
                        logger.debug(f"解析成功 {java_file.name}: {len(file_classes)} 类, {len(file_methods)} 方法, {len(file_fields)} 字段")
                except Exception as e:
                    logger.warning(f"解析文件失败 {java_file}: {e}", exc_info=True)
                    continue
            
            logger.info(f"解析完成: {len(classes)} 类, {len(methods)} 方法, {len(fields)} 字段, {len(calls)} 调用, {len(imports)} 导入")
            logger.info(f"特殊关系: {len(dubbo_references)} Dubbo引用, {len(dubbo_services)} Dubbo服务, {len(mq_listeners)} MQ监听, {len(mq_senders)} MQ发送, {len(mapper_tables)} Mapper")
            
            # 存储到 Neo4j（包含创建项目节点）
            self._store_to_neo4j(project_name, str(project_dir), list(packages), classes, methods, fields, calls, imports,
                                dubbo_references, dubbo_services, mq_listeners, mq_senders, mapper_tables)
            
            logger.info(f"✅ Python AST 扫描成功: {project_name}")
            return {
                "success": True,
                "message": "Python AST 扫描成功",
                "method": "python-ast",
                "stats": {
                    "packages": len(packages),
                    "classes": len(classes),
                    "methods": len(methods),
                    "fields": len(fields),
                    "calls": len(calls),
                    "imports": len(imports)
                }
            }
            
        except Exception as e:
            logger.error(f"Python AST 扫描异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _find_java_files(self, project_dir: Path) -> List[Path]:
        """查找所有 Java 文件（根据配置过滤）"""
        java_files = []
        
        # 使用配置中的排除目录
        exclude_dirs = set(self.config.exclude_dirs)
        
        for root, dirs, files in os.walk(project_dir):
            # 过滤排除目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = Path(root) / file
                
                # 使用配置检查是否应该排除
                if not self.config.should_exclude_file(str(file_path)):
                    java_files.append(file_path)
        
        return java_files
    
    def _parse_java_file(self, java_file: Path) -> tuple:
        """
        解析单个 Java 文件
        
        Returns:
            (classes, methods, fields, calls, imports, package_name, 
             dubbo_references, dubbo_services, mq_listeners, mq_senders, mapper_tables)
        """
        if javalang is None:
            raise ImportError("javalang module is not installed. Please install it with: pip install javalang")
        
        with open(java_file, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()
        
        try:
            tree = javalang.parse.parse(source_code)
        except javalang.parser.JavaSyntaxError as e:
            logger.warning(f"Java 语法错误 {java_file}: {e}")
            return [], [], [], [], [], None, [], [], [], [], []
        
        classes = []
        methods = []
        fields = []
        calls = []
        imports = []
        dubbo_references = []  # Dubbo引用列表: [{'class_fqn': str, 'field_name': str, 'service_interface': str}]
        dubbo_services = []    # Dubbo服务列表: [{'class_fqn': str, 'service_interface': str}]
        mq_listeners = []      # MQ监听列表: [{'class_fqn': str, 'method_signature': str, 'topic': str, 'group_id': str, 'mq_type': str}]
        mq_senders = []        # MQ发送列表: [{'class_fqn': str, 'method_signature': str, 'topic': str, 'mq_type': str}]
        mapper_tables = []     # Mapper和表的关系列表: [{'mapper_fqn': str, 'table_name': str, 'entity_fqn': str}]
        
        # 获取包名
        package_name = None
        if tree.package:
            # javalang 的 package.name 可能是列表或字符串
            if isinstance(tree.package.name, list):
                package_name = '.'.join(str(n) for n in tree.package.name)
            else:
                package_name = str(tree.package.name)
        
        # 获取导入
        if tree.imports:
            for imp in tree.imports:
                import_info = {
                    'path': '.'.join(imp.path),
                    'static': imp.static if hasattr(imp, 'static') else False,
                    'wildcard': imp.wildcard if hasattr(imp, 'wildcard') else False,
                    'file_path': str(java_file)
                }
                imports.append(import_info)
        
        # 提取类型声明（类、接口等）
        if tree.types:
            logger.debug(f"找到 {len(tree.types)} 个类型声明")
            for type_decl in tree.types:
                logger.debug(f"类型: {type(type_decl).__name__}, 名称: {getattr(type_decl, 'name', 'N/A')}")
                # 处理接口
                if isinstance(type_decl, javalang.tree.InterfaceDeclaration):
                    extends_list = []
                    if hasattr(type_decl, 'extends') and type_decl.extends:
                        for ext in type_decl.extends:
                            if hasattr(ext, 'name'):
                                if isinstance(ext.name, list):
                                    extends_list.append('.'.join(ext.name))
                                else:
                                    extends_list.append(str(ext.name))
                    
                    # 提取接口注解
                    interface_annotations = []
                    should_exclude_interface = False
                    if hasattr(type_decl, 'annotations') and type_decl.annotations:
                        for ann in type_decl.annotations:
                            ann_name = '.'.join(ann.name) if isinstance(ann.name, list) else str(ann.name)
                            
                            # 检查是否应该排除此注解
                            if self.config.should_exclude_annotation(ann_name):
                                should_exclude_interface = True
                                logger.debug(f"接口 {type_decl.name} 有排除的注解 {ann_name}，跳过")
                                break
                            
                            interface_annotations.append({
                                'name': ann_name,
                                'fqn': ann_name
                            })
                    
                    # 如果接口有排除的注解，跳过此接口
                    if should_exclude_interface:
                        continue
                    
                    interface_info = {
                        'name': type_decl.name,
                        'package': package_name,
                        'fqn': f"{package_name}.{type_decl.name}" if package_name else type_decl.name,
                        'modifiers': [str(m) for m in type_decl.modifiers] if type_decl.modifiers else [],
                        'extends': extends_list[0] if extends_list else None,
                        'implements': extends_list,  # 接口的extends就是实现的接口
                        'annotations': interface_annotations,
                        'is_abstract': True,  # 接口默认抽象
                        'is_final': False,
                        'is_interface': True,
                        'kind': 'INTERFACE',
                        'visibility': self._extract_visibility(type_decl.modifiers or []),
                        'file_path': str(java_file)
                    }
                    classes.append(interface_info)
                    current_class = interface_info['fqn']
                    
                    # 提取接口中的方法（接口方法声明）
                    if hasattr(type_decl, 'body') and type_decl.body:
                        for body_decl in type_decl.body:
                            # 接口方法声明（InterfaceMethodDeclaration）或常量字段（FieldDeclaration）
                            if isinstance(body_decl, javalang.tree.MethodDeclaration) or \
                               (hasattr(javalang.tree, 'InterfaceMethodDeclaration') and 
                                isinstance(body_decl, javalang.tree.InterfaceMethodDeclaration)):
                                return_type_str = 'void'
                                if body_decl.return_type:
                                    if isinstance(body_decl.return_type, javalang.tree.BasicType):
                                        return_type_str = body_decl.return_type.name
                                    elif hasattr(body_decl.return_type, 'name'):
                                        if isinstance(body_decl.return_type.name, list):
                                            return_type_str = '.'.join(body_decl.return_type.name)
                                        else:
                                            return_type_str = str(body_decl.return_type.name)
                                
                                # 提取方法注解
                                method_annotations = []
                                should_exclude_method = False
                                if hasattr(body_decl, 'annotations') and body_decl.annotations:
                                    for ann in body_decl.annotations:
                                        ann_name = '.'.join(ann.name) if isinstance(ann.name, list) else str(ann.name)
                                        
                                        # 检查是否应该排除此注解
                                        if self.config.should_exclude_annotation(ann_name):
                                            should_exclude_method = True
                                            logger.debug(f"方法 {body_decl.name} 有排除的注解 {ann_name}，跳过")
                                            break
                                        
                                        method_annotations.append({
                                            'name': ann_name,
                                            'fqn': ann_name
                                        })
                                
                                # 如果方法有排除的注解，跳过此方法
                                if should_exclude_method:
                                    continue
                                
                                parameters = []
                                if body_decl.parameters:
                                    for i, param in enumerate(body_decl.parameters):
                                        param_type_str = 'Object'
                                        if param.type:
                                            if isinstance(param.type, javalang.tree.BasicType):
                                                param_type_str = param.type.name
                                            elif hasattr(param.type, 'name'):
                                                if isinstance(param.type.name, list):
                                                    param_type_str = '.'.join(param.type.name)
                                                else:
                                                    param_type_str = str(param.type.name)
                                        
                                        parameters.append({
                                            'type': param_type_str,
                                            'name': param.name,
                                            'position': i
                                        })
                                
                                modifiers = [str(m) for m in body_decl.modifiers] if body_decl.modifiers else []
                                param_types = [p['type'] for p in parameters]
                                signature = f"{current_class}.{body_decl.name}({', '.join(param_types)})"
                                
                                method_info = {
                                    'name': body_decl.name,
                                    'class_fqn': current_class,
                                    'signature': signature,
                                    'return_type': return_type_str,
                                    'parameters': parameters,
                                    'modifiers': modifiers,
                                    'annotations': method_annotations,
                                    'visibility': self._extract_visibility(modifiers),
                                    'is_static': 'static' in modifiers,
                                    'is_abstract': True,  # 接口方法默认抽象
                                    'parameter_count': len(parameters),
                                    'line_number': body_decl.position.line if hasattr(body_decl, 'position') and body_decl.position else 0,
                                    'file_path': str(java_file)
                                }
                                methods.append(method_info)
                            
                            # 接口常量字段（FieldDeclaration）
                            elif isinstance(body_decl, javalang.tree.FieldDeclaration):
                                field_annotations = []
                                should_exclude_field = False
                                if hasattr(body_decl, 'annotations') and body_decl.annotations:
                                    for ann in body_decl.annotations:
                                        ann_name = '.'.join(ann.name) if isinstance(ann.name, list) else str(ann.name)
                                        
                                        # 检查是否应该排除此注解
                                        if self.config.should_exclude_annotation(ann_name):
                                            should_exclude_field = True
                                            logger.debug(f"接口字段有排除的注解 {ann_name}，跳过")
                                            break
                                        
                                        field_annotations.append({
                                            'name': ann_name,
                                            'fqn': ann_name
                                        })
                                
                                # 如果字段有排除的注解，跳过此字段
                                if should_exclude_field:
                                    continue
                                
                                field_type_str = 'Object'
                                if body_decl.type:
                                    if isinstance(body_decl.type, javalang.tree.BasicType):
                                        field_type_str = body_decl.type.name
                                    elif hasattr(body_decl.type, 'name'):
                                        if isinstance(body_decl.type.name, list):
                                            field_type_str = '.'.join(body_decl.type.name)
                                        else:
                                            field_type_str = str(body_decl.type.name)
                                
                                modifiers = [str(m) for m in body_decl.modifiers] if body_decl.modifiers else []
                                
                                if body_decl.declarators:
                                    for declarator in body_decl.declarators:
                                        field_info = {
                                            'name': declarator.name,
                                            'class_fqn': current_class,
                                            'type': field_type_str,
                                            'modifiers': modifiers,
                                            'annotations': field_annotations,
                                            'visibility': self._extract_visibility(modifiers),
                                            'is_static': True,  # 接口字段默认static final
                                            'is_final': True,
                                            'file_path': str(java_file)
                                        }
                                        fields.append(field_info)
                
                # 处理类
                elif isinstance(type_decl, javalang.tree.ClassDeclaration):
                    extends_name = None
                    if hasattr(type_decl, 'extends') and type_decl.extends:
                        if isinstance(type_decl.extends, javalang.tree.ClassReference):
                            extends_name = '.'.join(type_decl.extends.name) if isinstance(type_decl.extends.name, list) else str(type_decl.extends.name)
                        elif hasattr(type_decl.extends, 'name'):
                            if isinstance(type_decl.extends.name, list):
                                extends_name = '.'.join(type_decl.extends.name)
                            else:
                                extends_name = str(type_decl.extends.name)
                    
                    implements_list = []
                    if hasattr(type_decl, 'implements') and type_decl.implements:
                        for impl in type_decl.implements:
                            if hasattr(impl, 'name'):
                                if isinstance(impl.name, list):
                                    implements_list.append('.'.join(impl.name))
                                else:
                                    implements_list.append(str(impl.name))
                    
                    # 提取类注解
                    class_annotations = []
                    should_exclude_class = False
                    if hasattr(type_decl, 'annotations') and type_decl.annotations:
                        for ann in type_decl.annotations:
                            ann_name = '.'.join(ann.name) if isinstance(ann.name, list) else str(ann.name)
                            
                            # 检查是否应该排除此注解
                            if self.config.should_exclude_annotation(ann_name):
                                should_exclude_class = True
                                logger.debug(f"类 {type_decl.name} 有排除的注解 {ann_name}，跳过")
                                break
                            
                            class_annotations.append({
                                'name': ann_name,
                                'fqn': ann_name  # javalang 不提供完整限定名，使用名称
                            })
                    
                    # 如果类有排除的注解，跳过此类
                    if should_exclude_class:
                        continue
                    
                    class_info = {
                        'name': type_decl.name,
                        'package': package_name,
                        'fqn': f"{package_name}.{type_decl.name}" if package_name else type_decl.name,
                        'modifiers': [str(m) for m in type_decl.modifiers] if type_decl.modifiers else [],
                        'extends': extends_name,
                        'implements': implements_list,
                        'annotations': class_annotations,
                        'is_abstract': 'abstract' in [str(m) for m in (type_decl.modifiers or [])],
                        'is_final': 'final' in [str(m) for m in (type_decl.modifiers or [])],
                        'is_interface': False,  # ClassDeclaration 不是接口
                        'kind': 'CLASS',
                        'visibility': self._extract_visibility(type_decl.modifiers or []),
                        'file_path': str(java_file)
                    }
                    classes.append(class_info)
                    current_class = class_info['fqn']
                    
                    # 检查是否是 @DubboService 或 @Service 注解的类
                    for ann in class_annotations:
                        ann_name = ann.get('name', '')
                        ann_fqn = ann.get('fqn', ann_name)
                        # 支持 @DubboService 和 @Service (com.alibaba.dubbo.config.annotation.Service)
                        is_dubbo_service = (
                            'DubboService' in ann_name or 
                            (ann_name.endswith('.Service') and 'dubbo' in ann_fqn.lower()) or
                            (ann_name == 'Service' and 'dubbo' in ann_fqn.lower())
                        )
                        
                        if is_dubbo_service:
                            # 查找实现的接口
                            if implements_list:
                                for impl_interface in implements_list:
                                    service_interface = self._resolve_type_fqn(impl_interface, imports, package_name)
                                    if service_interface:
                                        dubbo_services.append({
                                            'class_fqn': current_class,
                                            'service_interface': service_interface
                                        })
                                        logger.debug(f"发现Dubbo服务: {current_class} -> {service_interface} (注解: {ann_name})")
                    
                    # 检查是否是Mapper接口
                    is_mapper = False
                    
                    # 方法1: 检查是否有@Mapper注解
                    for ann in class_annotations:
                        ann_name = ann.get('name', '')
                        if 'Mapper' == ann_name or ann_name.endswith('.Mapper'):
                            is_mapper = True
                            break
                    
                    # 方法2: 如果是接口，且满足以下条件之一，也认为是Mapper：
                    # - 接口名以Mapper结尾
                    # - 包名包含mapper
                    if isinstance(type_decl, javalang.tree.InterfaceDeclaration):
                        if current_class.endswith('Mapper'):
                            is_mapper = True
                        elif package_name and 'mapper' in package_name.lower():
                            # 包名包含mapper，且接口名符合Mapper命名规范
                            # 检查方法参数中是否有实体类（domain.db或entity包下的类）
                            if hasattr(type_decl, 'body') and type_decl.body:
                                for body_decl in type_decl.body:
                                    if isinstance(body_decl, javalang.tree.MethodDeclaration):
                                        if body_decl.parameters:
                                            for param in body_decl.parameters:
                                                if param.type:
                                                    param_type_str = 'Object'
                                                    if isinstance(param.type, javalang.tree.BasicType):
                                                        param_type_str = param.type.name
                                                    elif hasattr(param.type, 'name'):
                                                        if isinstance(param.type.name, list):
                                                            param_type_str = '.'.join(param.type.name)
                                                        else:
                                                            param_type_str = str(param.type.name)
                                                    
                                                    # 检查是否是实体类（domain.db或entity包）
                                                    param_fqn = self._resolve_type_fqn(param_type_str, imports, package_name)
                                                    if param_fqn and ('domain.db' in param_fqn.lower() or 'entity' in param_fqn.lower()):
                                                        is_mapper = True
                                                        break
                                            if is_mapper:
                                                break
                    
                    if is_mapper:
                        # 尝试从接口名推断表名（Mapper接口通常以Mapper结尾）
                        table_name = self._infer_table_name_from_mapper(current_class, source_code, imports, package_name)
                        if table_name:
                            mapper_tables.append({
                                'mapper_fqn': current_class,
                                'table_name': table_name,
                                'entity_fqn': None  # 可以后续完善
                            })
                            logger.debug(f"发现Mapper: {current_class} -> 表 {table_name}")
                    
                    # 提取类中的字段和方法
                    if hasattr(type_decl, 'body') and type_decl.body:
                        for body_decl in type_decl.body:
                            # 提取字段
                            if isinstance(body_decl, javalang.tree.FieldDeclaration):
                                field_annotations = []
                                should_exclude_field = False
                                if hasattr(body_decl, 'annotations') and body_decl.annotations:
                                    for ann in body_decl.annotations:
                                        ann_name = '.'.join(ann.name) if isinstance(ann.name, list) else str(ann.name)
                                        
                                        # 检查是否应该排除此注解
                                        if self.config.should_exclude_annotation(ann_name):
                                            should_exclude_field = True
                                            logger.debug(f"字段有排除的注解 {ann_name}，跳过")
                                            break
                                        
                                        field_annotations.append({
                                            'name': ann_name,
                                            'fqn': ann_name
                                        })
                                
                                # 如果字段有排除的注解，跳过此字段
                                if should_exclude_field:
                                    continue
                                
                                field_type_str = 'Object'
                                if body_decl.type:
                                    if isinstance(body_decl.type, javalang.tree.BasicType):
                                        field_type_str = body_decl.type.name
                                    elif hasattr(body_decl.type, 'name'):
                                        if isinstance(body_decl.type.name, list):
                                            field_type_str = '.'.join(body_decl.type.name)
                                        else:
                                            field_type_str = str(body_decl.type.name)
                                
                                modifiers = [str(m) for m in body_decl.modifiers] if body_decl.modifiers else []
                                
                                # 一个 FieldDeclaration 可能包含多个变量
                                if body_decl.declarators:
                                    for declarator in body_decl.declarators:
                                        field_info = {
                                            'name': declarator.name,
                                            'class_fqn': current_class,
                                            'type': field_type_str,
                                            'modifiers': modifiers,
                                            'annotations': field_annotations,
                                            'visibility': self._extract_visibility(modifiers),
                                            'is_static': 'static' in modifiers,
                                            'is_final': 'final' in modifiers,
                                            'file_path': str(java_file)
                                        }
                                        fields.append(field_info)
                                        
                                        # 检查是否是 @DubboReference 或 @Reference 注解的字段
                                        for ann in field_annotations:
                                            ann_name = ann.get('name', '')
                                            # 支持 @DubboReference 和 @Reference (com.alibaba.dubbo.config.annotation.Reference)
                                            if 'DubboReference' in ann_name or (ann_name.endswith('.Reference') and 'dubbo' in ann_name.lower()):
                                                # 字段类型就是服务接口
                                                service_interface = self._resolve_type_fqn(field_type_str, imports, package_name)
                                                if not service_interface:
                                                    # 如果无法解析，使用原始类型名
                                                    service_interface = field_type_str
                                                dubbo_references.append({
                                                    'class_fqn': current_class,
                                                    'field_name': declarator.name,
                                                    'service_interface': service_interface
                                                })
                                                logger.debug(f"发现Dubbo引用: {current_class}.{declarator.name} -> {service_interface} (注解: {ann_name})")
                                            # 也支持简单的 @Reference (可能是 dubbo 的 Reference)
                                            elif ann_name == 'Reference' or ann_name.endswith('.Reference'):
                                                # 检查是否是dubbo的Reference（通过包名判断）
                                                ann_fqn = ann.get('fqn', ann_name)
                                                if 'dubbo' in ann_fqn.lower() or 'dubbo' in ann_name.lower():
                                                    service_interface = self._resolve_type_fqn(field_type_str, imports, package_name)
                                                    if not service_interface:
                                                        service_interface = field_type_str
                                                    dubbo_references.append({
                                                        'class_fqn': current_class,
                                                        'field_name': declarator.name,
                                                        'service_interface': service_interface
                                                    })
                                                    logger.debug(f"发现Dubbo引用: {current_class}.{declarator.name} -> {service_interface} (注解: {ann_name})")
                            
                            # 提取方法
                            elif isinstance(body_decl, javalang.tree.MethodDeclaration):
                                return_type_str = 'void'
                                if body_decl.return_type:
                                    if isinstance(body_decl.return_type, javalang.tree.BasicType):
                                        return_type_str = body_decl.return_type.name
                                    elif hasattr(body_decl.return_type, 'name'):
                                        if isinstance(body_decl.return_type.name, list):
                                            return_type_str = '.'.join(body_decl.return_type.name)
                                        else:
                                            return_type_str = str(body_decl.return_type.name)
                                
                                # 提取方法注解
                                method_annotations = []
                                should_exclude_method = False
                                if hasattr(body_decl, 'annotations') and body_decl.annotations:
                                    for ann in body_decl.annotations:
                                        ann_name = '.'.join(ann.name) if isinstance(ann.name, list) else str(ann.name)
                                        
                                        # 检查是否应该排除此注解
                                        if self.config.should_exclude_annotation(ann_name):
                                            should_exclude_method = True
                                            logger.debug(f"方法 {body_decl.name} 有排除的注解 {ann_name}，跳过")
                                            break
                                        
                                        method_annotations.append({
                                            'name': ann_name,
                                            'fqn': ann_name
                                        })
                                
                                # 如果方法有排除的注解，跳过此方法
                                if should_exclude_method:
                                    continue
                                
                                parameters = []
                                if body_decl.parameters:
                                    for i, param in enumerate(body_decl.parameters):
                                        param_type_str = 'Object'
                                        if param.type:
                                            if isinstance(param.type, javalang.tree.BasicType):
                                                param_type_str = param.type.name
                                            elif hasattr(param.type, 'name'):
                                                if isinstance(param.type.name, list):
                                                    param_type_str = '.'.join(param.type.name)
                                                else:
                                                    param_type_str = str(param.type.name)
                                        
                                        parameters.append({
                                            'type': param_type_str,
                                            'name': param.name,
                                            'position': i
                                        })
                                
                                modifiers = [str(m) for m in body_decl.modifiers] if body_decl.modifiers else []
                                param_types = [p['type'] for p in parameters]
                                signature = f"{current_class}.{body_decl.name}({', '.join(param_types)})"
                                
                                method_info = {
                                    'name': body_decl.name,
                                    'class_fqn': current_class,
                                    'signature': signature,
                                    'return_type': return_type_str,
                                    'parameters': parameters,
                                    'modifiers': modifiers,
                                    'annotations': method_annotations,
                                    'visibility': self._extract_visibility(modifiers),
                                    'is_static': 'static' in modifiers,
                                    'is_abstract': 'abstract' in modifiers,
                                    'parameter_count': len(parameters),
                                    'line_number': body_decl.position.line if hasattr(body_decl, 'position') and body_decl.position else 0,
                                    'file_path': str(java_file)
                                }
                                methods.append(method_info)
                                
                                # 检查是否是MQ监听方法（@KafkaListener, @RabbitListener, @RocketMQMessageListener）
                                for ann in method_annotations:
                                    ann_name = ann.get('name', '')
                                    mq_info = None
                                    
                                    if 'KafkaListener' in ann_name:
                                        # 提取topic和groupId
                                        # 需要从注解对象中提取，但javalang可能不完整，所以主要从源代码提取
                                        topic, group_id = self._extract_kafka_listener_info(body_decl, ann, source_code)
                                        if topic:
                                            mq_info = {
                                                'class_fqn': current_class,
                                                'method_signature': signature,
                                                'topic': topic,
                                                'group_id': group_id or '',
                                                'mq_type': 'KAFKA'
                                            }
                                            mq_listeners.append(mq_info)
                                            logger.debug(f"发现Kafka监听: {current_class}.{body_decl.name} -> topic: {topic}")
                                    
                                    elif 'RabbitListener' in ann_name:
                                        # 提取queue和exchange
                                        topic, group_id = self._extract_rabbit_listener_info(body_decl, ann, source_code)
                                        if topic:
                                            mq_info = {
                                                'class_fqn': current_class,
                                                'method_signature': signature,
                                                'topic': topic,
                                                'group_id': group_id or '',
                                                'mq_type': 'RABBITMQ'
                                            }
                                            mq_listeners.append(mq_info)
                                            logger.debug(f"发现RabbitMQ监听: {current_class}.{body_decl.name} -> queue: {topic}")
                                    
                                    elif 'RocketMQMessageListener' in ann_name:
                                        # 提取topic和consumerGroup
                                        topic, group_id = self._extract_rocketmq_listener_info(body_decl, ann, source_code)
                                        if topic:
                                            mq_info = {
                                                'class_fqn': current_class,
                                                'method_signature': signature,
                                                'topic': topic,
                                                'group_id': group_id or '',
                                                'mq_type': 'ROCKETMQ'
                                            }
                                            mq_listeners.append(mq_info)
                                            logger.debug(f"发现RocketMQ监听: {current_class}.{body_decl.name} -> topic: {topic}")
                                
                                # 提取方法中的调用（包括MQ发送）
                                if hasattr(body_decl, 'body') and body_decl.body:
                                    if isinstance(body_decl.body, list):
                                        for stmt in body_decl.body:
                                            self._extract_method_calls(stmt, current_class, calls, java_file)
                                            self._extract_mq_sends(stmt, current_class, signature, mq_senders, java_file, source_code)
                                    else:
                                        self._extract_method_calls(body_decl.body, current_class, calls, java_file)
                                        self._extract_mq_sends(body_decl.body, current_class, signature, mq_senders, java_file, source_code)
        
        return (classes, methods, fields, calls, imports, package_name,
                dubbo_references, dubbo_services, mq_listeners, mq_senders, mapper_tables)
    
    def _extract_visibility(self, modifiers: List[str]) -> str:
        """提取可见性"""
        modifier_strs = [str(m) for m in modifiers]
        if "public" in modifier_strs:
            return "PUBLIC"
        elif "protected" in modifier_strs:
            return "PROTECTED"
        elif "private" in modifier_strs:
            return "PRIVATE"
        else:
            return "PACKAGE"
    
    def _extract_method_calls(self, node, current_class, calls, java_file):
        """递归提取方法调用"""
        if isinstance(node, javalang.tree.MethodInvocation):
            qualifier_str = None
            if node.qualifier:
                if isinstance(node.qualifier, list):
                    qualifier_str = '.'.join(node.qualifier)
                else:
                    qualifier_str = str(node.qualifier)
            
            call_info = {
                'caller_class': current_class,
                'callee': node.member if node.member else None,
                'target': qualifier_str,
                'file_path': str(java_file)
            }
            calls.append(call_info)
        
        # 递归处理子节点
        if hasattr(node, '__dict__'):
            for attr_name, attr_value in node.__dict__.items():
                if attr_name.startswith('_'):
                    continue
                
                if isinstance(attr_value, list):
                    for item in attr_value:
                        if isinstance(item, javalang.tree.Node):
                            self._extract_method_calls(item, current_class, calls, java_file)
                elif isinstance(attr_value, javalang.tree.Node):
                    self._extract_method_calls(attr_value, current_class, calls, java_file)
    
    def _store_to_neo4j(
        self,
        project_name: str,
        project_path: str,
        packages: List[str],
        classes: List[Dict],
        methods: List[Dict],
        fields: List[Dict],
        calls: List[Dict],
        imports: List[Dict],
        dubbo_references: List[Dict] = None,
        dubbo_services: List[Dict] = None,
        mq_listeners: List[Dict] = None,
        mq_senders: List[Dict] = None,
        mapper_tables: List[Dict] = None
    ):
        """存储到 Neo4j（按照技术方案的数据模型）"""
        
        logger.info("开始存储到Neo4j...")
        
        # 先创建项目节点
        logger.info("创建项目节点...")
        self._create_project_node(project_name, project_path)
        
        # 创建包节点
        logger.info(f"创建包节点 ({len(packages)} 个)...")
        for package_name in packages:
            if package_name:
                self._create_package_node(project_name, package_name)
        
        # 创建类节点（Type 节点）- 按照技术方案的数据模型
        # 使用类级别去重：如果类已存在且已扫描，跳过
        logger.info(f"创建类型节点 ({len(classes)} 个)...")
        created_classes = 0
        skipped_classes = 0
        for idx, cls in enumerate(classes, 1):
            if idx % 50 == 0:
                logger.info(f"  处理类型节点 [{idx}/{len(classes)}]...")
            class_fqn = cls['fqn']
            
            # 检查类是否已扫描（去重）
            if self.dependency_tracker and self.dependency_tracker.check_class_scanned(class_fqn):
                skipped_classes += 1
                logger.debug(f"类已扫描，跳过: {class_fqn}")
                continue
            
            created_classes += 1
            
            # 注意：此方法需要 Neo4jClient，新架构应使用 Neo4jStorage
            # 这里保留以兼容旧代码
            if self.client:
                self.client.execute_write("""
                MATCH (p:Project {name: $project_name})
                MERGE (t:Type {fqn: $fqn})
                SET t.name = $name,
                    t.kind = $kind,
                    t.visibility = $visibility,
                    t.is_abstract = $is_abstract,
                    t.is_final = $is_final,
                    t.super_class = $super_class,
                    t.file_path = $file_path,
                    t.scanned_at = datetime()
                MERGE (p)-[:CONTAINS]->(t)
                
                WITH t
                WHERE $package_name <> ''
                MATCH (pkg:Package {fqn: $package_name})
                MERGE (pkg)-[:CONTAINS]->(t)
            """, {
                "project_name": project_name,
                "fqn": class_fqn,
                "name": cls['name'],
                "kind": cls.get('kind', 'CLASS'),
                "visibility": cls.get('visibility', 'PACKAGE'),
                "is_abstract": cls.get('is_abstract', False),
                "is_final": cls.get('is_final', False),
                "super_class": cls.get('extends') or '',
                "package_name": cls.get('package') or '',
                "file_path": cls.get('file_path', '')
            })
            
            # 标记类为已扫描
            if self.dependency_tracker:
                self.dependency_tracker.mark_class_scanned(class_fqn)
            
            # 如果是接口，查找实现类并添加到待扫描列表
            if self.dependency_tracker and (cls.get('kind') == 'INTERFACE' or cls.get('is_interface', False)):
                self._track_interface_implementations(class_fqn, project_path)
            
            # 创建类注解关系
            if self.client:
                for annotation in cls.get('annotations', []):
                    self._create_annotation_relationship(cls['fqn'], annotation, 'Type')
            
            # 创建继承关系
            if cls.get('extends') and self.client:
                self.client.execute_write("""
                    MATCH (child:Type {fqn: $child_fqn})
                    MERGE (parent:Type {fqn: $parent_fqn})
                    SET parent.name = $parent_name
                    MERGE (child)-[:EXTENDS]->(parent)
                """, {
                    "child_fqn": cls['fqn'],
                    "parent_fqn": cls['extends'],
                    "parent_name": cls['extends'].split('.')[-1]
                })
            
            # 创建实现关系
            if self.client:
                for impl in cls.get('implements', []):
                    self.client.execute_write("""
                    MATCH (impl:Type {fqn: $impl_fqn})
                    MERGE (iface:Type {fqn: $interface_fqn})
                    SET iface.name = $interface_name
                    MERGE (impl)-[:IMPLEMENTS]->(iface)
                """, {
                    "impl_fqn": cls['fqn'],
                    "interface_fqn": impl,
                    "interface_name": impl.split('.')[-1]
                })
        
        logger.info(f"  类型节点创建完成: 新建 {created_classes} 个, 跳过 {skipped_classes} 个")
        
        # 创建字段节点
        logger.info(f"创建字段节点 ({len(fields)} 个)...")
        for field in fields:
            field_signature = f"{field['class_fqn']}.{field['name']}"
            self.client.execute_write("""
                MATCH (t:Type {fqn: $class_fqn})
                MERGE (f:Field {signature: $signature})
                SET f.name = $name,
                    f.type = $type,
                    f.visibility = $visibility,
                    f.is_static = $is_static,
                    f.is_final = $is_final
                MERGE (t)-[:DECLARES]->(f)
            """, {
                "class_fqn": field['class_fqn'],
                "signature": field_signature,
                "name": field['name'],
                "type": field['type'],
                "visibility": field.get('visibility', 'PACKAGE'),
                "is_static": field.get('is_static', False),
                "is_final": field.get('is_final', False)
            })
            
            # 创建字段注解关系
            for annotation in field.get('annotations', []):
                self._create_annotation_relationship(field_signature, annotation, 'Field')
        
        # 创建方法节点和关系 - 按照技术方案的数据模型
        logger.info(f"创建方法节点 ({len(methods)} 个)...")
        for idx, method in enumerate(methods, 1):
            if idx % 100 == 0:
                logger.info(f"  处理方法节点 [{idx}/{len(methods)}]...")
            if not method.get('class_fqn'):
                continue
            
            signature = method.get('signature', f"{method['class_fqn']}.{method['name']}")
            
            self.client.execute_write("""
                MATCH (t:Type {fqn: $class_fqn})
                MERGE (m:Method {signature: $signature})
                SET m.name = $name,
                    m.return_type = $return_type,
                    m.visibility = $visibility,
                    m.is_static = $is_static,
                    m.is_abstract = $is_abstract,
                    m.parameter_count = $parameter_count,
                    m.line_number = $line_number
                MERGE (t)-[:DECLARES]->(m)
            """, {
                "class_fqn": method['class_fqn'],
                "signature": signature,
                "name": method['name'],
                "return_type": method['return_type'],
                "visibility": method.get('visibility', 'PACKAGE'),
                "is_static": method.get('is_static', False),
                "is_abstract": method.get('is_abstract', False),
                "parameter_count": method.get('parameter_count', 0),
                "line_number": method.get('line_number', 0)
            })
            
            # 创建参数节点
            for param in method.get('parameters', []):
                param_signature = f"{signature}.{param['name']}"
                self.client.execute_write("""
                    MATCH (m:Method {signature: $method_signature})
                    MERGE (p:Parameter {signature: $param_signature})
                    SET p.name = $name,
                        p.type = $type,
                        p.position = $position
                    MERGE (m)-[:HAS_PARAMETER]->(p)
                """, {
                    "method_signature": signature,
                    "param_signature": param_signature,
                    "name": param['name'],
                    "type": param['type'],
                    "position": param.get('position', 0)
                })
            
            # 创建方法注解关系
            for annotation in method.get('annotations', []):
                self._create_annotation_relationship(signature, annotation, 'Method')
        
        # 创建类之间的依赖关系（基于导入和调用）
        logger.info(f"创建依赖关系 ({len(calls)} 个调用)...")
        import_map = {}
        for imp in imports:
            if imp['path'] and not imp['wildcard']:
                imported_class = imp['path'].split('.')[-1]
                import_map[imported_class] = imp['path']
        
        # 创建调用关系
        for call in calls:
            if call.get('caller_class') and call.get('callee'):
                # 尝试匹配被调用的类
                callee_class = None
                if call.get('target'):
                    # 有明确的目标类
                    callee_class = call['target']
                elif call['callee'] in import_map:
                    # 从导入中查找
                    callee_class = import_map[call['callee']]
                
                if callee_class:
                    self.client.execute_write("""
                        MATCH (caller:Type {fqn: $caller_class})
                        MERGE (callee:Type {fqn: $callee_class})
                        SET callee.name = $callee_name
                        MERGE (caller)-[:DEPENDS_ON]->(callee)
                    """, {
                        "caller_class": call['caller_class'],
                        "callee_class": callee_class,
                        "callee_name": callee_class.split('.')[-1]
                    })
        
        # 存储Dubbo引用关系
        logger.info(f"创建Dubbo引用关系 ({len(dubbo_references) if dubbo_references else 0} 个)...")
        if dubbo_references:
            for ref in dubbo_references:
                self.client.execute_write("""
                    MATCH (caller:Type {fqn: $caller_class})
                    MERGE (service:Type {fqn: $service_interface})
                    SET service.name = $service_name
                    MERGE (caller)-[:DUBBO_CALLS {field_name: $field_name}]->(service)
                """, {
                    "caller_class": ref['class_fqn'],
                    "service_interface": ref['service_interface'],
                    "service_name": ref['service_interface'].split('.')[-1],
                    "field_name": ref['field_name']
                })
        
        # 存储Dubbo服务关系
        logger.info(f"创建Dubbo服务关系 ({len(dubbo_services) if dubbo_services else 0} 个)...")
        if dubbo_services:
            for svc in dubbo_services:
                self.client.execute_write("""
                    MATCH (provider:Type {fqn: $provider_class})
                    MERGE (service:Type {fqn: $service_interface})
                    SET service.name = $service_name
                    MERGE (provider)-[:DUBBO_PROVIDES]->(service)
                """, {
                    "provider_class": svc['class_fqn'],
                    "service_interface": svc['service_interface'],
                    "service_name": svc['service_interface'].split('.')[-1]
                })
        
        # 存储MQ监听关系
        logger.info(f"创建MQ监听关系 ({len(mq_listeners) if mq_listeners else 0} 个)...")
        if mq_listeners:
            for listener in mq_listeners:
                self.client.execute_write("""
                    MATCH (m:Method {signature: $method_signature})
                    MERGE (topic:MQTopic {name: $topic, mq_type: $mq_type})
                    SET topic.group_id = $group_id
                    MERGE (m)-[:LISTENS_TO_MQ]->(topic)
                """, {
                    "method_signature": listener['method_signature'],
                    "topic": listener['topic'],
                    "mq_type": listener['mq_type'],
                    "group_id": listener.get('group_id', '')
                })
        
        # 存储MQ发送关系
        logger.info(f"创建MQ发送关系 ({len(mq_senders) if mq_senders else 0} 个)...")
        if mq_senders:
            for sender in mq_senders:
                self.client.execute_write("""
                    MATCH (m:Method {signature: $method_signature})
                    MERGE (topic:MQTopic {name: $topic, mq_type: $mq_type})
                    MERGE (m)-[:SENDS_TO_MQ]->(topic)
                """, {
                    "method_signature": sender['method_signature'],
                    "topic": sender['topic'],
                    "mq_type": sender['mq_type']
                })
        
        # 存储Mapper和表的关系
        logger.info(f"创建Mapper和表的关系 ({len(mapper_tables) if mapper_tables else 0} 个)...")
        if mapper_tables:
            for mapper_table in mapper_tables:
                self.client.execute_write("""
                    MATCH (mapper:Type {fqn: $mapper_fqn})
                    MERGE (table:Table {name: $table_name})
                    SET table.entity_fqn = $entity_fqn
                    MERGE (mapper)-[:MAPPER_FOR_TABLE]->(table)
                """, {
                    "mapper_fqn": mapper_table['mapper_fqn'],
                    "table_name": mapper_table['table_name'],
                    "entity_fqn": mapper_table.get('entity_fqn')
                })
        
        logger.info("✅ Neo4j存储完成！")
    
    def _create_package_node(self, project_name: str, package_name: str):
        """创建包节点"""
        self.client.execute_write("""
            MATCH (p:Project {name: $project_name})
            MERGE (pkg:Package {fqn: $package_name})
            SET pkg.name = $package_name
            MERGE (p)-[:CONTAINS]->(pkg)
        """, {
            "project_name": project_name,
            "package_name": package_name
        })
    
    def _create_annotation_relationship(self, target_signature: str, annotation_info: Dict, target_type: str):
        """创建注解关系"""
        ann_name = annotation_info.get('name', '')
        ann_fqn = annotation_info.get('fqn', ann_name)
        
        # 根据目标类型选择匹配字段
        if target_type == 'Type':
            match_field = 'fqn'
        else:
            match_field = 'signature'
        
        self.client.execute_write(f"""
            MATCH (target)
            WHERE target.{match_field} = $target_signature
            MERGE (a:Annotation {{fqn: $ann_fqn}})
            SET a.name = $ann_name
            MERGE (target)-[:ANNOTATED_BY]->(a)
        """, {
            "target_signature": target_signature,
            "ann_fqn": ann_fqn,
            "ann_name": ann_name
        })
    
    def _track_interface_implementations(self, interface_fqn: str, project_path: str):
        """
        追踪接口的实现类
        
        Args:
            interface_fqn: 接口的FQN
            project_path: 项目路径
        """
        try:
            # 查找实现类
            implementations = self.dependency_tracker.find_interface_implementations(
                interface_fqn,
                [project_path]
            )
            
            if implementations:
                logger.info(f"接口 {interface_fqn} 找到 {len(implementations)} 个实现类")
                for impl in implementations:
                    impl_fqn = impl['fqn']
                    # 添加到待扫描列表（如果还未扫描）
                    if not self.dependency_tracker.check_class_scanned(impl_fqn):
                        self.dependency_tracker.add_pending_class(impl_fqn)
                        logger.debug(f"添加待扫描实现类: {impl_fqn}")
        except Exception as e:
            logger.warning(f"追踪接口实现类失败 {interface_fqn}: {e}")
    
    def _resolve_type_fqn(self, type_name: str, imports: List[Dict], package_name: Optional[str] = None) -> Optional[str]:
        """
        解析类型的FQN
        
        Args:
            type_name: 类型名称
            imports: 导入列表
            package_name: 包名
        
        Returns:
            类型的FQN，如果无法解析返回None
        """
        if not type_name:
            return None
        
        # 如果已经是FQN格式（包含多个点）
        if '.' in type_name and len(type_name.split('.')) >= 2:
            return type_name
        
        # 从导入中查找
        import_map = {}
        for imp in imports:
            if imp.get('path') and not imp.get('wildcard', False):
                import_path = imp['path']
                simple_name = import_path.split('.')[-1]
                import_map[simple_name] = import_path
        
        # 精确匹配
        if type_name in import_map:
            return import_map[type_name]
        
        # 尝试包名 + 类型名
        if package_name:
            possible_fqn = f"{package_name}.{type_name}"
            return possible_fqn
        
        return None
    
    def _infer_table_name_from_mapper(self, mapper_fqn: str, source_code: str, imports: List[Dict], package_name: Optional[str]) -> Optional[str]:
        """
        从Mapper接口推断表名
        
        Args:
            mapper_fqn: Mapper接口的FQN
            source_code: 源代码
            imports: 导入列表
            package_name: 包名
        
        Returns:
            表名，如果无法推断返回None
        """
        # 方法1: 从Mapper接口名推断（去掉Mapper后缀，转下划线）
        mapper_name = mapper_fqn.split('.')[-1]
        if mapper_name.endswith('Mapper'):
            entity_name = mapper_name[:-6]  # 去掉Mapper
            # 驼峰转下划线（简单实现）
            table_name = self._camel_to_snake(entity_name)
            return table_name
        
        # 方法2: 从方法参数中的实体类推断
        # 查找方法参数中的实体类（通常是domain.db、domain或entity包下的类）
        import re
        # 查找方法参数中的类型，如 selectByHostUid(ChatroomHostGuardActiveInfo record)
        # 匹配模式：类型名 参数名
        entity_pattern = r'(\w+)\s+\w+\s*[,\)]'
        matches = re.findall(entity_pattern, source_code)
        for match in matches:
            if match and match[0].isupper():
                # 可能是实体类名
                entity_fqn = self._resolve_type_fqn(match, imports, package_name)
                if entity_fqn:
                    # 检查是否是实体类（domain.db、domain或entity包）
                    entity_lower = entity_fqn.lower()
                    if 'domain.db' in entity_lower or 'domain' in entity_lower or 'entity' in entity_lower:
                        # 从实体类名推断表名
                        entity_name = entity_fqn.split('.')[-1]
                        # 去掉DO、Entity等后缀
                        if entity_name.endswith('DO'):
                            entity_name = entity_name[:-2]
                        elif entity_name.endswith('Entity'):
                            entity_name = entity_name[:-6]
                        table_name = self._camel_to_snake(entity_name)
                        return table_name
        
        # 方法3: 从导入的实体类推断
        for imp in imports:
            if imp.get('path'):
                import_path = imp['path']
                import_lower = import_path.lower()
                # 检查是否是实体类导入（domain.db、domain或entity包）
                if 'domain.db' in import_lower or ('domain' in import_lower and 'mapper' not in import_lower) or 'entity' in import_lower:
                    entity_name = import_path.split('.')[-1]
                    # 去掉DO、Entity等后缀
                    if entity_name.endswith('DO'):
                        entity_name = entity_name[:-2]
                    elif entity_name.endswith('Entity'):
                        entity_name = entity_name[:-6]
                    table_name = self._camel_to_snake(entity_name)
                    return table_name
        
        return None
    
    def _camel_to_snake(self, camel_str: str) -> str:
        """驼峰转下划线命名"""
        import re
        # 在大写字母前插入下划线，然后转小写
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()
    
    def _extract_kafka_listener_info(self, method_decl, annotation, source_code: str) -> Tuple[Optional[str], Optional[str]]:
        """
        提取Kafka监听信息
        
        Args:
            method_decl: 方法声明
            annotation: 注解对象
            source_code: 源代码
        
        Returns:
            (topic, group_id)
        """
        topic = None
        group_id = None
        
        # 从注解参数中提取
        if hasattr(annotation, 'arguments') and annotation.arguments:
            for arg in annotation.arguments:
                if hasattr(arg, 'name') and arg.name == 'topics':
                    if hasattr(arg, 'value'):
                        # 可能是字符串字面量或数组
                        if isinstance(arg.value, list):
                            if arg.value:
                                topic = str(arg.value[0])
                        else:
                            topic = str(arg.value)
                elif hasattr(arg, 'name') and arg.name == 'groupId':
                    if hasattr(arg, 'value'):
                        group_id = str(arg.value)
        
        # 如果注解参数中没有，尝试从源代码中提取
        if not topic:
            import re
            # 查找 @KafkaListener(topics = "xxx", groupId = "xxx")
            pattern = r'@KafkaListener\s*\([^)]*topics\s*=\s*["\']?([^"\'\),]+)["\']?'
            match = re.search(pattern, source_code)
            if match:
                topic = match.group(1).strip()
            
            # 查找 groupId
            pattern = r'groupId\s*=\s*["\']?([^"\'\),]+)["\']?'
            match = re.search(pattern, source_code)
            if match:
                group_id = match.group(1).strip()
        
        return topic, group_id
    
    def _extract_rabbit_listener_info(self, method_decl, annotation, source_code: str) -> Tuple[Optional[str], Optional[str]]:
        """
        提取RabbitMQ监听信息
        
        Args:
            method_decl: 方法声明
            annotation: 注解对象
            source_code: 源代码
        
        Returns:
            (queue, exchange)
        """
        queue = None
        
        # 从注解参数中提取
        if hasattr(annotation, 'arguments') and annotation.arguments:
            for arg in annotation.arguments:
                if hasattr(arg, 'name') and arg.name in ['queues', 'queue']:
                    if hasattr(arg, 'value'):
                        if isinstance(arg.value, list):
                            if arg.value:
                                queue = str(arg.value[0])
                        else:
                            queue = str(arg.value)
        
        # 如果注解参数中没有，尝试从源代码中提取
        if not queue:
            import re
            # 查找 @RabbitListener(queues = "xxx")
            pattern = r'@RabbitListener\s*\([^)]*queues?\s*=\s*["\']?([^"\'\),]+)["\']?'
            match = re.search(pattern, source_code)
            if match:
                queue = match.group(1).strip()
        
        return queue, None
    
    def _extract_rocketmq_listener_info(self, method_decl, annotation, source_code: str) -> Tuple[Optional[str], Optional[str]]:
        """
        提取RocketMQ监听信息
        
        Args:
            method_decl: 方法声明
            annotation: 注解对象
            source_code: 源代码
        
        Returns:
            (topic, consumerGroup)
        """
        topic = None
        consumer_group = None
        
        # 从注解参数中提取
        if hasattr(annotation, 'arguments') and annotation.arguments:
            for arg in annotation.arguments:
                if hasattr(arg, 'name') and arg.name == 'topic':
                    if hasattr(arg, 'value'):
                        topic = str(arg.value)
                elif hasattr(arg, 'name') and arg.name in ['consumerGroup', 'consumer_group']:
                    if hasattr(arg, 'value'):
                        consumer_group = str(arg.value)
        
        # 如果注解参数中没有，尝试从源代码中提取
        if not topic:
            import re
            # 查找 @RocketMQMessageListener(topic = "xxx", consumerGroup = "xxx")
            pattern = r'@RocketMQMessageListener\s*\([^)]*topic\s*=\s*["\']?([^"\'\),]+)["\']?'
            match = re.search(pattern, source_code)
            if match:
                topic = match.group(1).strip()
            
            # 查找 consumerGroup
            pattern = r'consumerGroup\s*=\s*["\']?([^"\'\),]+)["\']?'
            match = re.search(pattern, source_code)
            if match:
                consumer_group = match.group(1).strip()
        
        return topic, consumer_group
    
    def _extract_mq_sends(self, node, current_class: str, method_signature: str, mq_senders: List[Dict], java_file: Path, source_code: str):
        """
        递归提取MQ发送代码
        
        Args:
            node: AST节点
            current_class: 当前类FQN
            method_signature: 方法签名
            mq_senders: MQ发送列表
            java_file: Java文件路径
            source_code: 源代码
        """
        # 检查是否是方法调用
        if isinstance(node, javalang.tree.MethodInvocation):
            member = node.member if hasattr(node, 'member') else None
            qualifier = node.qualifier if hasattr(node, 'qualifier') else None
            
            # 检查是否是KafkaTemplate.send或RabbitTemplate.send
            if member == 'send' and qualifier:
                qualifier_str = '.'.join(qualifier) if isinstance(qualifier, list) else str(qualifier)
                
                # 检查是否是KafkaTemplate
                if 'KafkaTemplate' in qualifier_str or 'kafkaTemplate' in qualifier_str:
                    # 提取topic（通常是第一个参数）
                    if hasattr(node, 'arguments') and node.arguments:
                        topic = None
                        # 第一个参数通常是topic
                        if len(node.arguments) > 0:
                            arg = node.arguments[0]
                            if isinstance(arg, javalang.tree.StringLiteral):
                                topic = arg.value
                            elif isinstance(arg, javalang.tree.MemberReference):
                                # 可能是常量引用，尝试从源代码中提取
                                import re
                                pattern = rf'{arg.member}\s*=\s*["\']([^"\']+)["\']'
                                match = re.search(pattern, source_code)
                                if match:
                                    topic = match.group(1)
                        
                        if topic:
                            mq_senders.append({
                                'class_fqn': current_class,
                                'method_signature': method_signature,
                                'topic': topic,
                                'mq_type': 'KAFKA'
                            })
                            logger.debug(f"发现Kafka发送: {current_class}.{method_signature} -> topic: {topic}")
                
                # 检查是否是RabbitTemplate
                elif 'RabbitTemplate' in qualifier_str or 'rabbitTemplate' in qualifier_str:
                    # 提取exchange和routingKey
                    topic = None
                    if hasattr(node, 'arguments') and node.arguments:
                        if len(node.arguments) > 0:
                            arg = node.arguments[0]
                            if isinstance(arg, javalang.tree.StringLiteral):
                                topic = arg.value
                    
                    if topic:
                        mq_senders.append({
                            'class_fqn': current_class,
                            'method_signature': method_signature,
                            'topic': topic,
                            'mq_type': 'RABBITMQ'
                        })
                        logger.debug(f"发现RabbitMQ发送: {current_class}.{method_signature} -> exchange: {topic}")
                
                # 检查是否是RocketMQTemplate
                elif 'RocketMQTemplate' in qualifier_str or 'rocketMQTemplate' in qualifier_str or 'rocketMqTemplate' in qualifier_str:
                    # 提取topic和tag
                    topic = None
                    if hasattr(node, 'arguments') and node.arguments:
                        # RocketMQTemplate.send通常第一个参数是destination (topic:tag格式)
                        if len(node.arguments) > 0:
                            arg = node.arguments[0]
                            if isinstance(arg, javalang.tree.StringLiteral):
                                destination = arg.value
                                # 提取topic（去掉tag部分）
                                topic = destination.split(':')[0] if ':' in destination else destination
                            elif isinstance(arg, javalang.tree.MemberReference):
                                # 可能是常量引用，尝试从源代码中提取
                                import re
                                pattern = rf'{arg.member}\s*=\s*["\']([^"\']+)["\']'
                                match = re.search(pattern, source_code)
                                if match:
                                    destination = match.group(1)
                                    topic = destination.split(':')[0] if ':' in destination else destination
                    
                    if topic:
                        mq_senders.append({
                            'class_fqn': current_class,
                            'method_signature': method_signature,
                            'topic': topic,
                            'mq_type': 'ROCKETMQ'
                        })
                        logger.debug(f"发现RocketMQ发送: {current_class}.{method_signature} -> topic: {topic}")
        
        # 递归处理子节点
        if hasattr(node, '__dict__'):
            for attr_name, attr_value in node.__dict__.items():
                if attr_name.startswith('_'):
                    continue
                
                if isinstance(attr_value, list):
                    for item in attr_value:
                        if isinstance(item, javalang.tree.Node):
                            self._extract_mq_sends(item, current_class, method_signature, mq_senders, java_file, source_code)
                elif isinstance(attr_value, javalang.tree.Node):
                    self._extract_mq_sends(attr_value, current_class, method_signature, mq_senders, java_file, source_code)
    
    def _create_project_node(self, project_name: str, project_path: str):
        """创建或更新项目节点"""
        try:
            self.client.execute_write("""
                MERGE (p:Project {name: $name})
                SET p.path = $path,
                    p.scanned_at = datetime(),
                    p.scanner = 'python-ast'
            """, {
                "name": project_name,
                "path": project_path
            })
            logger.info(f"✅ 项目节点创建/更新成功: {project_name}")
        except Exception as e:
            logger.error(f"创建项目节点失败: {e}", exc_info=True)
