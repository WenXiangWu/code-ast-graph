"""
精确复现后端配置（含 stderr + setting_sources + MCP 服务）
"""
import asyncio
import os
import sys
import traceback

from dotenv import load_dotenv
load_dotenv(r"D:\cursor\bixin-ai-agent-platform\.env")

sys.path.insert(0, r"D:\cursor\bixin-ai-agent-platform")
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ["ANTHROPIC_BASE_URL"] = os.getenv("ANTHROPIC_BASE_URL", "")

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow
from claude_agent_sdk.types import ToolPermissionContext
import pathlib

TEST_CWD = r"D:\tmp\ai-agent\test-exact-backend"
pathlib.Path(TEST_CWD).mkdir(parents=True, exist_ok=True)
# 模拟 workspace 的 .claude 目录结构
pathlib.Path(TEST_CWD + r"\.claude\skills").mkdir(parents=True, exist_ok=True)


async def can_use_tool_cb(tool_name, tool_input, ctx: ToolPermissionContext):
    print(f"  [can_use_tool] {tool_name}")
    return PermissionResultAllow()


async def main():
    from backend.tools.mcp_task_scheduler import create_task_scheduler_server

    def stderr_cb(line: str):
        print(f"  [stderr] {line}")

    mcp_servers = {
        "code_index_mcp": {"type": "http", "url": "http://localhost:18085/mcp"},
        "code_ast_mcp": {"type": "http", "url": "http://localhost:18086/mcp"},
        "task_scheduler": create_task_scheduler_server(),
    }

    system_prompt = """你是一位资深 Java 微服务架构师，专职负责**技术方案生成**。

当前时间：2026-02-27
会话 workspace：""" + TEST_CWD + """

## 工作流程

当用户提出功能需求时，你必须严格按照四阶段流水线执行，不可跳步：

**阶段一：语义搜索——获取候选类/方法列表**
- 调用 mcp_code_search 进行语义搜索（top_k=20）
- 记录每条结果的 project、class_fqn、method、相似度分数

**阶段二：调用统计——排名前 10 的高频类**
- 对候选列表中每个类调用 ast_query_call_stats
- 按调用次数降序排名，取 Top 10 类

**阶段三：读取完整代码——写入本地临时文件夹**
- 对 Top 10 类逐个调用 mcp_read_full_file（max_lines=800）
- 用 Write 将源码写入 _code_research/{类名}.java

**阶段四：代码分析——生成技术方案文档**
- 逐一 Read _code_research/ 下的源码文件
- 将技术方案写入 workspace 根目录的 tech_plan.md

## 原则
- 所有结论必须来自真实代码，不得凭类名猜测
"""

    tools = [
        "mcp__code_index_mcp__mcp_code_search",
        "mcp__code_index_mcp__mcp_read_full_file",
        "mcp__code_ast_mcp__ast_list_projects",
        "mcp__code_ast_mcp__ast_query_call_stats",
        "mcp__code_ast_mcp__ast_query_call_chain",
        "Read", "Write", "Skill",
        "mcp__task_scheduler__schedule_delayed_task",
        "mcp__task_scheduler__list_scheduled_tasks",
        "mcp__task_scheduler__delete_scheduled_task",
    ]

    print("=== Test: 精确后端配置 (30s timeout) ===")
    opts = ClaudeAgentOptions(
        model="anthropic/claude-sonnet-4.5",  # 注意：.5 非 -5
        cwd=TEST_CWD,
        system_prompt=system_prompt,
        permission_mode="acceptEdits",
        allowed_tools=tools,
        mcp_servers=mcp_servers,
        can_use_tool=can_use_tool_cb,
        stderr=stderr_cb,
        setting_sources=["project"],
        include_partial_messages=True,
        max_thinking_tokens=10000,
        disallowed_tools=["AskUserQuestion"],
    )
    client = ClaudeSDKClient(options=opts)
    try:
        print("Calling client.connect()...")
        await asyncio.wait_for(client.connect(), timeout=30.0)
        print("SUCCESS: client.connect() completed!")
        print("Sending query...")
        await client.query("Say hello in 1 word", session_id="test-session")
        print("Receiving response...")
        async for msg in client.receive_response():
            print(f"  msg: {type(msg).__name__}: {str(msg)[:80]}")
        await client.disconnect()
        print("DONE!")
    except asyncio.TimeoutError:
        print("TIMEOUT (30s): connect() did not complete in time")
        print("This means query.initialize() is hanging (likely MCP init issue)")
        await client.disconnect()
    except Exception as e:
        print(f"\nFAILED:")
        print(f"  Type: {type(e).__name__}")
        print(f"  repr: {repr(str(e))}")
        print(f"  str: {str(e)!r}")
        print("\nFull traceback:")
        traceback.print_exc()
        cause = e.__cause__
        while cause:
            print(f"  -> caused by {type(cause).__name__}: {repr(str(cause))}")
            cause = cause.__cause__
        try:
            await client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
