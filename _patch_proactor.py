patch_target = 'd:/cursor/bixin-ai-agent-platform/backend/main.py'
with open(patch_target, encoding='utf-8') as f:
    content = f.read()

# 1. 在 import asyncio 后插入 Windows ProactorEventLoop 策略（模块级）
old1 = 'import asyncio\nimport logging'
new1 = (
    'import asyncio\n'
    'import sys\n'
    '# Windows: SelectorEventLoop does not support subprocesses; force ProactorEventLoop\n'
    'if sys.platform == "win32":\n'
    '    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())\n'
    'import logging'
)

# 2. 在 uvicorn.run 调用前也加一次（保险：reload模式下worker子进程可能reset策略）
old2 = (
    'def main():\n'
    '    """Run the server."""\n'
    '    # 检查 API Key（使用配置中的值，已有内置默认值）\n'
    '    if not settings.anthropic_api_key:'
)
new2 = (
    'def main():\n'
    '    """Run the server."""\n'
    '    # Windows: ensure ProactorEventLoop for subprocess support\n'
    '    if sys.platform == "win32":\n'
    '        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())\n'
    '    # 检查 API Key（使用配置中的值，已有内置默认值）\n'
    '    if not settings.anthropic_api_key:'
)

patched = False
if old1 in content:
    content = content.replace(old1, new1, 1)
    patched = True
    print('Patch 1 (module-level policy): OK')
else:
    print('Patch 1 NOT FOUND')
    # fallback: try without sys already imported
    old1b = 'import asyncio\n'
    idx = content.find(old1b)
    print(f'  "import asyncio" found at index: {idx}')
    print(repr(content[idx:idx+60]))

if old2 in content:
    content = content.replace(old2, new2, 1)
    print('Patch 2 (main() policy): OK')
else:
    print('Patch 2 NOT FOUND')
    idx2 = content.find('def main():')
    if idx2 >= 0:
        print(repr(content[idx2:idx2+200]))

if patched:
    with open(patch_target, 'w', encoding='utf-8') as f:
        f.write(content)
    print('File written.')
