# Code AST Graph 项目 Wiki 索引

> 面向“技术方案生成 Agent / 架构分析”的项目入口导航。
>
> 本 Wiki 旨在帮助你快速理解 Code AST Graph 的能力边界、系统架构，以及如何在技术方案生成工作流中与 `code-index-demo`、技术方案 Agent 协同使用。

## 1. 项目概览

Code AST Graph 是一个独立的**代码知识图谱构建与分析系统**，负责从代码仓库中解析出类、方法、调用关系、Dubbo 调用、数据库表、MQ Topic 等信息，并将其写入 Neo4j，以便做全链路架构分析。

- **定位**：只做“知识图谱 + 调用链 + 架构关系”，不包含向量搜索。
- **典型用法**：给定某个项目 + 类/方法，全链路地查出入口 API、下游 Dubbo、数据库表、MQ 主题等，为技术方案生成提供“现状分析”数据。
- **配套项目**：
  - `code-index-demo`：负责代码向量化与语义搜索（找“哪些类可能相关”）。
  - 技术方案 Agent (`tech_planning`)：编排 `code-index-demo` + Code AST Graph，生成完整技术方案。

推荐先阅读根目录下的 [README](../README.md) 了解基础使用方式，再按下面的导航深入。

## 2. 使用角色视角导航

### 2.1 普通使用者（只想查调用链/表/MQ）

- **快速开始**：参见 [快速开始](QUICK_START.md)
  - 启动 Neo4j
  - 启动后端 `backend/main.py`
  - 启动前端 `frontend`（React + Vite）
- **前端入口**：
  - 项目管理页：查看/触发项目扫描
  - 图谱查询页：按项目 + 起始类/方法查询调用关系
  - 可视化页：交互式浏览知识图谱
- **MCP 查询接口**：
  - HTTP 端点：`POST /api/mcp/query`
  - 文档：详见 [MCP 标准化查询接口说明](MCP接口说明.md)

### 2.2 技术方案生成 Agent / 架构师

- **整体架构与分层**：
  - [架构设计文档](ARCHITECTURE.md)
  - 重点关注 Input/Parser/Storage/Query 各层职责和扩展点。
- **配置与部署**：
  - [配置管理系统设计](CONFIG_MANAGEMENT.md)
  - [全局/模块/项目配置示例](../config/global.yaml.example, ../config/modules/jqassistant.yaml.example)
- **MCP 能力与返回数据模型**：
  - [MCP 标准化查询接口说明](MCP接口说明.md)
  - 可直接作为 Agent 工具函数的契约文档。
- **典型工作流（与 code-index-demo 协同）**：
  - 在 `code-index-demo` 中做语义搜索，拿到候选类/方法列表。
  - 对每个候选类/方法，调用本项目的 `/api/mcp/query` 获取调用链、Dubbo、表、MQ 等信息。
  - 将结果写入 Agent 的 Working Memory，用于技术方案撰写与审查。

## 3. 核心能力总览

### 3.1 代码知识图谱能力

- **实体（节点）**：Project、Package、Type、Method、Field、HTTPEndpoint、MQTopic、Table、DubboService 等。
- **关系（边）**：CONTAINS、CALLS、DEPENDS_ON、EXPOSES_API、MAPPER_FOR_TABLE、USES_TABLE、LISTENS_TO_MQ、SENDS_TO_MQ、USES_DUBBO_SERVICE 等。
- **典型问题**：
  - 某个 HTTP 接口的完整调用链（Controller → Service → Manager → Dubbo → DB/MQ）。
  - 某张数据库表在哪些类/方法中被访问。
  - 修改某个类时，上游/下游有哪些受影响的调用点（影响面分析）。

更多细节可参考：

- [调用链与数据模型示例文档](图谱构建借鉴与目标结构.md)
- [边类型设计说明](边类型设计说明.md)
- [架构分层识别规则](架构分层识别规则.md)

### 3.2 MCP 标准化查询接口

- **端点**：`POST /api/mcp/query`
- **输入**：
  - `project`：项目名称（与 Neo4j 中 Project 节点一致）
  - `class_fqn`：类的全限定名
  - `method`：方法名
  - `max_depth`：最大查询深度
- **输出核心字段**：
  - `endpoints`：对应的前端入口（路径、HTTP 方法）。
  - `internal_classes`：内部类及架构层（Controller/Service/Manager/Repository 等）。
  - `dubbo_calls`：涉及的 Dubbo 接口与方法。
  - `tables`：涉及的数据库表及 Mapper。
  - `aries_jobs`：相关定时任务。
  - `mq_info`：涉及的 MQ Topic 与监听/发送方。

