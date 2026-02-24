"""
测试 Python AST 解析器和 Neo4j 存储的迁移
"""

import unittest
import tempfile
import os
from pathlib import Path

# 使用新架构导入
from src.parsers.java import JavaParser, JavaParserConfig
from src.storage.neo4j import Neo4jStorage
from src.core.models import ProjectInfo, CodeFile
from src.inputs.filesystem_input import FileSystemCodeInput

# 兼容性导入（用于测试）
PythonASTParser = JavaParser
PythonASTConfig = JavaParserConfig


class TestPythonASTMigration(unittest.TestCase):
    """测试 Python AST 迁移"""
    
    def setUp(self):
        """设置测试环境"""
        self.config = PythonASTConfig()
        self.parser = PythonASTParser(config=self.config)
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.test_project_path = Path(self.temp_dir) / "test_project"
        self.test_project_path.mkdir()
    
    def tearDown(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parser_supported_languages(self):
        """测试解析器支持的语言"""
        languages = self.parser.supported_languages()
        self.assertIn('java', languages)
    
    def test_parser_can_parse(self):
        """测试解析器能否解析文件"""
        # 创建一个 Java 文件（不使用 Test.java，因为会被排除规则匹配）
        java_file = self.test_project_path / "Example.java"
        java_file.write_text("""
package com.example;

public class Example {
    public void hello() {
        System.out.println("Hello");
    }
}
        """)
        
        code_file = CodeFile(
            path=java_file,
            content=java_file.read_text(),
            language='java'
        )
        
        self.assertTrue(self.parser.can_parse(code_file))
    
    def test_parser_parse_single_file(self):
        """测试解析单个文件"""
        # 创建一个 Java 文件（不使用 Test.java，因为会被排除规则匹配）
        java_file = self.test_project_path / "Example.java"
        java_file.write_text("""
package com.example;

public class Example {
    private String name;
    
    public void hello() {
        System.out.println("Hello");
    }
}
        """)
        
        code_file = CodeFile(
            path=java_file,
            content=java_file.read_text(),
            language='java'
        )
        
        project_info = ProjectInfo(
            name="test_project",
            path=str(self.test_project_path),
            language='java'
        )
        
        result = self.parser.parse(code_file, project_info)
        
        # 验证解析结果
        self.assertIsNotNone(result)
        # 检查是否有错误
        if result.errors:
            print(f"解析错误: {result.errors}")
        # 应该至少有一个包实体和一个类实体
        self.assertGreater(len(result.entities), 0)
        
        # 应该有一个类实体
        type_entities = [e for e in result.entities if e.type.value == 'Type']
        self.assertGreater(len(type_entities), 0)
        
        # 应该有一个方法实体
        method_entities = [e for e in result.entities if e.type.value == 'Method']
        self.assertGreater(len(method_entities), 0)
    
    def test_storage_interface(self):
        """测试存储接口"""
        # 注意：这个测试需要 Neo4j 运行，如果没有运行会跳过
        storage = Neo4jStorage()
        
        # 测试连接方法存在
        self.assertTrue(hasattr(storage, 'connect'))
        self.assertTrue(hasattr(storage, 'disconnect'))
        self.assertTrue(hasattr(storage, 'is_connected'))
        self.assertTrue(hasattr(storage, 'create_entities'))
        self.assertTrue(hasattr(storage, 'create_relationships'))
        self.assertTrue(hasattr(storage, 'project_exists'))
    
    @unittest.skipUnless(
        os.getenv('NEO4J_URI') or os.getenv('JQASSISTANT_NEO4J_URI'),
        "需要 Neo4j 连接配置"
    )
    def test_full_scan_flow(self):
        """测试完整的扫描流程（需要 Neo4j）"""
        # 创建一个简单的 Java 项目
        (self.test_project_path / "src" / "main" / "java" / "com" / "example").mkdir(parents=True)
        java_file = self.test_project_path / "src" / "main" / "java" / "com" / "example" / "Test.java"
        java_file.write_text("""
package com.example;

public class Test {
    public void hello() {
        System.out.println("Hello");
    }
}
        """)
        
        # 创建输入源
        input_source = FileSystemCodeInput(str(self.test_project_path))
        
        # 创建存储
        storage = Neo4jStorage()
        if not storage.connect():
            self.skipTest("无法连接到 Neo4j")
        
        try:
            # 创建项目信息
            project_info = ProjectInfo(
                name="test_project_migration",
                path=str(self.test_project_path),
                language='java'
            )
            
            # 解析项目
            parse_result = self.parser.parse_project(input_source, project_info)
            
            # 验证解析结果
            self.assertIsNotNone(parse_result)
            self.assertGreater(len(parse_result.entities), 0)
            
            # 存储到 Neo4j
            entities_count = storage.create_entities(parse_result.entities)
            relationships_count = storage.create_relationships(parse_result.relationships)
            
            # 验证存储结果
            self.assertGreater(entities_count, 0)
            self.assertGreaterEqual(relationships_count, 0)
            
            # 验证项目是否存在
            self.assertTrue(storage.project_exists("test_project_migration"))
        
        finally:
            storage.disconnect()


if __name__ == '__main__':
    unittest.main()
