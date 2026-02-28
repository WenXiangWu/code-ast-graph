"""
在 base_agent.py 中，加载完 mcp_servers 后，
为所有 HTTP 类型的 MCP 服务器注入 timeout=120000ms（2分钟），
防止 Claude CLI 端在向量搜索返回前就超时放弃。
"""

path = 'd:/cursor/bixin-ai-agent-platform/backend/agents/base_agent.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

# 在 mcp_servers 赋值后（load_mcp_config 调用后）注入 timeout
# 找到 "if mcp_servers:" 前的空行并插入 timeout 注入逻辑
old = (
    '    if mcp_servers:\n'
    '        options_kwargs["mcp_servers"] = mcp_servers\n'
    '        logger.info(f"MCP servers configured: {list(mcp_servers.keys())}, auth={\'yes\' if auth_token else \'no\'}")'
)
new = (
    '    # 为 HTTP 类型 MCP 服务器注入超时时间（120s），避免向量搜索等慢操作被 Claude CLI 提前超时\n'
    '    for _srv_name, _srv_cfg in mcp_servers.items():\n'
    '        if isinstance(_srv_cfg, dict) and _srv_cfg.get("type") == "http":\n'
    '            if "timeout" not in _srv_cfg:\n'
    '                _srv_cfg["timeout"] = 120000  # ms\n'
    '                logger.debug(f"Injected timeout=120000ms for HTTP MCP server: {_srv_name}")\n'
    '\n'
    '    if mcp_servers:\n'
    '        options_kwargs["mcp_servers"] = mcp_servers\n'
    '        logger.info(f"MCP servers configured: {list(mcp_servers.keys())}, auth={\'yes\' if auth_token else \'no\'}")'
)

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: timeout injection patched into base_agent.py')
else:
    print('NOT FOUND')
    idx = content.find('if mcp_servers:')
    if idx >= 0:
        print(repr(content[idx:idx+200]))