适合作为技术方案 Agent 的**单一工具节点**，一键拿到“现状分析”所需的主要结构化数据。

## 4. 运行与配置

### 4.1 运行方式速查

- 推荐一键启动：
  - 根目录执行 `npm run dev` 或使用 `start.ps1` / `start.sh`。
- 手工启动：
  - Neo4j：`docker run neo4j`（详见根目录 README）。
  - 后端：`cd backend && python main.py`。
  - 前端：`cd frontend && npm run dev`。

更多细节请参见：

- [快速开始](QUICK_START.md)
- [Neo4j 故障排查](NEO4J_TROUBLESHOOTING.md)

### 4.2 配置体系

- 全局配置：控制存储后端、日志级别、UI 端口等。
- 模块配置：如 Java 解析、jQAssistant 集成开关、扫描并发度等。
- 项目级配置：支持在业务仓库根目录放置 `.code-ast-graph.yaml`，为单个项目定制扫描规则和存储配置。

配置体系的完整设计和示例见 [配置管理系统设计](CONFIG_MANAGEMENT.md)。

## 5. 与其他系统的关系

### 5.1 与 code-index-demo

- `code-index-demo`：负责
  - 从 Git 仓库拉取代码并分块向量化
  - 提供语义搜索能力（自然语言 → 相关代码片段/类/方法）
  - 存储在 PostgreSQL + pgvector 中
- Code AST Graph：负责
  - 解析代码 AST，构建 Neo4j 知识图谱
  - 提供调用链、依赖关系、表/MQ/Dubbo 等结构化查询能力
- **组合使用方式**：
  1. 使用 `code-index-demo` 搜索“积分发放”“聊天室贵族开通”等业务关键词；
  2. 从搜索结果中提取候选类/方法；
  3. 对每个候选项调用 Code AST Graph 的 MCP 接口，获取精确调用链和数据流；
  4. 技术方案 Agent 基于这些数据撰写和审查方案。

### 5.2 与技术方案 Agent (`tech_planning`)

- 技术方案 Agent 可以将 Code AST Graph 视为一个**外部工具提供方**：
  - 在“Code Research”阶段，通过 MCP 或直接 REST API 调用本项目；
  - 将查询结果填充到 `research_report` 中的“调用链/表/MQ/定时任务”部分；
  - 在 “Architecture Design / Plan Review” 阶段，结合这些结构化数据进行架构设计和风险评估。

## 6. 脚本与调试入口

项目根目录下提供了大量调试脚本，常见场景包括：

- 图谱构建与验证：`scan_project.py`、`final_test.py`、`final_verification.py`。
- 特定链路排查：`check_dubbo_calls.py`、`check_db_calls_in_tree.py`、`debug_noble_full_chain.py`、`test_call_tree_full.py` 等。
- 清理与修复：`clean_all_wrong_data.py`、`clean_duplicate_interface_nodes.py`、`clean_wrong_implements.py` 等。

如果你想从命令行快速理解某条链路或某类节点的数据情况，可以优先查看 `scripts/` 目录下的对应脚本，并把其中的 Cypher 查询迁移到你自己的 Agent 工具里。

## 7. 故障排查与常见问题

- Neo4j 无法连接 / 查询超时 → 参见 [Neo4j 故障排查](NEO4J_TROUBLESHOOTING.md)。
- 构建出的图谱缺少 Dubbo / MQ / 表信息 → 优先检查解析规则是否覆盖对应注解，参考 [边类型设计说明](边类型设计说明.md) 与相关排查文档。
- 某些项目构建后节点/边数量明显异常 → 使用 `debug_*`、`check_*` 系列脚本做定向排查。

## 8. 后续扩展建议

如果你在此基础上继续演进项目，建议优先考虑：

1. 用 MCP 形式标准化更多查询接口（例如：根据 URL 直接查调用链、根据表名反查访问它的 Service 列表等）。
2. 为多语言（如 Python、TypeScript）解析补齐同构的数据模型与关系边，确保前端与 Agent 不需要感知语言差异。
3. 在前端 UI 中暴露更多“技术方案视角”的聚合视图，例如“服务依赖矩阵”、“表访问矩阵”、“关键链路一览”等。
