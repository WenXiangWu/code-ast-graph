"""
Java AST Scanner V2 - 技术方案导向版本
核心改进:
1. 仅追踪注入依赖调用 (@Reference/@DubboReference/@Resource/@Autowired)
2. 过滤非业务类 (无注入字段且不被注入的类)
3. Method级CALLS边 (内部调用)
4. Type级DUBBO_CALLS边 (Dubbo调用)
5. arch_layer推断 (Controller/Service/Manager/DAO/Mapper/Entity)
6. RPC入口识别 (@MobileAPI/@PostMapping等)
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set
from collections import defaultdict

try:
    import javalang
except ImportError:
    javalang = None
    logging.warning("javalang module not found. Please install it with: pip install javalang")

from .config import JavaParserConfig
from ...storage.neo4j.storage import Neo4jStorage

logger = logging.getLogger(__name__)


class JavaASTScannerV2:
    """技术方案导向的 Java AST 扫描器"""
    
    # 注入注解四件套
    INJECTION_ANNOTATIONS = {
        'Reference', 'DubboReference', 'Resource', 'Autowired'
    }
    
    # RPC/HTTP 入口注解
    RPC_ANNOTATIONS = {
        'MobileAPI', 'PostMapping', 'GetMapping', 
        'RequestMapping', 'PutMapping', 'DeleteMapping',
        'PatchMapping'
    }
    
    # Dubbo 服务注解
    DUBBO_SERVICE_ANNOTATIONS = {
        'DubboService', 'Service'  # Service需要检查包名是否为dubbo
    }
    
    # MQ 监听注解 (Kafka / RocketMQ 用于提取 topic/group)
    MQ_LISTENER_ANNOTATIONS = {
        'KafkaListener', 'KafkaListeners',
        'RocketMQMessageListener',
        'RabbitListener'
    }
    KAFKA_LISTENER_ANNOTATIONS = ('KafkaListener', 'KafkaListeners')
    ROCKETMQ_LISTENER_ANNOTATION = 'RocketMQMessageListener'
    
    # MQ 生产者字段类型
    MQ_PRODUCER_TYPES = {
        'KafkaProducer', 'KafkaTemplate',
        'RocketMQTemplate', 'RocketMQManager',
        'RabbitTemplate'
    }
    
    def __init__(
        self,
        config: Optional[JavaParserConfig] = None,
        client: Optional[Neo4jStorage] = None
    ):
        """初始化扫描器"""
        if config is None:
            from .config import get_java_parser_config
            config = get_java_parser_config()
        
        self.config = config
        self.client = client
        
        # 注入字段映射: class_fqn -> {field_name: {annotation, type_fqn}}
        self.injected_fields = defaultdict(dict)
        
        # 被注入的类型集合: 用于判断类是否为业务类
        self.injected_types = set()
        
        # Dubbo接口集合: 用于判断类是否为业务类
        self.dubbo_interfaces = set()
        
        # Mapper接口集合
        self.mapper_interfaces = set()
    
    def scan_project(
        self,
        project_name: str,
        project_path: str,
        force_rescan: bool = False,
        commit_id: str = ""
    ) -> Dict:
        """
        全量扫描 Java 项目
        
        Args:
            project_name: 项目名称
            project_path: 项目路径
            force_rescan: 是否强制重新扫描
            commit_id: 当前 Git commit ID
        
        Returns:
            扫描结果字典
        """
        logger.info(f"开始全量扫描项目: {project_name}")
        
        # 检查项目路径
        project_dir = Path(project_path)
        if not project_dir.exists():
            logger.error(f"项目路径不存在: {project_path}")
            return {
                "success": False,
                "error": f"项目路径不存在: {project_path}"
            }
        
        try:
            # 查找所有 Java 文件
            java_files = self._find_java_files(project_dir)
            logger.info(f"找到 {len(java_files)} 个 Java 文件")
            
            # 调用核心扫描逻辑 (需要过滤非业务类)
            return self._scan_files(
                project_name=project_name,
                project_path=project_path,
                java_files=java_files,
                filter_business_classes=True,
                commit_id=commit_id
            )
        
        except Exception as e:
            logger.error(f"扫描项目失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def scan_specific_classes(
        self,
        project_name: str,
        project_path: str,
        class_fqns: List[str]
    ) -> Dict:
        """
        增量扫描: 只扫描指定的类
        
        Args:
            project_name: 项目名称
            project_path: 项目路径
            class_fqns: 要扫描的类的全限定名列表
        
        Returns:
            扫描结果字典
        """
        logger.info(f"开始增量扫描 {len(class_fqns)} 个类: {project_name}")
        
        # 检查项目路径
        project_dir = Path(project_path)
        if not project_dir.exists():
            logger.error(f"项目路径不存在: {project_path}")
            return {
                "success": False,
                "error": f"项目路径不存在: {project_path}"
            }
        
        try:
            # 1. 查找指定类的 Java 文件
            logger.info(f"查找 {len(class_fqns)} 个类的源文件...")
            target_files = self._find_specific_class_files(class_fqns, project_dir)
            
            if not target_files:
                logger.warning(f"未找到任何目标类的源文件")
                return {
                    "success": False,
                    "error": "未找到任何目标类的源文件"
                }
            
            logger.info(f"✓ 找到 {len(target_files)} 个目标文件")
            
            # 2. 调用核心扫描逻辑 (不过滤业务类)
            return self._scan_files(
                project_name=project_name,
                project_path=project_path,
                java_files=target_files,
                filter_business_classes=False
            )
        
        except Exception as e:
            logger.error(f"增量扫描失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _scan_files(
        self,
        project_name: str,
        project_path: str,
        java_files: List[Path],
        filter_business_classes: bool,
        commit_id: str = ""
    ) -> Dict:
        """
        核心扫描逻辑 (全量和增量扫描共享)
        
        Args:
            project_name: 项目名称
            project_path: 项目路径
            java_files: 要扫描的 Java 文件列表
            filter_business_classes: 是否过滤非业务类
        
        Returns:
            扫描结果字典
        """
        # 第一遍扫描: 提取所有类、方法、字段、注入关系
        logger.info("第一遍扫描: 提取类、方法、字段、注入关系...")
        scan_result = self._first_pass_scan(java_files, project_name)
        
        # 业务类过滤 (可选)
        filtered_count = 0
        if filter_business_classes:
            logger.info("过滤非业务类...")
            original_count = len(scan_result['classes'])
            business_classes = self._filter_business_classes(scan_result['classes'])
            filtered_count = original_count - len(business_classes)
            logger.info(f"✓ 过滤完成: 保留 {len(business_classes)} 个业务类, 跳过 {filtered_count} 个非业务类 (总共 {original_count} 个)")
            scan_result['classes'] = business_classes
        else:
            logger.info("跳过业务类过滤 (增量扫描模式)")
        
        # 第二遍扫描: 提取调用关系及 MQ 发送 (仅业务类中注入字段发起的调用)
        logger.info("第二遍扫描: 提取调用关系 (仅注入字段)...")
        calls, mq_senders = self._second_pass_scan(java_files, scan_result['classes'])
        scan_result['calls'] = calls
        scan_result['mq_senders'] = mq_senders
        
        # 存储到 Neo4j
        if self.client:
            logger.info("存储到 Neo4j...")
            self._store_to_neo4j(project_name, project_path, scan_result, commit_id)
        
        # 生成分类报告（根据配置决定是否生成）
        report_path = None
        if self._should_generate_report():
            logger.info("生成扫描分类报告...")
            report_path = self._generate_scan_report(project_name, project_path, scan_result)
        
        result = {
            "success": True,
            "message": f"扫描完成: {len(scan_result['classes'])} 个类, {len(scan_result['methods'])} 个方法",
            "stats": {
                "classes": len(scan_result['classes']),
                "methods": len(scan_result['methods']),
                "fields": len(scan_result['fields']),
                "calls": len(calls),
                "injected_fields": sum(len(v) for v in self.injected_fields.values()),
                "filtered_classes": filtered_count
            }
        }
        
        if report_path:
            result["report_path"] = report_path
        
        return result
    
    def _find_specific_class_files(
        self,
        class_fqns: List[str],
        project_dir: Path
    ) -> List[Path]:
        """
        查找指定类的 Java 文件
        
        Args:
            class_fqns: 类的全限定名列表
            project_dir: 项目目录
        
        Returns:
            Java 文件路径列表
        """
        target_files = []
        class_fqn_set = set(class_fqns)
        found_fqns = set()
        
        for java_file in self._find_java_files(project_dir):
            # 快速检查: 读取文件的 package 和 class 声明
            try:
                with open(java_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 简单解析: 提取 package 和 class/interface 名称
                    import re
                    package_match = re.search(r'package\s+([\w.]+)\s*;', content)
                    class_matches = re.findall(r'(?:public\s+)?(?:class|interface|enum)\s+(\w+)', content)
                    
                    if package_match and class_matches:
                        package = package_match.group(1)
                        for class_name in class_matches:
                            fqn = f"{package}.{class_name}"
                            if fqn in class_fqn_set and fqn not in found_fqns:
                                target_files.append(java_file)
                                found_fqns.add(fqn)
                                logger.info(f"  ✓ 找到: {fqn}")
                                break
            except Exception as e:
                logger.warning(f"快速检查文件失败 {java_file}: {e}")
        
        # 报告未找到的类
        not_found = class_fqn_set - found_fqns
        if not_found:
            logger.warning(f"未找到以下类的源文件: {', '.join(not_found)}")
        
        return target_files
    
    def _find_java_files(self, project_dir: Path) -> List[Path]:
        """查找所有 Java 文件 (排除 test 目录)"""
        java_files = []
        for root, dirs, files in os.walk(project_dir):
            # 排除常见的非源码目录和 test 目录
            dirs[:] = [d for d in dirs if d not in {
                'target', 'build', '.git', '.idea', 'node_modules', 'test'
            }]
            
            # 跳过 test 路径
            root_path = Path(root)
            if 'test' in root_path.parts or '\\test\\' in str(root_path) or '/test/' in str(root_path):
                continue
            
            for file in files:
                if file.endswith('.java'):
                    # 跳过 Test 结尾的文件
                    if file.endswith('Test.java') or file.endswith('Tests.java'):
                        continue
                    java_files.append(Path(root) / file)
        
        return java_files
    
    def _first_pass_scan(self, java_files: List[Path], project_name: str) -> Dict:
        """
        第一遍扫描: 提取类、方法、字段、注入关系
        
        Returns:
            {
                'packages': [],
                'classes': [],
                'methods': [],
                'fields': [],
                'dubbo_references': [],
                'dubbo_services': [],
                'mq_listeners': [],
                'mq_senders': [],
                'mapper_tables': [],
                'rpc_endpoints': [],
                'jobs': []
            }
        """
        packages = set()
        classes = []
        methods = []
        fields = []
        dubbo_references = []
        dubbo_services = []
        
        # 统计失败数量
        parse_errors = 0
        mq_listeners = []
        mq_senders = []
        mapper_tables = []
        rpc_endpoints = []
        jobs = []
        
        for idx, java_file in enumerate(java_files, 1):
            if idx % 100 == 0:
                logger.info(f"  第一遍扫描进度: [{idx}/{len(java_files)}]")
            
            try:
                with open(java_file, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
                
                # 解析 AST
                tree = javalang.parse.parse(source_code)
                
                # 提取包名
                package_name = tree.package.name if tree.package else ''
                if package_name:
                    packages.add(package_name)
                
                # 提取 imports
                imports = self._extract_imports(tree)
                
                # 遍历类型声明
                for path, type_decl in tree.filter(javalang.tree.TypeDeclaration):
                    # 提取类信息
                    class_info = self._extract_class_info(
                        type_decl, package_name, java_file, imports, source_code
                    )
                    if class_info:
                        classes.append(class_info)
                        
                        # 提取字段 (仅注入字段)
                        class_fields = self._extract_injected_fields(
                            type_decl, class_info['fqn'], package_name, imports
                        )
                        fields.extend(class_fields)
                        
                        # 提取方法
                        class_methods, class_rpc_endpoints, class_jobs, class_mq_listeners = self._extract_methods(
                            type_decl, class_info['fqn'], package_name, imports, java_file, source_code
                        )
                        methods.extend(class_methods)
                        rpc_endpoints.extend(class_rpc_endpoints)
                        jobs.extend(class_jobs)
                        mq_listeners.extend(class_mq_listeners)
                        
                        # 提取 Dubbo 服务声明
                        if class_info.get('is_dubbo_service'):
                            dubbo_services.append({
                                'class_fqn': class_info['fqn'],
                                'interfaces': class_info.get('interfaces', [])
                            })
                        
                        # 提取 Mapper-Table 关系
                        if class_info.get('is_mapper'):
                            table_name = self._infer_table_name_from_mapper(
                                class_info['fqn'], source_code, imports, package_name
                            )
                            if table_name:
                                mapper_tables.append({
                                    'mapper_fqn': class_info['fqn'],
                                    'table_name': table_name,
                                    'entity_fqn': None
                                })
            
            except Exception as e:
                parse_errors += 1
                logger.warning(f"解析文件失败 {java_file}")
                logger.warning(f"  错误类型: {type(e).__name__}")
                
                # 尝试获取错误信息
                error_msg = str(e) if str(e) else "无错误描述"
                if hasattr(e, 'description') and e.description:
                    error_msg = f"{e.description}"
                if hasattr(e, 'at') and e.at:
                    try:
                        error_msg += f" (位置: {e.at})"
                    except:
                        pass
                
                logger.warning(f"  错误信息: {error_msg[:500]}")
                
                # JavaSyntaxError 特殊处理
                if type(e).__name__ == 'JavaSyntaxError':
                    logger.warning(f"  可能原因: Java 语法不兼容 (javalang 不支持 Java 14+ 的 switch 表达式等新特性)")
                continue
        
        # 收集 Dubbo References (从注入字段中筛选)
        for class_fqn, fields_map in self.injected_fields.items():
            for field_name, field_info in fields_map.items():
                if field_info['annotation'] in ['Reference', 'DubboReference']:
                    service_interface = field_info.get('type_fqn')
                    if service_interface:
                        dubbo_references.append({
                            'class_fqn': class_fqn,
                            'field_name': field_name,
                            'service_interface': service_interface
                        })
                        self.dubbo_interfaces.add(service_interface)
                    else:
                        logger.warning(f"Dubbo 注入字段缺少 type_fqn: {class_fqn}.{field_name}")
        
        # 输出统计信息
        # 统计 arch_layer 分布
        layer_stats = {}
        for cls in classes:
            layer = cls.get('arch_layer', 'Other')
            layer_stats[layer] = layer_stats.get(layer, 0) + 1
        
        logger.info(f"✓ 第一遍扫描完成:")
        logger.info(f"  - 成功: {len(java_files) - parse_errors} 个文件")
        logger.info(f"  - 失败: {parse_errors} 个文件")
        logger.info(f"  - 类: {len(classes)} 个")
        logger.info(f"  - 方法: {len(methods)} 个")
        logger.info(f"  - 注入字段: {len(fields)} 个")
        logger.info(f"  - Dubbo References: {len(dubbo_references)} 个")
        logger.info(f"  - Dubbo Services: {len(dubbo_services)} 个")
        logger.info(f"  - 架构层分布: {layer_stats}")
        
        return {
            'packages': list(packages),
            'classes': classes,
            'methods': methods,
            'fields': fields,
            'dubbo_references': dubbo_references,
            'dubbo_services': dubbo_services,
            'mq_listeners': mq_listeners,
            'mq_senders': mq_senders,
            'mapper_tables': mapper_tables,
            'rpc_endpoints': rpc_endpoints,
            'jobs': jobs,
            'parse_errors': parse_errors  # 添加失败统计
        }
    
    def _extract_imports(self, tree) -> Dict[str, str]:
        """
        提取 import 映射
        
        返回两种类型的 import:
        1. 显式 import: {'ClassName': 'com.example.ClassName'}
        2. 通配符 import: {'*:com.example': 'com.example'}  # 特殊标记，不包含 .*
        """
        imports = {}
        if tree.imports:
            for imp in tree.imports:
                if imp.path:
                    full_path = imp.path
                    if imp.wildcard:
                        # 通配符 import: import com.example.*
                        # javalang 的 path 已经不包含 .*，直接使用
                        # 使用特殊前缀 "*:" 标记
                        imports[f"*:{full_path}"] = full_path
                    else:
                        # 显式 import: import com.example.ClassName
                        simple_name = full_path.split('.')[-1]
                        imports[simple_name] = full_path
        return imports
    
    def _extract_class_info(
        self, 
        type_decl, 
        package_name: str, 
        java_file: Path,
        imports: Dict[str, str],
        source_code: str
    ) -> Optional[Dict]:
        """提取类信息"""
        if not hasattr(type_decl, 'name'):
            return None
        
        class_name = type_decl.name
        class_fqn = f"{package_name}.{class_name}" if package_name else class_name
        
        # 提取修饰符
        modifiers = [str(m) for m in type_decl.modifiers] if type_decl.modifiers else []
        
        # 提取注解
        annotations = []
        is_dubbo_service = False
        is_aries_job = False
        if hasattr(type_decl, 'annotations') and type_decl.annotations:
            for ann in type_decl.annotations:
                ann_name = self._extract_annotation_name(ann)
                annotations.append({'name': ann_name})
                
                # 检查是否为 Dubbo 服务
                if ann_name in self.DUBBO_SERVICE_ANNOTATIONS:
                    is_dubbo_service = True
                elif ann_name == 'Service' and 'dubbo' in source_code.lower():
                    is_dubbo_service = True
                
                # 检查是否为 Aries Job
                if ann_name == 'AriesCronJobListener':
                    is_aries_job = True
        
        # 提取继承和实现
        extends = []
        implements = []
        if hasattr(type_decl, 'extends') and type_decl.extends:
            extends_name = self._extract_type_name(type_decl.extends)
            if extends_name:
                extends.append(self._resolve_type_fqn(extends_name, imports, package_name))
        
        if hasattr(type_decl, 'implements') and type_decl.implements:
            for impl in type_decl.implements:
                impl_name = self._extract_type_name(impl)
                if impl_name:
                    implements.append(self._resolve_type_fqn(impl_name, imports, package_name))
        
        # 判断类型 - 只保留 Class 和 Interface,排除 Enum 和 Annotation
        if isinstance(type_decl, javalang.tree.InterfaceDeclaration):
            kind = 'INTERFACE'
        elif isinstance(type_decl, javalang.tree.EnumDeclaration):
            # 不存储 Enum
            return None
        elif isinstance(type_decl, javalang.tree.AnnotationDeclaration):
            # 不存储 Annotation
            return None
        else:
            # 如果是 Aries Job，类型改为 ARIES_JOB
            if is_aries_job:
                kind = 'ARIES_JOB'
            else:
                kind = 'CLASS'
        
        # 判断是否为 Mapper
        is_mapper = self._is_mapper_interface(type_decl, class_name, package_name, source_code)
        if is_mapper:
            self.mapper_interfaces.add(class_fqn)
        
        # 推断 arch_layer
        arch_layer = self._infer_arch_layer(
            class_name, package_name, annotations, is_mapper, is_dubbo_service, implements
        )
        
        # 调试日志: 记录非 Other 层的类
        if arch_layer != 'Other':
            logger.debug(f"识别架构层: {class_fqn} -> {arch_layer}")
        
        return {
            'fqn': class_fqn,
            'name': class_name,
            'kind': kind,
            'package': package_name,
            'file_path': str(java_file),
            'modifiers': modifiers,
            'annotations': annotations,
            'extends': extends,
            'implements': implements,
            'is_dubbo_service': is_dubbo_service,
            'is_mapper': is_mapper,
            'is_aries_job': is_aries_job,
            'is_interface': (kind == 'INTERFACE'),
            'arch_layer': arch_layer,
            'visibility': self._extract_visibility(modifiers)
        }
    
    def _extract_injected_fields(
        self,
        type_decl,
        class_fqn: str,
        package_name: str,
        imports: Dict[str, str]
    ) -> List[Dict]:
        """提取注入字段 (仅 @Reference/@DubboReference/@Resource/@Autowired)"""
        injected_fields_list = []
        
        if not hasattr(type_decl, 'body') or not type_decl.body:
            return injected_fields_list
        
        for body_decl in type_decl.body:
            if not isinstance(body_decl, javalang.tree.FieldDeclaration):
                continue
            
            # 提取字段注解
            field_annotations = []
            if hasattr(body_decl, 'annotations') and body_decl.annotations:
                for ann in body_decl.annotations:
                    ann_name = self._extract_annotation_name(ann)
                    field_annotations.append(ann_name)
            
            # 检查是否为注入字段
            injection_type = None
            for ann_name in field_annotations:
                if self._is_injection_annotation(ann_name):
                    injection_type = self._normalize_injection_annotation(ann_name)
                    break
            
            if not injection_type:
                continue  # 非注入字段,跳过
            
            # 提取字段类型
            field_type_str = self._extract_field_type(body_decl)
            
            # 提取字段名
            if body_decl.declarators:
                for declarator in body_decl.declarators:
                    field_name = declarator.name
                    field_type_fqn = self._resolve_type_fqn(field_type_str, imports, package_name)
                    
                    # 记录到 injected_fields 映射
                    self.injected_fields[class_fqn][field_name] = {
                        'annotation': injection_type,
                        'type_fqn': field_type_fqn or field_type_str
                    }
                    
                    # 记录到 injected_types 集合
                    self.injected_types.add(field_type_fqn or field_type_str)
                    
                    # 创建 Field 节点数据
                    injected_fields_list.append({
                        'name': field_name,
                        'class_fqn': class_fqn,
                        'type': field_type_str,
                        'type_fqn': field_type_fqn or field_type_str,
                        'injection_type': injection_type,
                        'signature': f"{class_fqn}.{field_name}"
                    })
        
        return injected_fields_list
    
    def _extract_methods(
        self,
        type_decl,
        class_fqn: str,
        package_name: str,
        imports: Dict[str, str],
        java_file: Path,
        source_code: str = ""
    ) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
        """
        提取方法、RPC入口、Job、MQ监听器
        
        Returns:
            (methods, rpc_endpoints, jobs, mq_listeners)
        """
        methods = []
        rpc_endpoints = []
        jobs = []
        mq_listeners = []
        
        if not hasattr(type_decl, 'body') or not type_decl.body:
            return methods, rpc_endpoints, jobs, mq_listeners
        
        for body_decl in type_decl.body:
            if not isinstance(body_decl, javalang.tree.MethodDeclaration):
                continue
            
            method_name = body_decl.name
            
            # 提取返回类型
            return_type_str = self._extract_return_type(body_decl)
            
            # 提取参数
            parameters = self._extract_parameters(body_decl)
            param_types = [p['type'] for p in parameters]
            
            # 构建方法签名
            method_signature = f"{class_fqn}.{method_name}({','.join(param_types)})"
            
            # 提取修饰符
            modifiers = [str(m) for m in body_decl.modifiers] if body_decl.modifiers else []
            
            # 提取注解
            annotations = []
            is_entry = False
            is_job = False
            is_mq_listener = False
            rpc_path = None
            http_method = None
            job_type = None
            cron_expr = None
            mq_topics = []
            mq_type = None
            mq_group = None
            
            if hasattr(body_decl, 'annotations') and body_decl.annotations:
                for ann in body_decl.annotations:
                    ann_name = self._extract_annotation_name(ann)
                    annotations.append({'name': ann_name})
                    
                    # 检查是否为 RPC 入口
                    if ann_name in self.RPC_ANNOTATIONS:
                        is_entry = True
                        rpc_path = self._extract_rpc_path(ann, ann_name)
                        http_method = self._infer_http_method(ann_name)
                    
                    # 检查是否为 Job
                    if ann_name in ['Scheduled', 'AriesCronJobListener', 'AriesDelayJobListener']:
                        is_job = True
                        job_type = 'scheduled' if 'Cron' in ann_name or ann_name == 'Scheduled' else 'delayed'
                        cron_expr = self._extract_cron_expr(ann)
                    
                    # 检查是否为 MQ 监听器 (Kafka/Rocket 使用 ported 的 AST+regex 提取)
                    if ann_name in self.KAFKA_LISTENER_ANNOTATIONS:
                        is_mq_listener = True
                        topic, group_id = self._extract_kafka_listener_info(body_decl, ann, source_code)
                        if topic:
                            mq_topics.append(topic)
                            mq_type = 'kafka'
                            mq_group = group_id or ''
                            mq_listeners.append({
                                'method_signature': method_signature,
                                'class_fqn': class_fqn,
                                'topic': topic,
                                'group_id': group_id or '',
                                'mq_type': 'kafka'
                            })
                    elif ann_name == self.ROCKETMQ_LISTENER_ANNOTATION:
                        is_mq_listener = True
                        topic, group_id = self._extract_rocketmq_listener_info(body_decl, ann, source_code)
                        if topic:
                            mq_topics.append(topic)
                            mq_type = 'rocket'
                            mq_group = group_id or ''
                            mq_listeners.append({
                                'method_signature': method_signature,
                                'class_fqn': class_fqn,
                                'topic': topic,
                                'group_id': group_id or '',
                                'mq_type': 'rocket'
                            })
                    elif ann_name in self.MQ_LISTENER_ANNOTATIONS:
                        is_mq_listener = True
                        mq_info = self._extract_mq_listener_info(ann, ann_name, source_code)
                        if mq_info:
                            for t in mq_info.get('topics', []):
                                mq_topics.append(t)
                            mq_type = mq_info.get('mq_type')
                            if mq_type == 'rocketmq':
                                mq_type = 'rocket'
                            mq_group = mq_info.get('group') or ''
                            for t in mq_info.get('topics', []):
                                mq_listeners.append({
                                    'method_signature': method_signature,
                                    'class_fqn': class_fqn,
                                    'topic': t,
                                    'group_id': mq_info.get('group') or '',
                                    'mq_type': mq_type or 'kafka'
                                })
            
            # 提取方法体行号
            line_start = body_decl.position.line if hasattr(body_decl, 'position') and body_decl.position else 0
            line_end = line_start  # javalang 不提供结束行,需要后续完善
            
            # 创建方法数据
            method_info = {
                'signature': method_signature,
                'name': method_name,
                'class_fqn': class_fqn,
                'return_type': return_type_str,
                'parameters': parameters,
                'modifiers': modifiers,
                'annotations': annotations,
                'is_entry': is_entry,
                'line_start': line_start,
                'line_end': line_end,
                'file_path': str(java_file),
                'visibility': self._extract_visibility(modifiers)
            }
            methods.append(method_info)
            
            # 创建 RPC Endpoint
            if is_entry and rpc_path:
                rpc_endpoints.append({
                    'path': rpc_path,
                    'http_method': http_method or 'POST',
                    'method_signature': method_signature,
                    'service_name': class_fqn.split('.')[-1]
                })
            
            # 创建 Job
            if is_job:
                jobs.append({
                    'fqn': f"{class_fqn}.{method_name}",
                    'name': method_name,
                    'job_type': job_type,
                    'cron_expr': cron_expr,
                    'class_fqn': class_fqn,
                    'method_signature': method_signature
                })
            # MQ 监听器已在注解循环中按 method_signature, class_fqn, topic, group_id, mq_type 追加到 mq_listeners
        
        return methods, rpc_endpoints, jobs, mq_listeners
    
    def _second_pass_scan(self, java_files: List[Path], classes: List[Dict]) -> List[Dict]:
        """
        第二遍扫描: 提取调用关系 (仅注入字段发起的调用)
        
        Args:
            java_files: 所有 Java 文件
            classes: 业务类列表 (已过滤)
        
        Returns:
            (calls, mq_senders)
            calls: [ { caller_class, caller_method, qualifier, callee_method, injection_type, target_type_fqn }, ... ]
            mq_senders: [ { caller_method, topic, mq_type: 'kafka'|'rocket' }, ... ]
        """
        calls = []
        mq_senders = []
        parse_errors = 0  # 统计第二遍扫描失败数量
        
        # 重置调用提取统计
        self._call_extraction_stats = {
            'total_invocations': 0,
            'with_qualifier': 0,
            'matched_injection': 0
        }
        
        # 构建业务类FQN集合 (用于快速查找)
        business_class_fqns = {cls['fqn'] for cls in classes}
        
        # 构建类FQN到文件的映射
        class_to_file = {cls['fqn']: cls['file_path'] for cls in classes}
        
        # 只处理业务类的文件
        business_files = [Path(cls['file_path']) for cls in classes]
        business_files = list(set(business_files))  # 去重
        
        logger.info(f"  需要扫描 {len(business_files)} 个业务类文件 (共 {len(java_files)} 个文件)")
        
        for idx, java_file in enumerate(business_files, 1):
            if idx % 50 == 0:
                logger.info(f"  第二遍扫描进度: [{idx}/{len(business_files)}]")
            
            try:
                with open(java_file, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
                
                tree = javalang.parse.parse(source_code)
                package_name = tree.package.name if tree.package else ''
                
                # 遍历类
                for path, type_decl in tree.filter(javalang.tree.TypeDeclaration):
                    if not hasattr(type_decl, 'name'):
                        continue
                    
                    class_name = type_decl.name
                    class_fqn = f"{package_name}.{class_name}" if package_name else class_name
                    
                    # 只处理业务类
                    if class_fqn not in business_class_fqns:
                        continue
                    
                    # 检查该类是否有注入字段
                    if class_fqn not in self.injected_fields:
                        continue
                    
                    # 遍历方法
                    if hasattr(type_decl, 'body') and type_decl.body:
                        for body_decl in type_decl.body:
                            if not isinstance(body_decl, javalang.tree.MethodDeclaration):
                                continue
                            
                            method_name = body_decl.name
                            
                            # 提取参数类型
                            param_types = []
                            if body_decl.parameters:
                                for param in body_decl.parameters:
                                    param_type = self._extract_param_type(param)
                                    param_types.append(param_type)
                            
                            caller_method_sig = f"{class_fqn}.{method_name}({','.join(param_types)})"
                            
                            # 提取方法体中的调用及 MQ 发送
                            if body_decl.body:
                                for stmt in body_decl.body:
                                    method_calls, method_mq_senders = self._extract_method_calls_filtered(
                                        stmt, class_fqn, caller_method_sig, source_code=source_code
                                    )
                                    calls.extend(method_calls)
                                    mq_senders.extend(method_mq_senders)
            
            except Exception as e:
                parse_errors += 1
                logger.warning(f"第二遍扫描文件失败 {java_file}")
                logger.warning(f"  错误类型: {type(e).__name__}")
                
                # 尝试获取错误信息
                error_msg = str(e) if str(e) else "无错误描述"
                if hasattr(e, 'description') and e.description:
                    error_msg = f"{e.description}"
                if hasattr(e, 'at') and e.at:
                    try:
                        error_msg += f" (位置: {e.at})"
                    except:
                        pass
                
                logger.warning(f"  错误信息: {error_msg[:500]}")
                
                # JavaSyntaxError 特殊处理
                if type(e).__name__ == 'JavaSyntaxError':
                    logger.warning(f"  可能原因: Java 语法不兼容 (javalang 不支持 Java 14+ 的 switch 表达式等新特性)")
                continue
        
        # 输出统计信息
        logger.info(f"✓ 第二遍扫描完成:")
        logger.info(f"  - 成功: {len(business_files) - parse_errors} 个文件")
        logger.info(f"  - 失败: {parse_errors} 个文件")
        logger.info(f"  - 调用关系: {len(calls)} 个")
        
        # 如果没有找到调用关系,输出调试信息
        if len(calls) == 0:
            logger.warning("  ⚠️ 未找到任何调用关系!")
            logger.warning(f"  - 业务类数量: {len(business_class_fqns)}")
            logger.warning(f"  - 有注入字段的类数量: {len(self.injected_fields)}")
            # 输出前5个有注入字段的类
            sample_classes = list(self.injected_fields.keys())[:5]
            logger.warning(f"  - 有注入字段的类示例: {sample_classes}")
            
            # 检查是否有业务类同时有注入字段
            business_with_injection = [cls for cls in business_class_fqns if cls in self.injected_fields]
            logger.warning(f"  - 业务类中有注入字段的数量: {len(business_with_injection)}")
            if business_with_injection:
                logger.warning(f"  - 示例: {business_with_injection[:3]}")
                # 输出第一个类的注入字段
                first_cls = business_with_injection[0]
                logger.warning(f"  - {first_cls} 的注入字段: {list(self.injected_fields[first_cls].keys())}")
            
            # 输出调用提取统计
            logger.warning(f"  - 调用提取统计:")
            logger.warning(f"    - 总方法调用数: {self._call_extraction_stats['total_invocations']}")
            logger.warning(f"    - 有 qualifier 的调用: {self._call_extraction_stats['with_qualifier']}")
            logger.warning(f"    - 匹配注入字段的调用: {self._call_extraction_stats['matched_injection']}")
        
        return calls, mq_senders
    
    # 用于统计调用提取的调试计数器
    _call_extraction_stats = {
        'total_invocations': 0,
        'with_qualifier': 0,
        'matched_injection': 0
    }
    
    def _extract_method_calls_filtered(
        self,
        node,
        current_class: str,
        current_method_sig: str,
        source_code: Optional[str] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        递归提取方法调用及 MQ 发送。MQ 发送只加入 mq_senders，不加入 calls。
        Returns:
            (calls, mq_senders)
        """
        calls = []
        mq_senders = []
        
        if isinstance(node, javalang.tree.MethodInvocation):
            self._call_extraction_stats['total_invocations'] += 1
            
            qualifier = None
            if node.qualifier:
                # 提取 qualifier (可能是字段名)
                if isinstance(node.qualifier, str):
                    qualifier = node.qualifier
                elif hasattr(node.qualifier, 'member'):
                    # 处理 this.field.method() 的情况
                    qualifier = node.qualifier.member
                elif hasattr(node.qualifier, 'value'):
                    # 处理简单的标识符
                    qualifier = node.qualifier.value
            
            if qualifier:
                self._call_extraction_stats['with_qualifier'] += 1
            
            callee_method = node.member
            
            topic = self._extract_first_argument(node)
            if topic and source_code and isinstance(topic, str) and topic.isupper():
                resolved = self._find_constant_value(topic, source_code)
                if resolved:
                    topic = resolved
            
            if qualifier and current_class in self.injected_fields:
                field_info = self.injected_fields[current_class].get(qualifier)
                if field_info:
                    self._call_extraction_stats['matched_injection'] += 1
                    field_type = (field_info.get('type_fqn') or '').split('.')[-1]
                    is_kafka_send = callee_method == 'send' and (
                        'KafkaProducer' in field_type or 'KafkaTemplate' in field_type
                        or (qualifier and qualifier == 'kafkaProducer')
                    )
                    is_rocket_send = callee_method in ('send', 'sendDelay', 'sendAsync') and (
                        'RocketMQ' in field_type or (qualifier and 'rocketmq' in (qualifier or '').lower())
                    )
                    if is_kafka_send and topic:
                        mq_senders.append({
                            'caller_method': current_method_sig,
                            'topic': topic,
                            'mq_type': 'kafka'
                        })
                    elif is_rocket_send and topic:
                        mq_senders.append({
                            'caller_method': current_method_sig,
                            'topic': topic.split(':')[0] if ':' in str(topic) else topic,
                            'mq_type': 'rocket'
                        })
                    elif not (is_kafka_send or is_rocket_send):
                        calls.append({
                            'caller_class': current_class,
                            'caller_method': current_method_sig,
                            'qualifier': qualifier,
                            'callee_method': callee_method,
                            'injection_type': field_info['annotation'],
                            'target_type_fqn': field_info['type_fqn']
                        })
                else:
                    if callee_method == 'send' and qualifier and qualifier == 'kafkaProducer' and topic:
                        mq_senders.append({
                            'caller_method': current_method_sig,
                            'topic': topic,
                            'mq_type': 'kafka'
                        })
                    elif callee_method in ('send', 'sendDelay') and qualifier and 'rocketmq' in (qualifier or '').lower() and topic:
                        mq_senders.append({
                            'caller_method': current_method_sig,
                            'topic': topic.split(':')[0] if ':' in str(topic) else topic,
                            'mq_type': 'rocket'
                        })
            elif not qualifier or qualifier == 'this':
                # 只记录当前类中真实存在的方法调用
                # 跳过链式调用的中间方法（如 stream().collect()）
                # 通过检查方法名是否是常见的 Java 标准库方法来过滤
                common_stdlib_methods = {
                    'stream', 'collect', 'map', 'filter', 'forEach', 'reduce', 'flatMap',
                    'orElse', 'orElseGet', 'ifPresent', 'isPresent', 'get', 'of', 'empty',
                    'equals', 'hashCode', 'toString', 'clone', 'finalize',
                    'wait', 'notify', 'notifyAll', 'getClass',
                    'findFirst', 'findAny', 'anyMatch', 'allMatch', 'noneMatch',
                    'sorted', 'distinct', 'limit', 'skip', 'peek', 'count',
                    'max', 'min', 'sum', 'average', 'toArray',
                    'join', 'split', 'replace', 'substring', 'trim', 'toLowerCase', 'toUpperCase',
                    'contains', 'startsWith', 'endsWith', 'indexOf', 'lastIndexOf',
                    'add', 'remove', 'clear', 'size', 'isEmpty', 'iterator',
                    'put', 'putAll', 'containsKey', 'containsValue', 'keySet', 'values', 'entrySet',
                    'equalsIgnoreCase', 'compareTo', 'compareToIgnoreCase'
                }
                
                # 如果是常见的标准库方法，跳过
                if callee_method not in common_stdlib_methods:
                    calls.append({
                        'caller_class': current_class,
                        'caller_method': current_method_sig,
                        'qualifier': None,
                        'callee_method': callee_method,
                        'injection_type': 'Internal',
                        'target_type_fqn': current_class
                    })
        
        if hasattr(node, '__dict__'):
            for attr_name, attr_value in node.__dict__.items():
                if attr_name.startswith('_'):
                    continue
                if isinstance(attr_value, list):
                    for item in attr_value:
                        if isinstance(item, javalang.tree.Node):
                            sub_calls, sub_senders = self._extract_method_calls_filtered(
                                item, current_class, current_method_sig, source_code
                            )
                            calls.extend(sub_calls)
                            mq_senders.extend(sub_senders)
                elif isinstance(attr_value, javalang.tree.Node):
                    sub_calls, sub_senders = self._extract_method_calls_filtered(
                        attr_value, current_class, current_method_sig, source_code
                    )
                    calls.extend(sub_calls)
                    mq_senders.extend(sub_senders)
        
        return calls, mq_senders
    
    def _filter_business_classes(self, classes: List[Dict]) -> List[Dict]:
        """
        过滤非业务类
        
        保留条件 (满足任一):
        1. has_injection = true (有注入字段)
        2. 被其他类注入 (在 injected_types 中)
        3. 是 Mapper
        4. 是 Dubbo 接口 (被注入)
        5. 是 Dubbo Service 实现类
        6. 是 Entity (arch_layer = Entity)
        7. 是 *.api 包下的接口 (对外提供的 Dubbo API)
        """
        business_classes = []
        filtered_classes = []
        
        for cls in classes:
            class_fqn = cls['fqn']
            class_name = cls['name']
            
            # 检查是否有注入字段
            has_injection = class_fqn in self.injected_fields
            
            # 检查是否被注入
            is_injected = class_fqn in self.injected_types
            
            # 检查是否为 Mapper
            is_mapper = cls.get('is_mapper', False)
            
            # 检查是否为 Dubbo 接口 (被注入)
            is_dubbo_interface = class_fqn in self.dubbo_interfaces
            
            # 检查是否为 Dubbo Service 实现类
            is_dubbo_service = cls.get('is_dubbo_service', False)
            
            # 检查是否为 Entity
            is_entity = cls.get('arch_layer') == 'Entity'
            
            # 检查是否为 *.api 包下的接口 (对外提供的 Dubbo API)
            is_api_interface = (
                cls.get('is_interface', False) and 
                '.api.' in class_fqn
            )
            
            if has_injection or is_injected or is_mapper or is_dubbo_interface or is_dubbo_service or is_entity or is_api_interface:
                cls['has_injection'] = has_injection
                business_classes.append(cls)
            else:
                filtered_classes.append(class_name)
                logger.debug(f"过滤非业务类: {class_fqn}")
        
        # 输出过滤统计
        if filtered_classes:
            logger.info(f"  过滤的类示例 (前10个): {', '.join(filtered_classes[:10])}")
            if len(filtered_classes) > 10:
                logger.info(f"  ... 还有 {len(filtered_classes) - 10} 个类被过滤")
        
        return business_classes
    
    def _store_to_neo4j(self, project_name: str, project_path: str, scan_result: Dict, commit_id: str = ""):
        """存储到 Neo4j (按照新的图模型)"""
        if not self.client:
            logger.warning("未提供 Neo4j 客户端,跳过存储")
            return
        
        logger.info("开始存储到 Neo4j...")
        
        # 1. 创建 Project 节点
        logger.info("1/10 创建 Project 节点...")
        self._create_repo_node(project_name, project_path, commit_id)
        
        # 2. 创建 Type 节点 (仅业务类,不再创建 Package 节点)
        logger.info(f"2/10 创建 Type 节点 ({len(scan_result['classes'])} 个业务类)...")
        for idx, cls in enumerate(scan_result['classes'], 1):
            self._create_type_node(project_name, cls)
            if idx % 50 == 0:
                logger.info(f"  进度: [{idx}/{len(scan_result['classes'])}]")
        
        # 3. 创建 Method 节点
        logger.info(f"3/10 创建 Method 节点 ({len(scan_result['methods'])} 个)...")
        for idx, method in enumerate(scan_result['methods'], 1):
            self._create_method_node(method)
            if idx % 100 == 0:
                logger.info(f"  进度: [{idx}/{len(scan_result['methods'])}]")
        
        # 4. 创建 Field 节点 (仅注入字段)
        logger.info(f"4/10 创建 Field 节点 ({len(scan_result['fields'])} 个注入字段)...")
        for idx, field in enumerate(scan_result['fields'], 1):
            self._create_field_node(field)
            if idx % 50 == 0:
                logger.info(f"  进度: [{idx}/{len(scan_result['fields'])}]")
        
        # 5. 创建 Table 节点和 MAPPER_FOR_TABLE 边
        logger.info(f"5/10 创建 Table 节点 ({len(scan_result['mapper_tables'])} 个)...")
        for mapper_table in scan_result['mapper_tables']:
            self._create_table_and_mapper_edge(mapper_table)
        
        # 6. 创建 RpcEndpoint 节点和 EXPOSES 边
        logger.info(f"6/10 创建 RpcEndpoint 节点 ({len(scan_result['rpc_endpoints'])} 个)...")
        for endpoint in scan_result['rpc_endpoints']:
            self._create_rpc_endpoint_and_exposes_edge(endpoint)
        
        # 7. 创建 Job 节点和 EXECUTES_JOB 边
        logger.info(f"7/12 创建 Job 节点 ({len(scan_result['jobs'])} 个)...")
        for job in scan_result['jobs']:
            self._create_job_and_executes_edge(job)
        
        # 8. 创建 MQ_TOPIC 节点及 MQ consumer/producer 边
        mq_listeners = scan_result.get('mq_listeners', [])
        mq_senders = scan_result.get('mq_senders', [])
        logger.info(f"8/12 创建 MQ 边 (listeners: {len(mq_listeners)}, senders: {len(mq_senders)})...")
        for listener in mq_listeners:
            self._create_mq_topic_node(listener['topic'], listener['mq_type'])
            self._create_mq_consumer_edges(listener)
        for sender in mq_senders:
            self._create_mq_topic_node(sender['topic'], sender['mq_type'])
            self._create_mq_producer_edges(sender)
        
        # 10. 创建 DUBBO_DEPENDS 边 (Class -> Interface, 类级别依赖)
        logger.info(f"10/12 创建 DUBBO_DEPENDS 边 ({len(scan_result['dubbo_references'])} 个)...")
        for dubbo_ref in scan_result['dubbo_references']:
            self._create_dubbo_depends_edge(dubbo_ref)
        
        # 11. 创建 DUBBO_PROVIDES 边 (Type -> Type)
        logger.info(f"11/12 创建 DUBBO_PROVIDES 边 ({len(scan_result['dubbo_services'])} 个)...")
        for dubbo_svc in scan_result['dubbo_services']:
            self._create_dubbo_provides_edge(dubbo_svc)
        
        # 12. 创建 CALLS/DB_CALL 边 (Method -> Method, 仅注入调用)
        logger.info(f"12/12 创建 CALLS/DB_CALL 边 ({len(scan_result['calls'])} 个)...")
        for idx, call in enumerate(scan_result['calls'], 1):
            call['project_name'] = project_name  # 添加项目名用于判断是否跨项目
            self._create_calls_edge(call)
            if idx % 100 == 0:
                logger.info(f"  进度: [{idx}/{len(scan_result['calls'])}]")
        
        # 13. 创建继承和实现边
        logger.info(f"额外: 创建继承和实现边 ({len(scan_result['classes'])} 个类)...")
        for idx, cls in enumerate(scan_result['classes'], 1):
            self._create_extends_implements_edges(cls)
            if idx % 50 == 0:
                logger.info(f"  进度: [{idx}/{len(scan_result['classes'])}]")
        
        logger.info("✓ 存储到 Neo4j 完成!")
    
    # ==================== 辅助方法 ====================
    
    def _is_injection_annotation(self, ann_name: str) -> bool:
        """判断是否为注入注解"""
        for inj_ann in self.INJECTION_ANNOTATIONS:
            if inj_ann in ann_name:
                return True
        return False
    
    def _normalize_injection_annotation(self, ann_name: str) -> str:
        """规范化注入注解名称"""
        if 'DubboReference' in ann_name:
            return 'DubboReference'
        elif 'Reference' in ann_name:
            return 'Reference'
        elif 'Resource' in ann_name:
            return 'Resource'
        elif 'Autowired' in ann_name:
            return 'Autowired'
        return ann_name
    
    def _is_mapper_interface(
        self, 
        type_decl, 
        class_name: str, 
        package_name: str,
        source_code: str
    ) -> bool:
        """判断是否为 Mapper 接口"""
        # 1. 有 @Mapper 注解
        if hasattr(type_decl, 'annotations') and type_decl.annotations:
            for ann in type_decl.annotations:
                ann_name = self._extract_annotation_name(ann)
                if ann_name == 'Mapper' or ann_name.endswith('.Mapper'):
                    return True
        
        # 2. 接口名以 Mapper 结尾
        if isinstance(type_decl, javalang.tree.InterfaceDeclaration):
            if class_name.endswith('Mapper'):
                return True
            
            # 3. 包名含 mapper
            if 'mapper' in package_name.lower():
                return True
        
        return False
    
    def _infer_arch_layer(
        self,
        class_name: str,
        package_name: str,
        annotations: List[Dict],
        is_mapper: bool,
        is_dubbo_service: bool,
        implements: List[str]
    ) -> str:
        """推断架构层次"""
        # Mapper
        if is_mapper:
            return 'Mapper'
        
        # Controller
        ann_names = [a['name'] for a in annotations]
        if any(a in ann_names for a in ['Controller', 'RestController']):
            return 'Controller'
        if is_dubbo_service:
            # Dubbo 服务实现类,检查是否实现 RemoteService
            if any('RemoteService' in impl for impl in implements):
                return 'Controller'
        
        # Service
        if 'Service' in ann_names and not is_dubbo_service:
            return 'Service'
        if 'service' in package_name.lower() and 'impl' not in package_name.lower():
            return 'Service'
        
        # Manager
        if class_name.endswith('Manager'):
            return 'Manager'
        if 'manager' in package_name.lower():
            return 'Manager'
        
        # DAO
        if any(a in ann_names for a in ['Repository']):
            return 'DAO'
        if 'dao' in package_name.lower():
            return 'DAO'
        
        # Entity
        if 'Entity' in ann_names:
            return 'Entity'
        if 'entity' in package_name.lower() or 'domain' in package_name.lower():
            return 'Entity'
        
        # Helper/Util
        if class_name.endswith('Helper') or class_name.endswith('Util'):
            return 'Helper'
        
        return 'Other'
    
    def _extract_annotation_name(self, ann) -> str:
        """提取注解名称"""
        if hasattr(ann, 'name'):
            if isinstance(ann.name, list):
                return '.'.join(ann.name)
            else:
                return str(ann.name)
        return ''
    
    def _extract_type_name(self, type_ref) -> Optional[str]:
        """提取类型名称（处理嵌套的 ReferenceType）"""
        if not type_ref:
            return None
        
        # 处理 ReferenceType 的嵌套结构
        if isinstance(type_ref, javalang.tree.ReferenceType):
            parts = []
            current = type_ref
            while current:
                if hasattr(current, 'name'):
                    if isinstance(current.name, list):
                        parts.extend(current.name)
                    else:
                        parts.append(str(current.name))
                
                # 继续处理 sub_type
                if hasattr(current, 'sub_type') and current.sub_type:
                    current = current.sub_type
                else:
                    break
            
            return '.'.join(parts) if parts else None
        
        # 其他类型
        if hasattr(type_ref, 'name'):
            if isinstance(type_ref.name, list):
                return '.'.join(type_ref.name)
            else:
                return str(type_ref.name)
        
        return None
    
    def _extract_field_type(self, field_decl) -> str:
        """提取字段类型"""
        if field_decl.type:
            if isinstance(field_decl.type, javalang.tree.BasicType):
                return field_decl.type.name
            elif hasattr(field_decl.type, 'name'):
                if isinstance(field_decl.type.name, list):
                    return '.'.join(field_decl.type.name)
                else:
                    return str(field_decl.type.name)
        return 'Object'
    
    def _extract_return_type(self, method_decl) -> str:
        """提取返回类型"""
        if method_decl.return_type:
            if isinstance(method_decl.return_type, javalang.tree.BasicType):
                return method_decl.return_type.name
            elif hasattr(method_decl.return_type, 'name'):
                if isinstance(method_decl.return_type.name, list):
                    return '.'.join(method_decl.return_type.name)
                else:
                    return str(method_decl.return_type.name)
        return 'void'
    
    def _extract_parameters(self, method_decl) -> List[Dict]:
        """提取方法参数"""
        parameters = []
        if method_decl.parameters:
            for i, param in enumerate(method_decl.parameters):
                param_type = self._extract_param_type(param)
                parameters.append({
                    'type': param_type,
                    'name': param.name,
                    'position': i
                })
        return parameters
    
    def _extract_param_type(self, param) -> str:
        """提取参数类型"""
        if param.type:
            if isinstance(param.type, javalang.tree.BasicType):
                return param.type.name
            elif hasattr(param.type, 'name'):
                if isinstance(param.type.name, list):
                    return '.'.join(param.type.name)
                else:
                    return str(param.type.name)
        return 'Object'
    
    def _extract_visibility(self, modifiers: List[str]) -> str:
        """提取可见性"""
        if "public" in modifiers:
            return "PUBLIC"
        elif "protected" in modifiers:
            return "PROTECTED"
        elif "private" in modifiers:
            return "PRIVATE"
        else:
            return "PACKAGE"
    
    def _resolve_type_fqn(self, type_name: str, imports: Dict[str, str], package_name: str) -> Optional[str]:
        """
        解析类型的完全限定名
        
        优先级:
        0. 如果已经是 FQN (包含 '.')，直接返回
        1. 基本类型
        2. java.lang 包
        3. 显式 import (import com.example.ClassName)
        4. 同包类 (优先于通配符 import)
        5. 通配符 import (import com.example.*)
        """
        # 0. 如果已经是 FQN (包含 '.')，直接返回
        if '.' in type_name:
            return type_name
        
        # 1. 基本类型
        if type_name in ['int', 'long', 'short', 'byte', 'float', 'double', 'boolean', 'char', 'void']:
            return type_name
        
        # 2. java.lang 包
        if type_name in ['String', 'Object', 'Integer', 'Long', 'Boolean', 'Double', 'Float', 'Byte', 'Short', 'Character']:
            return f"java.lang.{type_name}"
        
        # 3. 显式 import - 最高优先级
        if type_name in imports:
            return imports[type_name]
        
        # 4. 同包类 - 优先于通配符 import
        # 根据 Java 规范，同包类不需要 import，优先级高于通配符 import
        if package_name:
            return f"{package_name}.{type_name}"
        
        # 5. 通配符 import - 最低优先级
        # 遍历所有通配符 import，尝试匹配
        for key, value in imports.items():
            if key.startswith('*:'):
                # 提取包名: "*:com.example" -> "com.example"
                wildcard_package = key[2:]
                # 返回第一个匹配的通配符 import
                return f"{wildcard_package}.{type_name}"
        
        return type_name
    
    def _infer_table_name_from_mapper(
        self, 
        mapper_fqn: str, 
        source_code: str,
        imports: Dict[str, str],
        package_name: str
    ) -> Optional[str]:
        """从 Mapper 接口推断表名"""
        # 简单实现: 从类名推断
        # 如: UserMapper -> user, ChatroomNobleMapper -> chatroom_noble
        class_name = mapper_fqn.split('.')[-1]
        if class_name.endswith('Mapper'):
            entity_name = class_name[:-6]  # 去掉 Mapper
            # 驼峰转下划线
            table_name = self._camel_to_snake(entity_name)
            return table_name
        return None
    
    def _camel_to_snake(self, name: str) -> str:
        """驼峰转下划线"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _extract_rpc_path(self, ann, ann_name: str) -> Optional[str]:
        """提取 RPC 路径"""
        if not hasattr(ann, 'element') or not ann.element:
            return None
        
        # 情况1: element 是 Literal (如 @MobileAPI("/path"))
        if isinstance(ann.element, javalang.tree.Literal):
            return ann.element.value.strip('"')
        
        # 情况2: element 是 ElementValuePair 列表 (如 @MobileAPI(path = "/path"))
        if isinstance(ann.element, list):
            for elem in ann.element:
                if hasattr(elem, 'name') and elem.name in ('path', 'value'):
                    if hasattr(elem, 'value') and isinstance(elem.value, javalang.tree.Literal):
                        return elem.value.value.strip('"')
        
        # 情况3: element 是单个 ElementValuePair (如 @RequestMapping(path = "/path"))
        if hasattr(ann.element, 'name') and ann.element.name in ('path', 'value'):
            if hasattr(ann.element, 'value') and isinstance(ann.element.value, javalang.tree.Literal):
                return ann.element.value.value.strip('"')
        
        return None
    
    def _infer_http_method(self, ann_name: str) -> str:
        """推断 HTTP 方法"""
        if 'Post' in ann_name:
            return 'POST'
        elif 'Get' in ann_name:
            return 'GET'
        elif 'Put' in ann_name:
            return 'PUT'
        elif 'Delete' in ann_name:
            return 'DELETE'
        elif 'Patch' in ann_name:
            return 'PATCH'
        return 'POST'
    
    def _extract_cron_expr(self, ann) -> Optional[str]:
        """提取 cron 表达式"""
        # 简化实现
        if hasattr(ann, 'element'):
            if isinstance(ann.element, javalang.tree.Literal):
                return ann.element.value.strip('"')
        return None
    
    def _extract_mq_listener_info(self, ann, ann_name: str, source_code: str) -> Optional[Dict]:
        """
        提取 MQ 监听器信息
        
        Returns:
            {
                'topics': [str],  # topic 列表
                'mq_type': str,   # 'kafka', 'rocketmq', 'rabbit'
                'group': str      # consumer group
            }
        """
        import re
        
        mq_type = None
        if 'Kafka' in ann_name:
            mq_type = 'kafka'
        elif 'RocketMQ' in ann_name:
            mq_type = 'rocketmq'
        elif 'Rabbit' in ann_name:
            mq_type = 'rabbit'
        
        topics = []
        group = None
        
        # 尝试从 AST 提取
        if hasattr(ann, 'element'):
            # 单个参数的情况 (topics = "xxx" 或 topic = "xxx")
            if isinstance(ann.element, javalang.tree.Literal):
                topic_value = ann.element.value.strip('"')
                topics.append(topic_value)
            # 多个参数的情况 (topics = {...}, groupId = "xxx")
            elif isinstance(ann.element, list):
                for elem in ann.element:
                    if hasattr(elem, 'name') and hasattr(elem, 'value'):
                        elem_name = elem.name
                        if elem_name in ['topics', 'topic']:
                            if isinstance(elem.value, javalang.tree.Literal):
                                topics.append(elem.value.value.strip('"'))
                            elif isinstance(elem.value, javalang.tree.MemberReference):
                                # 常量引用，如 TOPIC_LOTTERY_STAR_BOX
                                const_name = elem.value.member
                                # 从源码中查找常量值
                                topic_value = self._find_constant_value(const_name, source_code)
                                if topic_value:
                                    topics.append(topic_value)
                                else:
                                    topics.append(const_name)  # 使用常量名
                        elif elem_name in ['groupId', 'consumerGroup']:
                            if isinstance(elem.value, javalang.tree.Literal):
                                group = elem.value.value.strip('"')
                            elif isinstance(elem.value, javalang.tree.MemberReference):
                                const_name = elem.value.member
                                group_value = self._find_constant_value(const_name, source_code)
                                if group_value:
                                    group = group_value
                                else:
                                    group = const_name
        
        # 正则兜底 - 从源码中提取
        if not topics:
            if mq_type == 'kafka':
                # @KafkaListener(topics = TOPIC_XXX, groupId = GROUP_XXX)
                match = re.search(r'@KafkaListener\s*\(\s*topics\s*=\s*([A-Z_]+)', source_code)
                if match:
                    const_name = match.group(1)
                    topic_value = self._find_constant_value(const_name, source_code)
                    topics.append(topic_value or const_name)
            elif mq_type == 'rocketmq':
                # @RocketMQMessageListener(topic = TOPIC_XXX, consumerGroup = "xxx")
                match = re.search(r'@RocketMQMessageListener\s*\(\s*topic\s*=\s*([A-Z_]+)', source_code)
                if not match:
                    match = re.search(r'@RocketMQMessageListener\s*\(\s*topic\s*=\s*"([^"]+)"', source_code)
                if match:
                    topic_or_const = match.group(1)
                    if topic_or_const.isupper():
                        topic_value = self._find_constant_value(topic_or_const, source_code)
                        topics.append(topic_value or topic_or_const)
                    else:
                        topics.append(topic_or_const)
        
        if not group and mq_type in ['kafka', 'rocketmq']:
            group_pattern = r'(groupId|consumerGroup)\s*=\s*"([^"]+)"'
            match = re.search(group_pattern, source_code)
            if match:
                group = match.group(2)
        
        if not topics:
            return None
        
        return {
            'topics': topics,
            'mq_type': mq_type,
            'group': group
        }
    
    def _find_constant_value(self, const_name: str, source_code: str) -> Optional[str]:
        """从源码中查找常量值"""
        # 查找 public static final String CONST_NAME = "value";
        pattern = rf'(?:public\s+)?(?:static\s+)?(?:final\s+)?String\s+{const_name}\s*=\s*"([^"]+)"'
        match = re.search(pattern, source_code)
        if match:
            return match.group(1)
        return None
    
    def _extract_first_argument(self, method_invocation_node) -> Optional[str]:
        """
        提取方法调用的第一个参数
        用于提取 MQ 发送的 topic
        
        Returns:
            topic 字符串或常量名
        """
        if not hasattr(method_invocation_node, 'arguments') or not method_invocation_node.arguments:
            return None
        
        first_arg = method_invocation_node.arguments[0]
        
        # 字符串字面量
        if isinstance(first_arg, javalang.tree.Literal):
            return first_arg.value.strip('"')
        
        # 常量引用 (如 TOPIC_LOTTERY_STAR_BOX)
        if isinstance(first_arg, javalang.tree.MemberReference):
            return first_arg.member
        
        # 其他情况返回 None
        return None
    
    def _extract_kafka_listener_info(
        self, method_decl, annotation, source_code: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        提取 Kafka 监听注解中的 topic 和 groupId。
        先尝试 AST 注解参数，失败时用正则从源码提取。(ported from scanner.py)
        Returns:
            (topic, group_id)
        """
        topic = None
        group_id = None
        if hasattr(annotation, 'arguments') and annotation.arguments:
            for arg in annotation.arguments:
                if hasattr(arg, 'name') and arg.name == 'topics':
                    if hasattr(arg, 'value'):
                        if isinstance(arg.value, list) and arg.value:
                            topic = str(arg.value[0])
                        else:
                            topic = str(arg.value)
                elif hasattr(arg, 'name') and arg.name == 'groupId':
                    if hasattr(arg, 'value'):
                        group_id = str(arg.value)
        if not topic:
            pattern = r'@KafkaListener\s*\([^)]*topics\s*=\s*["\']?([^"\'\),]+)["\']?'
            match = re.search(pattern, source_code)
            if match:
                topic = match.group(1).strip()
            pattern = r'groupId\s*=\s*["\']?([^"\'\),]+)["\']?'
            match = re.search(pattern, source_code)
            if match:
                group_id = match.group(1).strip()
        return topic, group_id
    
    def _extract_rocketmq_listener_info(
        self, method_decl, annotation, source_code: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        提取 RocketMQ 监听注解中的 topic 和 consumerGroup。(ported from scanner.py)
        Returns:
            (topic, consumer_group)
        """
        topic = None
        consumer_group = None
        if hasattr(annotation, 'arguments') and annotation.arguments:
            for arg in annotation.arguments:
                if hasattr(arg, 'name') and arg.name == 'topic':
                    if hasattr(arg, 'value'):
                        topic = str(arg.value)
                elif hasattr(arg, 'name') and arg.name in ('consumerGroup', 'consumer_group'):
                    if hasattr(arg, 'value'):
                        consumer_group = str(arg.value)
        if not topic:
            pattern = r'@RocketMQMessageListener\s*\([^)]*topic\s*=\s*["\']?([^"\'\),]+)["\']?'
            match = re.search(pattern, source_code)
            if match:
                topic = match.group(1).strip()
            pattern = r'consumerGroup\s*=\s*["\']?([^"\'\),]+)["\']?'
            match = re.search(pattern, source_code)
            if match:
                consumer_group = match.group(1).strip()
        return topic, consumer_group
    
    # ==================== Neo4j 存储方法 ====================
    
    def _create_repo_node(self, project_name: str, project_path: str, commit_id: str = ""):
        """创建 Project 节点 (保持与后端 API 兼容)"""
        params = {
            'name': project_name,
            'path': project_path,
            'commit_id': commit_id
        }
        self.client.execute_write("""
            MERGE (p:Project {name: $name})
            SET p.path = $path,
                p.scanned_at = datetime(),
                p.scanned_commit_id = $commit_id
        """, params)
    
    def _create_package_node(self, project_name: str, package_name: str):
        """创建 Package 节点 (已废弃: 直接使用 Type.package 属性)"""
        # 不再创建 Package 节点,改为在 Type 节点上存储 package 属性
        # 如果需要按包查询: WHERE t.package = 'xxx' 或 WHERE t.package STARTS WITH 'xxx'
        pass
    
    def _create_type_node(self, project_name: str, cls: Dict):
        """创建 Class/Interface/MAPPER/ARIES_JOB 节点 (直接关联到 Project,不使用 Package 节点)"""
        # 根据 kind 决定节点标签
        node_label = cls['kind']  # 'CLASS', 'INTERFACE', 'MAPPER', 'ARIES_JOB'
        
        # 如果是 Mapper，使用 MAPPER 标签
        if cls.get('is_mapper'):
            node_label = 'MAPPER'
        
        # 使用动态标签创建节点
        query = f"""
            MATCH (p:Project {{name: $project_name}})
            MERGE (t:{node_label} {{fqn: $fqn}})
            SET t.name = $name,
                t.arch_layer = $arch_layer,
                t.has_injection = $has_injection,
                t.file_path = $file_path,
                t.package = $package,
                t.visibility = $visibility,
                t.is_dubbo_service = $is_dubbo_service,
                t.is_mapper = $is_mapper,
                t.is_aries_job = $is_aries_job
            MERGE (p)-[:CONTAINS]->(t)
        """
        
        self.client.execute_write(query, {
            'project_name': project_name,
            'fqn': cls['fqn'],
            'name': cls['name'],
            'arch_layer': cls['arch_layer'],
            'has_injection': cls.get('has_injection', False),
            'file_path': cls['file_path'],
            'package': cls['package'],
            'visibility': cls['visibility'],
            'is_dubbo_service': cls.get('is_dubbo_service', False),
            'is_mapper': cls.get('is_mapper', False),
            'is_aries_job': cls.get('is_aries_job', False)
        })
    
    def _create_method_node(self, method: Dict):
        """创建 Method 节点"""
        # 序列化注解为 JSON 字符串
        import json
        annotations_json = json.dumps(method.get('annotations', []))
        
        self.client.execute_write("""
            MATCH (t) WHERE (t:CLASS OR t:INTERFACE OR t:MAPPER OR t:ARIES_JOB) AND t.fqn = $class_fqn
            MERGE (m:Method {signature: $signature})
            SET m.name = $name,
                m.class_fqn = $class_fqn,
                m.return_type = $return_type,
                m.is_entry = $is_entry,
                m.line_start = $line_start,
                m.line_end = $line_end,
                m.visibility = $visibility,
                m.annotations = $annotations
            MERGE (t)-[:DECLARES]->(m)
        """, {
            'class_fqn': method['class_fqn'],
            'signature': method['signature'],
            'name': method['name'],
            'return_type': method['return_type'],
            'is_entry': method.get('is_entry', False),
            'line_start': method['line_start'],
            'line_end': method['line_end'],
            'visibility': method['visibility'],
            'annotations': annotations_json
        })
    
    def _create_field_node(self, field: Dict):
        """创建 Field 节点 (仅注入字段) 和 HAS_FIELD 关系"""
        self.client.execute_write("""
            MATCH (t) WHERE (t:CLASS OR t:INTERFACE OR t:MAPPER OR t:ARIES_JOB) AND t.fqn = $class_fqn
            MERGE (f:Field {signature: $signature})
            SET f.name = $name,
                f.type_fqn = $type_fqn,
                f.class_fqn = $class_fqn,
                f.injection_type = $injection_type
            MERGE (t)-[:DECLARES]->(f)
            MERGE (t)-[r:HAS_FIELD {name: $name}]->(f)
            SET r.type_fqn = $type_fqn,
                r.injection_type = $injection_type
        """, {
            'class_fqn': field['class_fqn'],
            'signature': field['signature'],
            'name': field['name'],
            'type_fqn': field['type_fqn'],
            'injection_type': field['injection_type']
        })
    
    def _create_table_and_mapper_edge(self, mapper_table: Dict):
        """创建 Table 节点和 MAPPER_FOR_TABLE 边"""
        self.client.execute_write("""
            MATCH (mapper) WHERE (mapper:CLASS OR mapper:INTERFACE OR mapper:MAPPER OR mapper:ARIES_JOB) AND mapper.fqn = $mapper_fqn
            MERGE (table:Table {name: $table_name})
            MERGE (mapper)-[:MAPPER_FOR_TABLE]->(table)
        """, {
            'mapper_fqn': mapper_table['mapper_fqn'],
            'table_name': mapper_table['table_name']
        })
    
    def _create_rpc_endpoint_and_exposes_edge(self, endpoint: Dict):
        """创建 RpcEndpoint 节点和 EXPOSES 边"""
        endpoint_id = f"{endpoint['path']}#{endpoint['method_signature'].split('.')[-1]}"
        self.client.execute_write("""
            MATCH (m:Method {signature: $method_signature})
            MERGE (ep:RpcEndpoint {id: $endpoint_id})
            SET ep.path = $path,
                ep.http_method = $http_method,
                ep.service_name = $service_name
            MERGE (m)-[:EXPOSES]->(ep)
        """, {
            'method_signature': endpoint['method_signature'],
            'endpoint_id': endpoint_id,
            'path': endpoint['path'],
            'http_method': endpoint['http_method'],
            'service_name': endpoint['service_name']
        })
    
    def _create_job_and_executes_edge(self, job: Dict):
        """创建 Job 节点和 EXECUTES_JOB 边"""
        self.client.execute_write("""
            MATCH (m:Method {signature: $method_signature})
            MERGE (j:Job {fqn: $fqn})
            SET j.name = $name,
                j.job_type = $job_type,
                j.cron_expr = $cron_expr,
                j.class_fqn = $class_fqn
            MERGE (m)-[:EXECUTES_JOB]->(j)
        """, {
            'method_signature': job['method_signature'],
            'fqn': job['fqn'],
            'name': job['name'],
            'job_type': job['job_type'],
            'cron_expr': job.get('cron_expr'),
            'class_fqn': job['class_fqn']
        })
    
    def _create_mq_topic_node(self, topic_name: str, mq_type: str):
        """创建或合并 MQ_TOPIC 节点 (name + mq_type 唯一)."""
        self.client.execute_write("""
            MERGE (t:MQ_TOPIC {name: $name, mq_type: $mq_type})
            ON CREATE SET t.name = $name, t.mq_type = $mq_type
        """, {'name': topic_name, 'mq_type': mq_type})
    
    def _create_mq_consumer_edges(self, listener: Dict):
        """
        创建 Class -[:MQ_KAFKA_CONSUMER|MQ_ROCKET_CONSUMER]-> MQ_TOPIC 及
        MQ_TOPIC -[:MQ_CONSUMES_METHOD]-> Method。
        listener: { topic, mq_type, class_fqn, method_signature, group_id? }
        """
        mq_type = listener.get('mq_type') or 'kafka'
        if mq_type == 'rocketmq':
            mq_type = 'rocket'
        topic = listener['topic']
        class_fqn = listener['class_fqn']
        method_signature = listener['method_signature']
        group = listener.get('group_id') or listener.get('group')
        consumer_edge = 'MQ_KAFKA_CONSUMER' if mq_type == 'kafka' else 'MQ_ROCKET_CONSUMER'
        self.client.execute_write(f"""
            MERGE (t:MQ_TOPIC {{name: $topic, mq_type: $mq_type}})
            ON CREATE SET t.group = $group
            WITH t
            MATCH (cls) WHERE (cls:CLASS OR cls:INTERFACE OR cls:MAPPER OR cls:ARIES_JOB) AND cls.fqn = $class_fqn
            MERGE (cls)-[r:{consumer_edge}]->(t)
            SET r.group = $group
            WITH t
            MATCH (m:Method {{signature: $method_signature}})
            MERGE (t)-[:MQ_CONSUMES_METHOD]->(m)
        """, {
            'topic': topic,
            'mq_type': mq_type,
            'class_fqn': class_fqn,
            'method_signature': method_signature,
            'group': group
        })
    
    def _create_mq_producer_edges(self, sender: Dict):
        """
        创建 Method -[:MQ_KAFKA_PRODUCER|MQ_ROCKET_PRODUCER]-> MQ_TOPIC。
        sender: { caller_method, topic, mq_type }
        """
        mq_type = sender.get('mq_type') or 'kafka'
        topic = sender['topic']
        caller_method = sender['caller_method']
        producer_edge = 'MQ_KAFKA_PRODUCER' if mq_type == 'kafka' else 'MQ_ROCKET_PRODUCER'
        self.client.execute_write(f"""
            MERGE (t:MQ_TOPIC {{name: $topic, mq_type: $mq_type}})
            WITH t
            MATCH (m:Method {{signature: $caller_method}})
            MERGE (m)-[:{producer_edge}]->(t)
        """, {
            'topic': topic,
            'mq_type': mq_type,
            'caller_method': caller_method
        })
    
    def _create_mq_listener_edges(self, mq_listener: Dict):
        """
        创建 MQ 监听器相关的节点和边 (兼容旧调用).
        结构: Class -[:MQ_*_CONSUMER]-> MQ_TOPIC, MQ_TOPIC -[:MQ_CONSUMES_METHOD]-> Method
        """
        self._create_mq_topic_node(mq_listener['topic'], mq_listener.get('mq_type') or 'kafka')
        self._create_mq_consumer_edges(mq_listener)
    
    def _create_dubbo_depends_edge(self, dubbo_ref: Dict):
        """创建 DUBBO_DEPENDS 边 (Class/Interface/Mapper/ARIES_JOB -> Interface) - 类级别依赖"""
        self.client.execute_write("""
            MATCH (caller) WHERE (caller:CLASS OR caller:INTERFACE OR caller:MAPPER OR caller:ARIES_JOB) AND caller.fqn = $class_fqn
            MATCH (service) WHERE (service:CLASS OR service:INTERFACE OR service:MAPPER OR service:ARIES_JOB) AND service.fqn = $service_interface
            MERGE (caller)-[r:DUBBO_DEPENDS]->(service)
            SET r.field_name = $field_name
        """, {
            'class_fqn': dubbo_ref['class_fqn'],
            'service_interface': dubbo_ref['service_interface'],
            'field_name': dubbo_ref['field_name']
        })
    
    def _create_dubbo_provides_edge(self, dubbo_svc: Dict):
        """创建 DUBBO_PROVIDES 边 (Class -> Interface)"""
        for interface_fqn in dubbo_svc['interfaces']:
            self.client.execute_write("""
                MATCH (impl) WHERE (impl:CLASS OR impl:INTERFACE OR impl:MAPPER OR impl:ARIES_JOB) AND impl.fqn = $class_fqn
                MATCH (iface) WHERE (iface:CLASS OR iface:INTERFACE OR iface:MAPPER OR iface:ARIES_JOB) AND iface.fqn = $interface_fqn
                MERGE (impl)-[:DUBBO_PROVIDES]->(iface)
            """, {
                'class_fqn': dubbo_svc['class_fqn'],
                'interface_fqn': interface_fqn
            })
    
    def _create_calls_edge(self, call: Dict):
        """创建 CALLS/DB_CALL 边 (Method -> Method) 或 MQ_PRODUCER 边 (Method -> MQ_TOPIC)"""
        injection_type = call['injection_type']
        project_name = call.get('project_name')  # 调用方所属项目
        
        # 处理 MQ 生产者调用
        if call.get('is_mq_producer') and call.get('mq_topic'):
            topic = call['mq_topic']
            mq_type = call.get('mq_type', 'unknown')
            caller_method = call['caller_method']
            
            # 创建 Method --MQ_KAFKA_PRODUCER/MQ_ROCKET_PRODUCER--> MQ_TOPIC
            self.client.execute_write(f"""
                MATCH (m:Method {{signature: $caller_method}})
                MERGE (topic:MQ_TOPIC {{name: $topic, mq_type: $mq_type}})
                MERGE (m)-[r:{injection_type}]->(topic)
                SET r.via_field = $via_field
            """, {
                'caller_method': caller_method,
                'topic': topic,
                'mq_type': mq_type,
                'via_field': call.get('qualifier')
            })
            return
        
        # 所有类型的调用都创建关系 (CALLS 或 DB_CALL)
        if injection_type in ['Reference', 'DubboReference', 'Resource', 'Autowired', 'Internal']:
            # 内部调用或注入字段调用: Method -> Method
            # 优先匹配已存在的方法节点 (通过 class_fqn + name)
            # 如果找不到，再创建简化签名的方法节点
            self.client.execute_write("""
                MATCH (caller:Method {signature: $caller_method})
                
                // 先尝试匹配已存在的方法 (通过 class_fqn + name，排除简化签名)
                OPTIONAL MATCH (existing_callee:Method)
                WHERE existing_callee.class_fqn = $callee_class 
                  AND existing_callee.name = $callee_name
                  AND existing_callee.signature <> '...'
                  AND NOT existing_callee.signature ENDS WITH '(...)'
                
                // 如果找到已存在的方法，使用它；否则创建简化签名的方法并建立 DECLARES 关系
                WITH caller, existing_callee
                FOREACH (ignoreMe IN CASE WHEN existing_callee IS NULL THEN [1] ELSE [] END |
                    MERGE (new_callee:Method {signature: $callee_signature})
                    SET new_callee.name = $callee_name,
                        new_callee.class_fqn = $callee_class
                )
                
                // 为新创建的简化签名方法建立 DECLARES 关系
                WITH caller, existing_callee
                OPTIONAL MATCH (new_callee:Method {signature: $callee_signature})
                WHERE existing_callee IS NULL
                WITH caller, existing_callee, new_callee
                FOREACH (ignoreMe IN CASE WHEN new_callee IS NOT NULL THEN [1] ELSE [] END |
                    // 先检查是否已存在同 FQN 的 CLASS/MAPPER 节点
                    MERGE (callee_class_or_iface {fqn: $callee_class})
                    ON CREATE SET callee_class_or_iface:INTERFACE,
                                  callee_class_or_iface.name = split($callee_class, '.')[-1],
                                  callee_class_or_iface.is_external = true
                    MERGE (callee_class_or_iface)-[:DECLARES]->(new_callee)
                )
                
                // 获取最终的 callee 和其所属类及项目
                WITH caller, existing_callee
                OPTIONAL MATCH (fallback_callee:Method {signature: $callee_signature})
                WITH caller, COALESCE(existing_callee, fallback_callee) as callee
                OPTIONAL MATCH (callee_class)-[:DECLARES]->(callee)
                OPTIONAL MATCH (callee_project:Project)-[:CONTAINS]->(callee_class)
                
                // 判断 call_type: 
                // 1. 如果是 Reference/DubboReference 且跨项目 -> DubboReference
                // 2. 如果是 Reference/DubboReference 但同项目 -> Internal
                // 3. 其他保持原样
                WITH caller, callee, callee_class, callee_project,
                     CASE 
                         WHEN $call_type IN ['Reference', 'DubboReference'] AND (callee_project.name <> $project_name OR callee_project IS NULL)
                         THEN $call_type
                         WHEN $call_type IN ['Reference', 'DubboReference'] AND callee_project.name = $project_name
                         THEN 'Internal'
                         ELSE $call_type
                     END as final_call_type
                
                // 根据目标类和调用类型决定关系类型 (只创建一条边)
                WITH caller, callee, final_call_type, callee_class,
                     CASE 
                         WHEN callee_class.is_mapper = true THEN 'DB_CALL'
                         WHEN final_call_type IN ['Reference', 'DubboReference'] THEN 'DUBBO_CALLS'
                         ELSE 'CALLS'
                     END as rel_type
                
                // 根据 rel_type 创建对应的边
                FOREACH (ignoreMe IN CASE WHEN rel_type = 'DB_CALL' THEN [1] ELSE [] END |
                    MERGE (caller)-[r:DB_CALL]->(callee)
                    SET r.via_field = $via_field,
                        r.call_type = final_call_type
                )
                FOREACH (ignoreMe IN CASE WHEN rel_type = 'DUBBO_CALLS' THEN [1] ELSE [] END |
                    MERGE (caller)-[r:DUBBO_CALLS]->(callee)
                    SET r.via_field = $via_field,
                        r.call_type = final_call_type
                )
                FOREACH (ignoreMe IN CASE WHEN rel_type = 'CALLS' THEN [1] ELSE [] END |
                    MERGE (caller)-[r:CALLS]->(callee)
                    SET r.via_field = $via_field,
                        r.call_type = final_call_type
                )
            """, {
                'caller_method': call['caller_method'],
                'callee_signature': f"{call['target_type_fqn']}.{call['callee_method']}(...)",
                'callee_name': call['callee_method'],
                'callee_class': call['target_type_fqn'],
                'via_field': call.get('qualifier'),
                'call_type': injection_type,
                'project_name': project_name
            })
    
    def _create_extends_implements_edges(self, cls: Dict):
        """创建继承和实现边"""
        # EXTENDS
        for parent_fqn in cls.get('extends', []):
            if parent_fqn:
                self.client.execute_write("""
                    MATCH (child) WHERE (child:CLASS OR child:INTERFACE OR child:MAPPER OR child:ARIES_JOB) AND child.fqn = $child_fqn
                    MERGE (parent:CLASS {fqn: $parent_fqn})
                    MERGE (child)-[:EXTENDS]->(parent)
                """, {
                    'child_fqn': cls['fqn'],
                    'parent_fqn': parent_fqn
                })
        
        # IMPLEMENTS
        for interface_fqn in cls.get('implements', []):
            if interface_fqn:
                self.client.execute_write("""
                    MATCH (impl) WHERE (impl:CLASS OR impl:INTERFACE OR impl:MAPPER OR impl:ARIES_JOB) AND impl.fqn = $impl_fqn
                    // 先检查是否已存在同 FQN 的节点，避免创建重复的 INTERFACE
                    MERGE (iface {fqn: $interface_fqn})
                    ON CREATE SET iface:INTERFACE
                    MERGE (impl)-[:IMPLEMENTS]->(iface)
                """, {
                    'impl_fqn': cls['fqn'],
                    'interface_fqn': interface_fqn
                })
    
    def _should_generate_report(self) -> bool:
        """检查是否应该生成扫描报告"""
        import os
        generate_report = os.getenv('GENERATE_SCAN_REPORT', 'false').lower()
        return generate_report in ('true', '1', 'yes', 'on')
    
    def _generate_scan_report(
        self,
        project_name: str,
        project_path: str,
        scan_result: Dict
    ) -> str:
        """
        生成扫描分类报告
        
        按照 project -> module -> package -> class 的层级结构组织
        
        Args:
            project_name: 项目名称
            project_path: 项目路径
            scan_result: 扫描结果
        
        Returns:
            报告文件路径
        """
        import json
        from datetime import datetime
        from collections import defaultdict
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 创建报告目录
        report_dir = Path(project_path).parent / "scan_reports"
        report_dir.mkdir(exist_ok=True)
        
        # 报告文件名
        report_filename = f"{project_name}_{timestamp}.json"
        report_path = report_dir / report_filename
        
        # 组织数据结构: project -> module -> package -> classes
        project_structure = {
            "project_name": project_name,
            "project_path": project_path,
            "scan_time": datetime.now().isoformat(),
            "total_classes": len(scan_result['classes']),
            "total_methods": len(scan_result['methods']),
            "modules": {}
        }
        
        # 按 module 和 package 分组
        for cls in scan_result['classes']:
            file_path = cls.get('file_path', '')
            package = cls.get('package', '')
            class_name = cls.get('name', '')
            class_fqn = cls.get('fqn', '')
            kind = cls.get('kind', 'CLASS')
            
            # 提取 module 名称（从文件路径中提取）
            # 例如: D:\cursor\code-ast-graph\git-repos\official-room-pro-web\official-web-api\src\main\java\...
            module = self._extract_module_name(file_path, project_path)
            
            # 初始化 module
            if module not in project_structure["modules"]:
                project_structure["modules"][module] = {
                    "module_name": module,
                    "packages": {}
                }
            
            # 初始化 package
            if package not in project_structure["modules"][module]["packages"]:
                project_structure["modules"][module]["packages"][package] = {
                    "package_name": package,
                    "classes": []
                }
            
            # 添加类信息
            class_info = {
                "name": class_name,
                "fqn": class_fqn,
                "kind": kind,
                "file_path": file_path,
                "is_interface": cls.get('is_interface', False),
                "is_mapper": cls.get('is_mapper', False),
                "arch_layer": cls.get('arch_layer', 'Other'),
                "annotations": [ann.get('name', '') for ann in cls.get('annotations', [])],
                "method_count": len([m for m in scan_result['methods'] if m.get('class_fqn') == class_fqn])
            }
            
            project_structure["modules"][module]["packages"][package]["classes"].append(class_info)
        
        # 计算统计信息
        for module_name, module_data in project_structure["modules"].items():
            module_data["total_classes"] = sum(
                len(pkg["classes"]) for pkg in module_data["packages"].values()
            )
            module_data["total_packages"] = len(module_data["packages"])
        
        # 写入 JSON 文件
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(project_structure, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ 扫描报告已生成: {report_path}")
        return str(report_path)
    
    def _extract_module_name(self, file_path: str, project_path: str) -> str:
        """
        从文件路径中提取 module 名称
        
        例如:
        - D:\cursor\code-ast-graph\git-repos\official-room-pro-web\official-web-api\src\main\java\...
          -> official-web-api
        - D:\cursor\code-ast-graph\git-repos\yuer-chatroom-service\src\main\java\...
          -> yuer-chatroom-service (根模块)
        """
        try:
            file_path_obj = Path(file_path)
            project_path_obj = Path(project_path)
            
            # 获取相对路径
            rel_path = file_path_obj.relative_to(project_path_obj)
            parts = rel_path.parts
            
            # 如果第一个部分是 src，说明是根模块
            if parts[0] == 'src':
                return Path(project_path).name
            
            # 否则，第一个部分就是 module 名称
            return parts[0]
        except Exception as e:
            logger.warning(f"提取 module 名称失败: {e}")
            return "unknown"
