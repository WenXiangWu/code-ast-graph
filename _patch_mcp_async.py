"""
修复 code-index-demo/main/mcp_server.py:
  mcp_code_search 和 mcp_read_full_file 中的同步阻塞调用
  改为 asyncio.to_thread() 包装，避免阻塞 FastMCP 的 asyncio 事件循环
"""
import asyncio

path = 'd:/cursor/code-index-demo/main/mcp_server.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

# --- 1. 在 import json 后加 import asyncio ---
old_import = 'import json\nimport logging'
new_import = 'import asyncio\nimport json\nimport logging'

if old_import in content:
    content = content.replace(old_import, new_import, 1)
    print('Patch 1 (import asyncio): OK')
else:
    print('Patch 1 NOT FOUND - checking existing imports...')
    if 'import asyncio' in content:
        print('  asyncio already imported, skip')
    else:
        print('  MANUAL FIX NEEDED')

# --- 2. mcp_code_search: 同步调用改 asyncio.to_thread ---
old_search = (
    '    result = mcp_search(\n'
    '        query=query,\n'
    '        project=project if project and project not in ("", "全部项目") else None,\n'
    '        top_k=top_k,\n'
    '        filter_mode=filter_mode,\n'
    '    )\n'
    '    return json.dumps(result, ensure_ascii=False, default=str)'
)
new_search = (
    '    # 注意：mcp_search() 内部含 model.encode() 和 psycopg2 同步 I/O，\n'
    '    # 必须放入线程池以避免阻塞 FastMCP 的 asyncio 事件循环（否则 HTTP 响应被挂起）\n'
    '    result = await asyncio.to_thread(\n'
    '        mcp_search,\n'
    '        query=query,\n'
    '        project=project if project and project not in ("", "全部项目") else None,\n'
    '        top_k=top_k,\n'
    '        filter_mode=filter_mode,\n'
    '    )\n'
    '    return json.dumps(result, ensure_ascii=False, default=str)'
)

if old_search in content:
    content = content.replace(old_search, new_search, 1)
    print('Patch 2 (mcp_code_search -> to_thread): OK')
else:
    print('Patch 2 NOT FOUND')
    idx = content.find('result = mcp_search')
    if idx >= 0:
        print(repr(content[idx:idx+200]))

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('File written.')
