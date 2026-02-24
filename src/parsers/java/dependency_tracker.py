# -*- coding: utf-8 -*-
"""
依赖追踪器
用于追踪接口实现类、Dubbo调用等跨项目依赖关系
确保知识图谱的完整性和去重
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class DependencyTracker:
    """
    依赖追踪器
    
    功能：
    1. 追踪接口的实现类
    2. 追踪Dubbo服务调用
    3. 追踪Facade接口
    4. 确保类级别的去重
    5. 跨项目依赖追踪
    """
    
    def __init__(self, neo4j_client):
        """
        初始化依赖追踪器
        
        Args:
            neo4j_client: Neo4j客户端实例
        """
        self.client = neo4j_client
        self._scanned_classes: Set[str] = set()  # 已扫描的类FQN集合
        self._pending_classes: Set[str] = set()  # 待扫描的类FQN集合
    
    def check_class_scanned(self, class_fqn: str) -> bool:
        """
        检查类是否已被扫描
        
        Args:
            class_fqn: 类的完全限定名
        
        Returns:
            是否已扫描
        """
        # 先检查内存缓存
        if class_fqn in self._scanned_classes:
            return True
        
        # 检查Neo4j中是否存在
        try:
            result = self.client.execute_query("""
                MATCH (t:Type {fqn: $fqn})
                WHERE t.scanned_at IS NOT NULL
                RETURN count(t) as count
            """, {"fqn": class_fqn})
            
            if result and result[0].get('count', 0) > 0:
                self._scanned_classes.add(class_fqn)
                return True
        except Exception as e:
            logger.warning(f"检查类扫描状态失败 {class_fqn}: {e}")
        
        return False
    
    def mark_class_scanned(self, class_fqn: str):
        """
        标记类为已扫描
        
        Args:
            class_fqn: 类的完全限定名
        """
        self._scanned_classes.add(class_fqn)
        
        # 更新Neo4j中的扫描标记
        try:
            self.client.execute_write("""
                MATCH (t:Type {fqn: $fqn})
                SET t.scanned_at = datetime()
            """, {"fqn": class_fqn})
        except Exception as e:
            logger.warning(f"标记类扫描状态失败 {class_fqn}: {e}")
    
    def find_interface_implementations(
        self,
        interface_fqn: str,
        project_paths: List[str]
    ) -> List[Dict]:
        """
        查找接口的实现类
        
        Args:
            interface_fqn: 接口的完全限定名
            project_paths: 要搜索的项目路径列表
        
        Returns:
            实现类信息列表，每个包含 fqn 和 file_path
        """
        implementations = []
        
        # 先从Neo4j中查找已索引的实现类
        try:
            result = self.client.execute_query("""
                MATCH (impl:Type)-[:IMPLEMENTS]->(iface:Type {fqn: $interface_fqn})
                RETURN impl.fqn as fqn, impl.file_path as file_path
            """, {"interface_fqn": interface_fqn})
            
            for record in result:
                implementations.append({
                    'fqn': record['fqn'],
                    'file_path': record.get('file_path', '')
                })
        except Exception as e:
            logger.warning(f"从Neo4j查找接口实现失败 {interface_fqn}: {e}")
        
        # 如果Neo4j中没有找到，尝试在项目路径中搜索
        if not implementations:
            implementations.extend(
                self._search_implementations_in_projects(interface_fqn, project_paths)
            )
        
        return implementations
    
    def _search_implementations_in_projects(
        self,
        interface_fqn: str,
        project_paths: List[str]
    ) -> List[Dict]:
        """
        在项目路径中搜索接口的实现类
        
        Args:
            interface_fqn: 接口的完全限定名
            project_paths: 项目路径列表
        
        Returns:
            实现类信息列表
        """
        implementations = []
        interface_name = interface_fqn.split('.')[-1]
        
        for project_path in project_paths:
            project_dir = Path(project_path)
            if not project_dir.exists():
                continue
            
            # 搜索所有Java文件
            for java_file in self._find_java_files(project_dir):
                try:
                    # 简单检查：查找 implements 关键字和接口名
                    with open(java_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        # 检查是否实现了该接口
                        if f'implements {interface_name}' in content or \
                           f'implements {interface_fqn}' in content:
                            # 尝试解析类名
                            class_fqn = self._extract_class_fqn(java_file, content)
                            if class_fqn:
                                implementations.append({
                                    'fqn': class_fqn,
                                    'file_path': str(java_file)
                                })
                except Exception as e:
                    logger.debug(f"搜索实现类时读取文件失败 {java_file}: {e}")
                    continue
        
        return implementations
    
    def find_dubbo_references(
        self,
        class_fqn: str
    ) -> List[Dict]:
        """
        查找类中的Dubbo引用（@DubboReference注解的字段）
        
        Args:
            class_fqn: 类的完全限定名
        
        Returns:
            Dubbo引用信息列表，每个包含 field_name, service_interface, group
        """
        dubbo_refs = []
        
        try:
            result = self.client.execute_query("""
                MATCH (t:Type {fqn: $class_fqn})-[:DECLARES]->(f:Field)-[:ANNOTATED_BY]->(a:Annotation {name: 'DubboReference'})
                RETURN f.name as field_name, f.type as service_interface
            """, {"class_fqn": class_fqn})
            
            for record in result:
                dubbo_refs.append({
                    'field_name': record['field_name'],
                    'service_interface': record.get('service_interface', '')
                })
        except Exception as e:
            logger.warning(f"查找Dubbo引用失败 {class_fqn}: {e}")
        
        return dubbo_refs
    
    def find_facade_calls(
        self,
        class_fqn: str
    ) -> List[Dict]:
        """
        查找类中调用的Facade接口
        
        Args:
            class_fqn: 类的完全限定名
        
        Returns:
            Facade调用信息列表
        """
        facade_calls = []
        
        try:
            # 查找通过DEPENDS_ON关系连接的Facade接口
            # Facade通常以Facade、Service等结尾
            result = self.client.execute_query("""
                MATCH (caller:Type {fqn: $class_fqn})-[:DEPENDS_ON]->(facade:Type)
                WHERE facade.fqn CONTAINS 'Facade' OR facade.fqn CONTAINS 'Service'
                RETURN facade.fqn as facade_fqn, facade.name as facade_name
            """, {"class_fqn": class_fqn})
            
            for record in result:
                facade_calls.append({
                    'facade_fqn': record['facade_fqn'],
                    'facade_name': record.get('facade_name', '')
                })
        except Exception as e:
            logger.warning(f"查找Facade调用失败 {class_fqn}: {e}")
        
        return facade_calls
    
    def get_dependency_chain(
        self,
        start_class_fqn: str,
        max_depth: int = 5
    ) -> Dict:
        """
        获取依赖链
        
        Args:
            start_class_fqn: 起始类的FQN
            max_depth: 最大深度
        
        Returns:
            依赖链信息
        """
        chain = {
            'start_class': start_class_fqn,
            'implementations': [],
            'facades': [],
            'dubbo_services': [],
            'depth': 0
        }
        
        # 查找实现类
        implementations = self.find_interface_implementations(start_class_fqn, [])
        chain['implementations'] = implementations
        
        # 对每个实现类，查找其调用的Facade和Dubbo服务
        for impl in implementations:
            impl_fqn = impl['fqn']
            
            # 查找Facade调用
            facades = self.find_facade_calls(impl_fqn)
            chain['facades'].extend(facades)
            
            # 查找Dubbo引用
            dubbo_refs = self.find_dubbo_references(impl_fqn)
            chain['dubbo_services'].extend(dubbo_refs)
        
        return chain
    
    def _find_java_files(self, project_dir: Path) -> List[Path]:
        """查找所有Java文件"""
        java_files = []
        exclude_dirs = {'target', 'build', '.git', 'node_modules', 'out', 'test'}
        
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.java'):
                    java_files.append(Path(root) / file)
        
        return java_files
    
    def _extract_class_fqn(self, java_file: Path, content: str) -> Optional[str]:
        """
        从Java文件内容中提取类的FQN
        
        Args:
            java_file: Java文件路径
            content: 文件内容
        
        Returns:
            类的FQN，如果提取失败返回None
        """
        try:
            import javalang
            
            tree = javalang.parse.parse(content)
            
            # 获取包名
            package_name = None
            if tree.package:
                if isinstance(tree.package.name, list):
                    package_name = '.'.join(str(n) for n in tree.package.name)
                else:
                    package_name = str(tree.package.name)
            
            # 获取类名
            if tree.types:
                for type_decl in tree.types:
                    if isinstance(type_decl, javalang.tree.ClassDeclaration):
                        class_name = type_decl.name
                        if package_name:
                            return f"{package_name}.{class_name}"
                        return class_name
            
            return None
        except Exception as e:
            logger.debug(f"提取类FQN失败 {java_file}: {e}")
            return None
    
    def add_pending_class(self, class_fqn: str):
        """
        添加待扫描的类
        
        Args:
            class_fqn: 类的FQN
        """
        if not self.check_class_scanned(class_fqn):
            self._pending_classes.add(class_fqn)
    
    def get_pending_classes(self) -> Set[str]:
        """
        获取所有待扫描的类
        
        Returns:
            待扫描类的FQN集合
        """
        return self._pending_classes.copy()
    
    def clear_pending_classes(self):
        """清空待扫描类列表"""
        self._pending_classes.clear()
