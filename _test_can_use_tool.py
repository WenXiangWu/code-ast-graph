"""
复现后端确切行为的测试：
当 can_use_tool 被设置时，SDK 会自动加入 --permission-prompt-tool stdio
测试这个配置是否会导致 connect() 失败
"""
import asyncio
import os
import sys

# 设置环境变量（在 import claude_agent_sdk 前）
from dotenv import load_dotenv
load_dotenv(r"D:\cursor\bixin-ai-agent-platform\.env")

sys.path.insert(0, r"D:\cursor\bixin-ai-agent-platform")
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ["ANTHROPIC_BASE_URL"] = os.getenv("ANTHROPIC_BASE_URL", "")

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow
from claude_agent_sdk.types import ToolPermissionContext
import pathlib

TEST_CWD = r"D:\tmp\ai-agent\test-can-use-tool"
pathlib.Path(TEST_CWD).mkdir(parents=True, exist_ok=True)

async def can_use_tool_callback(tool_name, tool_input, context: ToolPermissionContext):
    print(f"  [can_use_tool] {tool_name}")
    return PermissionResultAllow()


async def test_with_can_use_tool():
    print("\n=== Test 1: 带 can_use_tool 的最简配置 ===")
    try:
        opts = ClaudeAgentOptions(
            model="anthropic/claude-sonnet-4-5",
            cwd=TEST_CWD,
            permission_mode="acceptEdits",
            can_use_tool=can_use_tool_callback,
        )
        client = ClaudeSDKClient(options=opts)
        await client.connect()
        print("PASSED: connect() succeeded with can_use_tool")
        await client.disconnect()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {repr(str(e))}")
        import traceback; traceback.print_exc()

    print("\n=== Test 2: 带 can_use_tool + stderr 回调 ===")
    try:
        def stderr_cb(line: str):
            print(f"  [stderr] {line}")

        opts = ClaudeAgentOptions(
            model="anthropic/claude-sonnet-4-5",
            cwd=TEST_CWD,
            permission_mode="acceptEdits",
            can_use_tool=can_use_tool_callback,
            stderr=stderr_cb,
        )
        client = ClaudeSDKClient(options=opts)
        await client.connect()
        print("PASSED: connect() succeeded with can_use_tool + stderr")
        await client.disconnect()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {repr(str(e))}")
        import traceback; traceback.print_exc()

    print("\n=== Test 3: 完整后端配置（含 MCP servers） ===")
    try:
        def stderr_cb2(line: str):
            print(f"  [stderr] {line}")

        mcp_servers = {
            "code_index_mcp": {"type": "http", "url": "http://localhost:18085/mcp"},
            "code_ast_mcp": {"type": "http", "url": "http://localhost:18086/mcp"},
        }
        from backend.tools.mcp_task_scheduler import create_task_scheduler_server
        mcp_servers["task_scheduler"] = create_task_scheduler_server()

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

        system_prompt = "你是一位资深 Java 微服务架构师，专职负责技术方案生成。"

        opts = ClaudeAgentOptions(
            model="anthropic/claude-sonnet-4-5",
            cwd=TEST_CWD,
            system_prompt=system_prompt,
            permission_mode="acceptEdits",
            allowed_tools=tools,
            mcp_servers=mcp_servers,
            can_use_tool=can_use_tool_callback,
            stderr=stderr_cb2,
            setting_sources=["project"],
            include_partial_messages=True,
            max_thinking_tokens=10000,
            disallowed_tools=["AskUserQuestion"],
        )
        client = ClaudeSDKClient(options=opts)
        await client.connect()
        print("PASSED: connect() succeeded with full backend config")
        await client.disconnect()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {repr(str(e))}")
        import traceback; traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_with_can_use_tool())
