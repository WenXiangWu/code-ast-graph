path = 'd:/cursor/bixin-ai-agent-platform/backend/ag_ui_adapter/adapter.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Also patch: add repr() and type() info
old = (
    '                logger.error(f"Connect error traceback:\\n{_tb.format_exc()}")'
)
new = (
    '                logger.error(f"Connect error type: {type(connect_error).__name__}, repr: {repr(connect_error)}")\n'
    '                logger.error(f"Connect error traceback:\\n{_tb.format_exc()}")'
)

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: patched repr/type logging')
else:
    print('NOT FOUND - already patched or different state')
    idx = content.find('format_exc')
    if idx >= 0:
        print(repr(content[idx-50:idx+100]))
