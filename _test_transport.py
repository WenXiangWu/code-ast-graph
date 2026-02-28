"""
测试 transport.connect() 是否能独立成功（with can_use_tool -> --permission-prompt-tool stdio）
"""
import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv(r"D:\cursor\bixin-ai-agent-platform\.env")

sys.path.insert(0, r"D:\cursor\bixin-ai-agent-platform")
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ["ANTHROPIC_BASE_URL"] = os.getenv("ANTHROPIC_BASE_URL", "")

from claude_agent_sdk import ClaudeAgentOptions, PermissionResultAllow
from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from dataclasses import replace
import pathlib

TEST_CWD = r"D:\tmp\ai-agent\test-transport"
pathlib.Path(TEST_CWD).mkdir(parents=True, exist_ok=True)


async def can_use_tool_cb(tool_name, tool_input, ctx):
    return PermissionResultAllow()


async def _empty():
    return
    yield {}


async def main():
    opts = ClaudeAgentOptions(
        model="anthropic/claude-sonnet-4-5",
        cwd=TEST_CWD,
        permission_mode="acceptEdits",
        can_use_tool=can_use_tool_cb,
    )
    # 模拟 ClaudeSDKClient.connect() 的内部行为：加入 permission_prompt_tool_name="stdio"
    opts2 = replace(opts, permission_prompt_tool_name="stdio")

    transport = SubprocessCLITransport(prompt=_empty(), options=opts2)
    
    print("Building command...")
    cmd = transport._build_command()
    print("Full command:")
    for part in cmd:
        print(f"  {part!r}")
    
    print("\nCalling transport.connect() with 10s timeout...")
    try:
        await asyncio.wait_for(transport.connect(), timeout=10.0)
        print("SUCCESS: transport.connect() completed in <10s")
        await transport.close()
    except asyncio.TimeoutError:
        print("TIMEOUT: transport.connect() did not complete within 10s")
        print("This means process started OK but stderr_task_group.__aenter__ or something else is hanging")
        await transport.close()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {repr(str(e))}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
