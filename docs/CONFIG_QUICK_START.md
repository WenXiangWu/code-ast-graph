# 配置管理快速参考

> 快速了解如何配置 Code AST Graph

## 📋 配置层级概览

```
优先级（高 → 低）
├── 命令行参数
├── 环境变量
├── 项目配置 (.code-ast-graph.yaml)
├── 模块配置 (config/modules/*.yaml)
├── 全局配置 (config/global.yaml)
└── 默认值
```

## 🚀 快速开始

### 1. 基础配置（使用环境变量）

最简单的方式是使用环境变量：

```bash
# .env 文件
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

PYTHON_AST_ENABLED=true
PYTHON_AST_EXCLUDE_DIRS=target,build,.git,test
```

### 2. 使用配置文件（推荐）

#### 步骤 1：创建全局配置

```bash
# 复制示例文件
cp config/global.yaml.example config/global.yaml

# 编辑配置
vim config/global.yaml
```

```yaml
# config/global.yaml
storage:
  backend: neo4j
  neo4j:
    uri: bolt://localhost:7687
    user: neo4j
    password: your_password
```

#### 步骤 2：创建模块配置

```bash
# 复制示例文件
cp config/modules/python_ast.yaml.example config/modules/python_ast.yaml

# 编辑配置
vim config/modules/python_ast.yaml
```

```yaml
# config/modules/python_ast.yaml
python_ast:
  enabled: true
  parser:
    exclude_dirs:
      - target
      - build
      - .git
```

#### 步骤 3：（可选）创建项目配置

在项目根目录创建 `.code-ast-graph.yaml`：

```yaml
# .code-ast-graph.yaml
project:
  name: my-project
  parsers:
    - language: java
      exclude_dirs:
        - custom-exclude-dir
```

## 📝 配置项说明

### 全局配置项

| 配置项 | 说明 | 默认值 | 环境变量 |
|--------|------|--------|----------|
| `app.debug` | 调试模式 | `false` | `APP_DEBUG` |
| `app.log_level` | 日志级别 | `INFO` | `APP_LOG_LEVEL` |
| `storage.backend` | 存储后端 | `neo4j` | `STORAGE_BACKEND` |
| `storage.neo4j.uri` | Neo4j URI | `bolt://localhost:7687` | `NEO4J_URI` |
| `storage.neo4j.user` | Neo4j 用户名 | `neo4j` | `NEO4J_USER` |
| `storage.neo4j.password` | Neo4j 密码 | `password` | `NEO4J_PASSWORD` |
| `ui.port` | UI 端口 | `7860` | `UI_PORT` |

### Python AST 配置项

| 配置项 | 说明 | 默认值 | 环境变量 |
|--------|------|--------|----------|
| `python_ast.enabled` | 是否启用 | `true` | `PYTHON_AST_ENABLED` |
| `python_ast.parser.exclude_dirs` | 排除目录 | `['target', 'build', '.git']` | `PYTHON_AST_EXCLUDE_DIRS` |
| `python_ast.parser.exclude_file_patterns` | 排除文件模式 | `['*Test.java']` | `PYTHON_AST_EXCLUDE_PATTERNS` |

### jQAssistant 配置项

| 配置项 | 说明 | 默认值 | 环境变量 |
|--------|------|--------|----------|
| `jqassistant.enabled` | 是否启用 | `false` | `JQASSISTANT_ENABLED` |
| `jqassistant.version` | 版本号 | `2.8.0` | `JQASSISTANT_VERSION` |
| `jqassistant.jar_path` | JAR 路径 | `null` | `JQASSISTANT_JAR_PATH` |

## 💡 常见场景

### 场景 1：开发环境配置

```yaml
# config/global.yaml
app:
  debug: true
  log_level: DEBUG

storage:
  neo4j:
    uri: bolt://localhost:7687
    user: neo4j
    password: dev_password
```

### 场景 2：生产环境配置

```yaml
# config/global.yaml
app:
  debug: false
  log_level: INFO

storage:
  neo4j:
    uri: bolt://prod-neo4j:7687
    user: neo4j
    password: ${NEO4J_PASSWORD}  # 使用环境变量
```

### 场景 3：多项目不同配置

```yaml
# 项目 A/.code-ast-graph.yaml
project:
  name: project-a
  parsers:
    - language: java
      exclude_dirs:
        - custom-dir-a

# 项目 B/.code-ast-graph.yaml
project:
  name: project-b
  parsers:
    - language: python
      exclude_dirs:
        - custom-dir-b
```

## 🔍 配置验证

```python
from src.config import get_config

config = get_config()

# 检查配置
neo4j_uri = config.get('storage.neo4j.uri')
if not neo4j_uri:
    print("错误：Neo4j URI 未配置")
```

## 📚 更多信息

- [配置管理系统设计](CONFIG_MANAGEMENT.md) - 详细设计文档
- [架构设计文档](ARCHITECTURE.md) - 完整架构说明
