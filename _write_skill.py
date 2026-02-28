import os

content = """\
---
name: tech-plan-generator
description: Generate technical implementation plans for Java microservice features. Four-stage pipeline: semantic search for candidate classes/methods, call statistics ranking to identify top 10 high-frequency classes, read full source code into local temp folder, LLM analysis to produce structured tech plan document. Use when users ask for tech plan, solution design, how to implement, how to develop, technical design.
description_zh: 针对 Java 微服务功能开发，通过四阶段流水线（语义搜索→调用统计排名→读取完整代码→分析生成方案）产出结构化技术方案文档。用户提到技术方案/方案设计/实现方案/技术设计/如何实现/如何开发时使用。
source: custom
---

# 技术方案生成 Skill

## 目标

通过四阶段流水线，基于**真实代码事实**生成可落地的技术方案，杜绝凭空臆测。

---

## 执行流程（必须按顺序完成，不可跳步）

### 阶段一：语义搜索——获取候选类/方法列表

**工具**：`mcp__code_index_mcp__mcp_code_search`

**步骤**：

1. 根据用户描述的需求，提炼 2-4 个搜索关键词（中英文各一组）
2. 每个关键词组独立调用一次 `mcp_code_search`，`top_k` 设为 20
3. 合并去重，得到**候选类/方法列表**（通常 20-50 条）
4. 记录每条结果的：`project`（项目名）、`class_fqn`（全限定类名）、`method`（方法名）、相似度分数

**输出**：候选类/方法清单（去重后）

---

### 阶段二：调用统计——排名前 10 的高频类

**工具**：`mcp__code_ast_mcp__ast_query_call_stats`

**步骤**：

1. 对阶段一每个候选项，按 `(project, class_fqn, method)` 调用 `ast_query_call_stats`
   - 若同一个类有多个方法命中，选最具代表性的方法（通常是 public 入口方法）
   - 若调用失败（方法不在图谱中），跳过，不中断流程
2. 收集返回的 `class_stats`（涉及类列表及调用频次）
3. 按**调用次数降序**合并排名，取 **Top 10 类**（以 class_fqn 去重）

**输出**：Top 10 高频类列表，含 project、class_fqn、调用次数

---

### 阶段三：读取完整代码——写入本地临时文件夹

**工具**：`mcp__code_index_mcp__mcp_read_full_file`、`Write`

**步骤**：

1. 对 Top 10 类，逐个调用 `mcp_read_full_file`
   - 参数：`project`=所属项目、`class_name`=全限定类名、`max_lines`=800
2. 将每个类的代码写入 workspace 临时目录 `_code_research/` 下，文件名为 `{简单类名}.java`
   - 示例：`_code_research/UserService.java`
3. 若某个类读取失败，记录到 `_code_research/fetch_errors.txt`，继续处理其他类
4. 写完后在 `_code_research/index.txt` 中列出：已读取的类名、文件路径、所属项目

**输出**：`_code_research/` 目录，含 Top 10 类的完整源代码文件

---

### 阶段四：代码分析——生成技术方案文档

**工具**：`Read`、`Write`

**步骤**：

1. 逐一 `Read` `_code_research/` 下的源代码文件，深度理解：
   - 现有的分层结构（Controller / Service / Manager / Mapper / DAO）
   - 核心接口/方法签名、参数类型、返回值类型
   - 已有的事务边界、异常处理模式、MQ 发送模式
   - 数据库操作（Mapper 方法对应的表名）
2. 结合用户需求和代码现状，生成技术方案文档，写入 `tech_plan.md`

---

## 技术方案文档结构（tech_plan.md 必须包含以下章节）

### 一、需求背景
- 用户原始需求描述
- 核心目标（一句话）

### 二、现有代码调研结论

#### 涉及的核心类/方法
| 类名 | 所属项目 | 层级 | 主要职责 |
|------|----------|------|----------|

#### 现有调用链路摘要
描述当前业务流程（从入口到 DB/MQ）

#### 可复用的代码模式
参数封装风格、返回值规范、异常处理方式

### 三、实现方案

#### 3.1 接口/方法设计
新增或修改的接口签名（含参数、返回值、注解）

#### 3.2 核心业务逻辑步骤
逐步说明实现路径

#### 3.3 数据库变更（如有）
新增字段/表：字段名、类型、含义、索引变更

#### 3.4 MQ 设计（如有）
Topic 名称、消息体结构、生产者/消费者

#### 3.5 Dubbo 接口变更（如有）
接口全限定名、新增方法

### 四、影响面分析
| 维度 | 影响内容 |
|------|----------|
| 涉及服务 | |
| 涉及数据表 | |
| 涉及外部接口 | |

### 五、开发任务拆分
| 子任务 | 负责层 | 预估工时 |
|--------|--------|----------|

### 六、风险与回滚
- 风险点
- 回滚方式

---

## 注意事项

- **所有结论必须来自阅读的真实代码**，不得基于类名推断
- 阶段二 `ast_query_call_stats` 部分类可能查不到（图谱未扫描），此时跳过排名，直接用阶段一的相似度分数作为排名依据
- `_code_research/` 为临时工作目录，生成方案后可告知用户是否清理
- 若 Top 10 中包含明显无关的工具类（如 StringUtils、DateUtils），主动过滤，替换为下一个候选
"""

dest = r"d:\cursor\bixin-ai-agent-platform\.claude\skills\tech-plan-generator\SKILL.md"
os.makedirs(os.path.dirname(dest), exist_ok=True)
with open(dest, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Written to: {dest}")
print(f"Size: {len(content)} chars")
