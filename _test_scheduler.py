"""测试带 task_scheduler SDK MCP server 的配置"""
import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)

os.environ['ANTHROPIC_API_KEY'] = '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'
os.environ['ANTHROPIC_BASE_URL'] = 'https://openrouter.ai/api/v1'

sys.path.insert(0, r'd:\cursor\bixin-ai-agent-platform')

async def test_with_scheduler():
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
    from backend.tools.mcp_task_scheduler import create_task_scheduler_server
    
    task_scheduler_server = create_task_scheduler_server()
    print("task_scheduler server config type:", type(task_scheduler_server))
    print("task_scheduler server config:", str(task_scheduler_server)[:200])
    
    print("\n=== Test: 带 task_scheduler SDK MCP server ===")
    try:
        mcp_servers = {
            "code_index_mcp": {"type": "http", "url": "http://192.168.24.73:18085/mcp"},
            "code_ast_mcp": {"type": "http", "url": "http://192.168.24.73:18086/mcp"},
            "task_scheduler": task_scheduler_server,
        }
        opts = ClaudeAgentOptions(
            model="anthropic/claude-sonnet-4-5",
            cwd=r"D:\tmp\ai-agent\test",
            allowed_tools=["mcp__code_index_mcp__mcp_code_search", "Read", "Write"],
            permission_mode="acceptEdits",
            mcp_servers=mcp_servers,
            max_thinking_tokens=10000,
            setting_sources=["project"],
        )
        import pathlib; pathlib.Path(r"D:\tmp\ai-agent\test").mkdir(parents=True, exist_ok=True)
        client = ClaudeSDKClient(options=opts)
        await client.connect()
        print("PASSED: connect() succeeded with task_scheduler")
        await client.disconnect()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {repr(str(e))}")
        import traceback; traceback.print_exc()

asyncio.run(test_with_scheduler())
