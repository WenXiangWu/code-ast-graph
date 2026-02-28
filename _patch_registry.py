"""
Patch bixin-ai-agent-platform/backend/agents/code_registry.py:
  1. Insert _build_tech_plan_agent function before the CODE_AGENTS dict
  2. Add tech_plan_agent entry to the dict
"""
import re

target = r"d:\cursor\bixin-ai-agent-platform\backend\agents\code_registry.py"

with open(target, "r", encoding="utf-8") as f:
    src = f.read()

# -------- 1. Insert builder function before "# 注册表" line --------
builder_code = '''
async def _build_tech_plan_agent(ctx: CodeAgentContext) -> Dict[str, Any]:
    """
    技术方案生成 Agent。
    四阶段流水线：
      1. mcp_code_search        —— 语义搜索，获取候选类/方法列表
      2. ast_query_call_stats   —— 调用统计，排名前 10 高频类
      3. mcp_read_full_file     —— 读取完整代码，写入 _code_research/ 临时目录
      4. Read + LLM 分析        —— 阅读源码并生成 tech_plan.md
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    tools = [
        # 代码语义搜索（code-index-demo MCP）
        "mcp__code_index_mcp__mcp_code_search",
        "mcp__code_index_mcp__mcp_read_full_file",
        # 调用图谱统计（code-ast-graph MCP）
        "mcp__code_ast_mcp__ast_list_projects",
        "mcp__code_ast_mcp__ast_query_call_stats",
        "mcp__code_ast_mcp__ast_query_call_chain",
        # 文件读写
        "Read",
        "Write",
        # Skill 调度
        "Skill",
    ]

    prompt = f"""你是一位资深 Java 微服务架构师，专职负责**技术方案生成**。

当前时间：{now}
会话 workspace：{ctx.workspace_path}

## 工作流程

当用户提出功能需求时，你必须严格按照四阶段流水线执行，不可跳步：

**阶段一：语义搜索——获取候选类/方法列表**
- 调用 `mcp__code_index_mcp__mcp_code_search` 进行语义搜索（top_k=20）
- 提炼 2-4 个关键词，中英文各一组，分别搜索后合并去重
- 记录每条结果的 project、class_fqn、method、相似度分数

**阶段二：调用统计——排名前 10 的高频类**
- 对候选列表中每个 (project, class_fqn, method) 调用 `mcp__code_ast_mcp__ast_query_call_stats`
- 若方法不在图谱中则跳过（不中断流程）
- 按调用次数降序排名，取 Top 10 类（以 class_fqn 去重）
- 过滤明显无关的工具类（StringUtils、DateUtils 等）

**阶段三：读取完整代码——写入本地临时文件夹**
- 对 Top 10 类逐个调用 `mcp__code_index_mcp__mcp_read_full_file`（max_lines=800）
- 用 `Write` 将源码写入 `_code_research/{{简单类名}}.java`
- 读取失败的类记录到 `_code_research/fetch_errors.txt`
- 最终在 `_code_research/index.txt` 中汇总已读取的类名、路径、项目

**阶段四：代码分析——生成技术方案文档**
- 逐一 `Read` `_code_research/` 下的源码文件，理解分层结构、接口签名、事务边界、DB/MQ 模式
- 将技术方案写入 workspace 根目录的 `tech_plan.md`

## 方案文档必须包含
一、需求背景 / 二、现有代码调研结论（核心类表格 + 调用链摘要 + 可复用模式）/
三、实现方案（接口设计 + 业务逻辑步骤 + DB/MQ/Dubbo 变更）/
四、影响面分析 / 五、开发任务拆分 / 六、风险与回滚

## 原则
- 所有结论必须来自真实代码，不得凭类名猜测
- 若 `ast_query_call_stats` 失败，用搜索相似度分数替代排名
- 完成后告知用户 `_code_research/` 是否需要清理
"""

    return {
        "name": "技术方案生成助手",
        "description": "四阶段流水线：语义搜索→调用统计排名→读取完整代码→分析生成方案",
        "prompt": prompt,
        "model": "anthropic/claude-sonnet-4.5",
        "tools": tools,
        "subagents": [],
        "max_thinking_tokens": 10000,
        "is_default": False,
        "is_dev_workflow": True,
    }

'''

marker = "# 注册表：key -> spec"
if marker not in src:
    print("ERROR: marker not found")
    exit(1)

src = src.replace(marker, builder_code + marker)

# -------- 2. Add tech_plan_agent entry to CODE_AGENTS dict --------
old_tail = '''    "code_dev_assistant": CodeAgentSpec(
        key="code_dev_assistant",
        name="Code Dev Assistant",
        description="代码级示例Agent（动态prompt/tools）",
        build=_build_dev_code_agent,
        is_dev_workflow=True,  # 标记为研发流程Agent
    )
}'''

new_tail = '''    "code_dev_assistant": CodeAgentSpec(
        key="code_dev_assistant",
        name="Code Dev Assistant",
        description="代码级示例Agent（动态prompt/tools）",
        build=_build_dev_code_agent,
        is_dev_workflow=True,
    ),
    "tech_plan_agent": CodeAgentSpec(
        key="tech_plan_agent",
        name="技术方案生成助手",
        description="四阶段流水线：语义搜索→调用统计排名→读取完整代码→分析生成方案",
        build=_build_tech_plan_agent,
        is_dev_workflow=True,
    ),
}'''

if old_tail not in src:
    print("ERROR: CODE_AGENTS tail not found, printing current tail for debug:")
    print(src[-500:])
    exit(1)

src = src.replace(old_tail, new_tail)

with open(target, "w", encoding="utf-8") as f:
    f.write(src)

print("Patched successfully.")
print(f"New size: {len(src)} chars")
