import re

path = 'd:/cursor/bixin-ai-agent-platform/backend/ag_ui_adapter/adapter.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

old = (
    '            except Exception as connect_error:\n'
    '                error_msg = str(connect_error)\n'
    '                logger.error(f"Failed to connect to Claude SDK: {error_msg}")'
)
new = (
    '            except Exception as connect_error:\n'
    '                import traceback as _tb\n'
    '                error_msg = str(connect_error)\n'
    '                logger.error(f"Failed to connect to Claude SDK: {error_msg}")\n'
    '                logger.error(f"Connect error traceback:\\n{_tb.format_exc()}")'
)

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: patched')
else:
    # Try to find roughly where the except block is
    idx = content.find('except Exception as connect_error:')
    print(f'NOT FOUND. "except Exception as connect_error:" at index: {idx}')
    if idx >= 0:
        print(repr(content[idx:idx+300]))
