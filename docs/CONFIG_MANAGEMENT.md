# 配置管理系统设计

> 清晰、分层、可扩展的配置管理方案

## 📋 目录

1. [设计目标](#设计目标)
2. [配置层级](#配置层级)
3. [配置结构](#配置结构)
4. [配置加载机制](#配置加载机制)
5. [配置验证](#配置验证)
6. [实现方案](#实现方案)
7. [使用示例](#使用示例)

---

## 设计目标

### 核心目标

1. **分层清晰**：全局配置 → 模块配置 → 项目配置
2. **来源统一**：支持多种配置来源（环境变量、YAML、JSON、命令行参数）
3. **优先级明确**：配置覆盖优先级清晰
4. **类型安全**：配置项有明确的类型和默认值
5. **易于扩展**：新增配置项简单
6. **文档完善**：配置项有清晰的文档说明

---

## 配置层级

### 三层配置架构

```
┌─────────────────────────────────────────┐
│     全局配置 (Global Config)            │
│  - 应用级别配置                         │
│  - 日志、数据库连接等                   │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│     模块配置 (Module Config)            │
│  - Python AST 配置                      │
│  - jQAssistant 配置                     │
│  - 解析器配置                           │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│     项目配置 (Project Config)           │
│  - 项目特定的扫描配置                   │
│  - 项目级别的排除规则等                 │
└─────────────────────────────────────────┘
```

### 配置优先级

```
命令行参数 > 环境变量 > 项目配置文件 > 模块配置文件 > 全局配置文件 > 默认值
```

---

## 配置结构

### 1. 全局配置 (Global Config)

```yaml
# config/global.yaml
app:
  name: "Code AST Graph"
  version: "1.0.0"
  debug: false
  log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR

storage:
  backend: "neo4j"  # neo4j, memgraph, arangodb
  neo4j:
    uri: "bolt://localhost:7687"
    user: "neo4j"
    password: "password"
    max_connection_pool_size: 50
    connection_timeout: 30
  memgraph:
    uri: "bolt://localhost:7687"
    user: "memgraph"
    password: "password"

ui:
  host: "0.0.0.0"
  port: 7860
  share: false
  theme: "dark"

paths:
  git_repos: "./git-repos"
  cache_dir: "./.cache"
  metadata_dir: "./.metadata"
```

### 2. 模块配置 (Module Config)

#### Python AST 配置

```yaml
# config/modules/python_ast.yaml
python_ast:
  enabled: true
  
  parser:
    language: "java"  # java, python, typescript
    exclude_dirs:
      - "target"
      - "build"
      - ".git"
      - "node_modules"
      - "out"
      - "bin"
      - "test"
    
    exclude_file_patterns:
      - "*Test.java"
      - "*Tests.java"
      - "*Mock.java"
    
    include_file_extensions:
      - ".java"
    
    exclude_annotations:
      - "org.junit.Test"
      - "org.junit.jupiter.api.Test"
    
    exclude_annotation_patterns:
      - "*.Test"
      - "*.Mock"
  
  storage:
    # 继承全局存储配置，可覆盖
    use_global: true
    # 或指定独立的存储配置
    # neo4j:
    #   uri: "bolt://localhost:7687"
  
  scan:
    batch_size: 100
    parallel: true
    max_workers: 4
    timeout: 3600
```

#### jQAssistant 配置

```yaml
# config/modules/jqassistant.yaml
jqassistant:
  enabled: false
  
  version: "2.8.0"
  jar_path: null  # 如果指定，使用指定路径；否则使用 Maven 插件
  
  storage:
    use_global: true
  
  scan:
    timeout: 3600
    parallel: true
    max_workers: 4
  
  docker:
    enabled: false
    container_name: "jqassistant-scanner"
    image: "jqassistant/jqassistant-cli:2.8.0"
```

### 3. 项目配置 (Project Config)

```yaml
# .code-ast-graph.yaml (项目根目录)
project:
  name: "my-project"
  
  parsers:
    - language: "java"
      enabled: true
      exclude_dirs:
        - "custom-exclude-dir"
      exclude_file_patterns:
        - "*CustomTest.java"
  
  storage:
    # 项目可以使用独立的存储配置
    backend: "neo4j"
    neo4j:
      uri: "bolt://project-neo4j:7687"
  
  incremental_update:
    enabled: true
    auto_update: false
    update_interval: 3600  # 秒
```

---

## 配置加载机制

### 配置加载顺序

```python
class ConfigLoader:
    """配置加载器"""
    
    def __init__(self):
        self.config_hierarchy = []
    
    def load_all(self) -> Dict:
        """加载所有配置"""
        config = {}
        
        # 1. 加载默认配置
        config = self._merge(config, self._load_defaults())
        
        # 2. 加载全局配置文件
        global_config_path = self._find_config_file('config/global.yaml')
        if global_config_path:
            config = self._merge(config, self._load_yaml(global_config_path))
        
        # 3. 加载模块配置文件
        module_configs = self._load_module_configs()
        config = self._merge(config, module_configs)
        
        # 4. 加载项目配置文件
        project_config_path = self._find_project_config()
        if project_config_path:
            config = self._merge(config, self._load_yaml(project_config_path))
        
        # 5. 加载环境变量（覆盖文件配置）
        env_config = self._load_from_env()
        config = self._merge(config, env_config)
        
        # 6. 加载命令行参数（最高优先级）
        cli_config = self._load_from_cli()
        config = self._merge(config, cli_config)
        
        return config
    
    def _merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并配置"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result
```

### 环境变量映射

```python
# 环境变量命名规则：模块_配置项（大写，下划线分隔）
ENV_MAPPING = {
    # 全局配置
    'APP_DEBUG': 'app.debug',
    'APP_LOG_LEVEL': 'app.log_level',
    'STORAGE_BACKEND': 'storage.backend',
    'NEO4J_URI': 'storage.neo4j.uri',
    'NEO4J_USER': 'storage.neo4j.user',
    'NEO4J_PASSWORD': 'storage.neo4j.password',
    
    # Python AST 配置
    'PYTHON_AST_ENABLED': 'python_ast.enabled',
    'PYTHON_AST_EXCLUDE_DIRS': 'python_ast.parser.exclude_dirs',
    'PYTHON_AST_EXCLUDE_PATTERNS': 'python_ast.parser.exclude_file_patterns',
    
    # jQAssistant 配置
    'JQASSISTANT_ENABLED': 'jqassistant.enabled',
    'JQASSISTANT_VERSION': 'jqassistant.version',
    'JQASSISTANT_JAR_PATH': 'jqassistant.jar_path',
}
```

---

## 配置验证

### 配置 Schema 定义

```python
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class StorageBackend(str, Enum):
    NEO4J = "neo4j"
    MEMGRAPH = "memgraph"
    ARANGODB = "arangodb"

@dataclass
class Neo4jConfig:
    """Neo4j 配置"""
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"
    max_connection_pool_size: int = 50
    connection_timeout: int = 30
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        if not self.uri:
            errors.append("Neo4j URI 不能为空")
        if not self.user:
            errors.append("Neo4j 用户名不能为空")
        if self.max_connection_pool_size <= 0:
            errors.append("连接池大小必须大于0")
        return errors

@dataclass
class StorageConfig:
    """存储配置"""
    backend: StorageBackend = StorageBackend.NEO4J
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    memgraph: Optional[Neo4jConfig] = None
    arangodb: Optional[Dict] = None
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        if self.backend == StorageBackend.NEO4J:
            errors.extend(self.neo4j.validate())
        elif self.backend == StorageBackend.MEMGRAPH:
            if self.memgraph:
                errors.extend(self.memgraph.validate())
        return errors

@dataclass
class PythonASTParserConfig:
    """Python AST 解析器配置"""
    language: str = "java"
    exclude_dirs: List[str] = field(default_factory=lambda: ['target', 'build', '.git'])
    exclude_file_patterns: List[str] = field(default_factory=lambda: ['*Test.java'])
    include_file_extensions: List[str] = field(default_factory=lambda: ['.java'])
    exclude_annotations: List[str] = field(default_factory=list)
    exclude_annotation_patterns: List[str] = field(default_factory=list)

@dataclass
class PythonASTConfig:
    """Python AST 模块配置"""
    enabled: bool = True
    parser: PythonASTParserConfig = field(default_factory=PythonASTParserConfig)
    storage: Optional[StorageConfig] = None
    scan: Dict = field(default_factory=lambda: {
        'batch_size': 100,
        'parallel': True,
        'max_workers': 4,
        'timeout': 3600
    })
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        if self.storage:
            errors.extend(self.storage.validate())
        return errors

@dataclass
class AppConfig:
    """应用配置"""
    name: str = "Code AST Graph"
    version: str = "1.0.0"
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO

@dataclass
class GlobalConfig:
    """全局配置"""
    app: AppConfig = field(default_factory=AppConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    ui: Dict = field(default_factory=lambda: {
        'host': '0.0.0.0',
        'port': 7860,
        'share': False,
        'theme': 'dark'
    })
    paths: Dict = field(default_factory=lambda: {
        'git_repos': './git-repos',
        'cache_dir': './.cache',
        'metadata_dir': './.metadata'
    })
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        errors.extend(self.storage.validate())
        return errors
```

---

## 实现方案

### 1. 统一配置管理器

```python
# src/config/__init__.py
"""
统一配置管理系统
"""

from typing import Dict, Optional, Any
from pathlib import Path
import yaml
import os
from dataclasses import dataclass, asdict

class ConfigManager:
    """配置管理器（单例）"""
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[Dict] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = self._load_all()
    
    def _load_all(self) -> Dict:
        """加载所有配置"""
        config = {}
        
        # 1. 默认配置
        config = self._merge(config, self._get_defaults())
        
        # 2. 全局配置文件
        global_config = self._load_file('config/global.yaml')
        if global_config:
            config = self._merge(config, global_config)
        
        # 3. 模块配置文件
        module_configs = self._load_module_configs()
        config = self._merge(config, module_configs)
        
        # 4. 项目配置文件
        project_config = self._load_project_config()
        if project_config:
            config = self._merge(config, project_config)
        
        # 5. 环境变量
        env_config = self._load_from_env()
        config = self._merge(config, env_config)
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的路径）
        
        Examples:
            config.get('storage.neo4j.uri')
            config.get('python_ast.parser.exclude_dirs')
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_module_config(self, module_name: str) -> Dict:
        """获取模块配置"""
        return self._config.get(module_name, {})
    
    def get_storage_config(self) -> Dict:
        """获取存储配置"""
        return self._config.get('storage', {})
    
    def reload(self):
        """重新加载配置"""
        self._config = self._load_all()
    
    def _merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并配置"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _load_file(self, path: str) -> Optional[Dict]:
        """加载 YAML 文件"""
        file_path = Path(path)
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return None
    
    def _load_module_configs(self) -> Dict:
        """加载模块配置"""
        config = {}
        modules_dir = Path('config/modules')
        if modules_dir.exists():
            for config_file in modules_dir.glob('*.yaml'):
                module_name = config_file.stem
                module_config = self._load_file(str(config_file))
                if module_config:
                    config[module_name] = module_config
        return config
    
    def _load_project_config(self) -> Optional[Dict]:
        """加载项目配置文件"""
        # 查找项目根目录的配置文件
        config_files = [
            '.code-ast-graph.yaml',
            '.code-ast-graph.yml',
            'code-ast-graph.yaml',
            'code-ast-graph.yml'
        ]
        
        # 从当前目录向上查找
        current = Path.cwd()
        while current != current.parent:
            for config_file in config_files:
                config_path = current / config_file
                if config_path.exists():
                    return self._load_file(str(config_path))
            current = current.parent
        
        return None
    
    def _load_from_env(self) -> Dict:
        """从环境变量加载配置"""
        config = {}
        env_mapping = self._get_env_mapping()
        
        for env_key, config_path in env_mapping.items():
            env_value = os.getenv(env_key)
            if env_value:
                self._set_nested(config, config_path, env_value)
        
        return config
    
    def _set_nested(self, config: Dict, path: str, value: Any):
        """设置嵌套配置值"""
        keys = path.split('.')
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = self._parse_value(value)
    
    def _parse_value(self, value: str) -> Any:
        """解析环境变量值（支持列表、布尔值等）"""
        # 布尔值
        if value.lower() in ('true', '1', 'yes', 'on'):
            return True
        if value.lower() in ('false', '0', 'no', 'off'):
            return False
        
        # 列表（逗号分隔）
        if ',' in value:
            return [v.strip() for v in value.split(',')]
        
        # 数字
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        return value
    
    def _get_env_mapping(self) -> Dict[str, str]:
        """获取环境变量映射"""
        return {
            # 全局配置
            'APP_DEBUG': 'app.debug',
            'APP_LOG_LEVEL': 'app.log_level',
            'STORAGE_BACKEND': 'storage.backend',
            'NEO4J_URI': 'storage.neo4j.uri',
            'NEO4J_USER': 'storage.neo4j.user',
            'NEO4J_PASSWORD': 'storage.neo4j.password',
            
            # Python AST 配置
            'PYTHON_AST_ENABLED': 'python_ast.enabled',
            'PYTHON_AST_EXCLUDE_DIRS': 'python_ast.parser.exclude_dirs',
            'PYTHON_AST_EXCLUDE_PATTERNS': 'python_ast.parser.exclude_file_patterns',
            
            # jQAssistant 配置
            'JQASSISTANT_ENABLED': 'jqassistant.enabled',
            'JQASSISTANT_VERSION': 'jqassistant.version',
            'JQASSISTANT_JAR_PATH': 'jqassistant.jar_path',
        }
    
    def _get_defaults(self) -> Dict:
        """获取默认配置"""
        return {
            'app': {
                'name': 'Code AST Graph',
                'version': '1.0.0',
                'debug': False,
                'log_level': 'INFO'
            },
            'storage': {
                'backend': 'neo4j',
                'neo4j': {
                    'uri': 'bolt://localhost:7687',
                    'user': 'neo4j',
                    'password': 'password',
                    'max_connection_pool_size': 50,
                    'connection_timeout': 30
                }
            },
            'ui': {
                'host': '0.0.0.0',
                'port': 7860,
                'share': False,
                'theme': 'dark'
            },
            'paths': {
                'git_repos': './git-repos',
                'cache_dir': './.cache',
                'metadata_dir': './.metadata'
            }
        }


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None

def get_config() -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
```

### 2. 模块配置适配器

```python
# src/config/adapters.py
"""
配置适配器：将统一配置转换为模块特定的配置对象
"""

from src.config import get_config
from src.python_ast.config import PythonASTConfig
from src.jqassistant.config import JQAssistantConfig

def get_python_ast_config() -> PythonASTConfig:
    """从统一配置获取 Python AST 配置"""
    config = get_config()
    module_config = config.get_module_config('python_ast')
    
    return PythonASTConfig(
        enabled=module_config.get('enabled', True),
        exclude_dirs=module_config.get('parser', {}).get('exclude_dirs', []),
        exclude_file_patterns=module_config.get('parser', {}).get('exclude_file_patterns', []),
        # ... 其他配置项
    )

def get_jqassistant_config() -> JQAssistantConfig:
    """从统一配置获取 jQAssistant 配置"""
    config = get_config()
    module_config = config.get_module_config('jqassistant')
    
    return JQAssistantConfig(
        enabled=module_config.get('enabled', False),
        jqassistant_version=module_config.get('version', '2.8.0'),
        jqassistant_jar_path=module_config.get('jar_path'),
        # ... 其他配置项
    )
```

---

## 使用示例

### 示例 1：基本使用

```python
from src.config import get_config

# 获取配置管理器
config = get_config()

# 获取配置值
neo4j_uri = config.get('storage.neo4j.uri')
python_ast_enabled = config.get('python_ast.enabled', True)

# 获取模块配置
python_ast_config = config.get_module_config('python_ast')
```

### 示例 2：模块配置适配

```python
from src.config.adapters import get_python_ast_config

# 获取 Python AST 配置对象
config = get_python_ast_config()
scanner = PythonASTScanner(config=config)
```

### 示例 3：配置文件示例

```yaml
# config/global.yaml
storage:
  backend: neo4j
  neo4j:
    uri: bolt://localhost:7687
    user: neo4j
    password: ${NEO4J_PASSWORD}  # 支持环境变量引用

# config/modules/python_ast.yaml
python_ast:
  enabled: true
  parser:
    exclude_dirs:
      - target
      - build
      - .git
```

### 示例 4：项目级配置

```yaml
# .code-ast-graph.yaml (项目根目录)
project:
  name: my-project
  parsers:
    - language: java
      exclude_dirs:
        - custom-exclude-dir
```

---

## 配置文档生成

### 自动生成配置文档

```python
# scripts/generate_config_doc.py
"""
生成配置文档
"""

from src.config import get_config
import yaml

def generate_config_doc():
    """生成配置文档"""
    config = get_config()
    
    doc = {
        'description': 'Code AST Graph 配置说明',
        'config': config._config,
        'env_variables': config._get_env_mapping()
    }
    
    with open('docs/CONFIG_REFERENCE.md', 'w', encoding='utf-8') as f:
        f.write('# 配置参考文档\n\n')
        f.write('## 配置结构\n\n')
        f.write('```yaml\n')
        f.write(yaml.dump(doc['config'], allow_unicode=True, default_flow_style=False))
        f.write('```\n\n')
        f.write('## 环境变量\n\n')
        for env_key, config_path in doc['env_variables'].items():
            f.write(f'- `{env_key}` → `{config_path}`\n')
```

---

## 总结

配置管理系统的核心特点：

1. **分层清晰**：全局 → 模块 → 项目
2. **来源统一**：支持 YAML、环境变量、命令行参数
3. **优先级明确**：命令行 > 环境变量 > 项目配置 > 模块配置 > 全局配置 > 默认值
4. **类型安全**：使用 dataclass 定义配置结构
5. **易于扩展**：新增配置项只需修改配置文件
6. **向后兼容**：保留现有的环境变量支持

通过这个配置管理系统，可以：
- ✅ 清晰管理各层级配置
- ✅ 支持多种配置来源
- ✅ 便于配置验证和文档生成
- ✅ 保持向后兼容性
