"""
完整测试 client.connect() with can_use_tool
捕获完整的异常链和 traceback
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

TEST_CWD = r"D:\tmp\ai-agent\test-full-connect"
pathlib.Path(TEST_CWD).mkdir(parents=True, exist_ok=True)


async def can_use_tool_cb(tool_name, tool_input, ctx: ToolPermissionContext):
    print(f"  [can_use_tool] {tool_name}")
    return PermissionResultAllow()


async def main():
    print("=== Test: client.connect() with can_use_tool (30s timeout) ===")
    opts = ClaudeAgentOptions(
        model="anthropic/claude-sonnet-4-5",
        cwd=TEST_CWD,
        permission_mode="acceptEdits",
        can_use_tool=can_use_tool_cb,
        include_partial_messages=True,
    )
    client = ClaudeSDKClient(options=opts)
    try:
        await asyncio.wait_for(client.connect(), timeout=30.0)
        print("SUCCESS: client.connect() completed!")
        
        # 发送一个简单查询
        print("Sending query...")
        await client.query("Say hello in 1 word", session_id="test-session")
        
        print("Receiving response...")
        async for msg in client.receive_response():
            print(f"  msg: {type(msg).__name__}: {str(msg)[:100]}")
        
        await client.disconnect()
    except asyncio.TimeoutError:
        print("TIMEOUT (30s): client.connect() or receive did not complete in time")
        print("This suggests query.initialize() is waiting for CLI control protocol response")
        await client.disconnect()
    except Exception as e:
        print(f"\nFAILED:")
        print(f"  Type: {type(e).__name__}")
        print(f"  repr: {repr(str(e))}")
        print(f"  str: {str(e)!r}")
        print("\nFull traceback:")
        traceback.print_exc()
        print("\nException chain:")
        cause = e.__cause__
        while cause:
            print(f"  -> {type(cause).__name__}: {repr(str(cause))}")
            cause = cause.__cause__
        try:
            await client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
