"""测试 ClaudeSDKClient 最小启动，定位 Failed to start Claude Code 错误"""
import asyncio
import os
import sys

# 设置环境变量（在 import claude_agent_sdk 前）
os.environ['ANTHROPIC_API_KEY'] = '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'
os.environ['ANTHROPIC_BASE_URL'] = 'https://openrouter.ai/api/v1'  # 修正：加上 v1

sys.path.insert(0, r'd:\cursor\bixin-ai-agent-platform')

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

async def test_minimal():
    print("=== Test 1: 最简配置 ===")
    try:
        opts = ClaudeAgentOptions(
            model="claude-sonnet-4-5",
            cwd=r"D:\tmp\ai-agent\test",
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
        )
        import pathlib; pathlib.Path(r"D:\tmp\ai-agent\test").mkdir(parents=True, exist_ok=True)
        client = ClaudeSDKClient(options=opts)
        await client.connect()
        print("Test 1 PASSED: connect() succeeded")
        await client.disconnect()
    except Exception as e:
        print(f"Test 1 FAILED: {type(e).__name__}: {repr(str(e))}")
    
    print("\n=== Test 2: 带 MCP 配置 ===")
    try:
        opts = ClaudeAgentOptions(
            model="claude-sonnet-4-5",
            cwd=r"D:\tmp\ai-agent\test",
            allowed_tools=["mcp__code_index_mcp__mcp_code_search", "Read"],
            permission_mode="acceptEdits",
            mcp_servers={
                "code_index_mcp": {
                    "type": "http",
                    "url": "http://192.168.24.73:18085/mcp"
                }
            }
        )
        client = ClaudeSDKClient(options=opts)
        await client.connect()
        print("Test 2 PASSED: connect() succeeded")
        await client.disconnect()
    except Exception as e:
        print(f"Test 2 FAILED: {type(e).__name__}: {repr(str(e))}")

    print("\n=== Test 3: anthropic/ 前缀 model ===")
    try:
        opts = ClaudeAgentOptions(
            model="anthropic/claude-sonnet-4-5",
            cwd=r"D:\tmp\ai-agent\test",
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
        )
        client = ClaudeSDKClient(options=opts)
        await client.connect()
        print("Test 3 PASSED: connect() succeeded")
        await client.disconnect()
    except Exception as e:
        print(f"Test 3 FAILED: {type(e).__name__}: {repr(str(e))}")

asyncio.run(test_minimal())
