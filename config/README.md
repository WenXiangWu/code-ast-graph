# 配置文件说明

## 📁 目录结构

```
config/
├── global.yaml.example          # 全局配置示例
├── modules/
│   ├── python_ast.yaml.example  # Python AST 模块配置示例
│   └── jqassistant.yaml.example # jQAssistant 模块配置示例
└── README.md                    # 本文件
```

## 🚀 快速开始

### 1. 复制示例文件

```bash
# 复制全局配置
cp config/global.yaml.example config/global.yaml

# 复制模块配置
cp config/modules/python_ast.yaml.example config/modules/python_ast.yaml
cp config/modules/jqassistant.yaml.example config/modules/jqassistant.yaml
```

### 2. 编辑配置

根据你的环境编辑配置文件：

- `config/global.yaml` - 全局配置（数据库连接、UI 设置等）
- `config/modules/python_ast.yaml` - Python AST 模块配置
- `config/modules/jqassistant.yaml` - jQAssistant 模块配置

### 3. 项目级配置（可选）

在项目根目录创建 `.code-ast-graph.yaml`：

```bash
cp .code-ast-graph.yaml.example .code-ast-graph.yaml
```

## 📝 配置优先级

配置按以下优先级加载（高优先级覆盖低优先级）：

1. **命令行参数**（最高）
2. **环境变量**
3. **项目配置文件** (`.code-ast-graph.yaml`)
4. **模块配置文件** (`config/modules/*.yaml`)
5. **全局配置文件** (`config/global.yaml`)
6. **默认值**（最低）

## 🔒 安全提示

⚠️ **重要**：配置文件可能包含敏感信息（如数据库密码），请：

1. 不要将实际配置文件提交到 Git
2. 使用环境变量存储敏感信息
3. 参考 `.gitignore` 确保配置文件不被提交

## 📚 更多信息

- [配置管理快速参考](../docs/CONFIG_QUICK_START.md)
- [配置管理系统设计](../docs/CONFIG_MANAGEMENT.md)
