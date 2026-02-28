path = 'd:/cursor/bixin-ai-agent-platform/backend/main.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Fix: pass loop="none" so uvicorn doesn't override Python 3.8+ default ProactorEventLoop
old = (
    '    uvicorn.run(\n'
    '        "backend.main:app",\n'
    '        host=settings.host,\n'
    '        port=settings.port,\n'
    '        reload=True,\n'
    '        log_level=settings.log_level.lower(),\n'
    '        timeout_graceful_shutdown=3,  # Force shutdown after 3 seconds if connections don\'t close\n'
    '    )'
)
new = (
    '    uvicorn.run(\n'
    '        "backend.main:app",\n'
    '        host=settings.host,\n'
    '        port=settings.port,\n'
    '        reload=True,\n'
    '        log_level=settings.log_level.lower(),\n'
    '        timeout_graceful_shutdown=3,  # Force shutdown after 3 seconds if connections don\'t close\n'
    '        loop="none",  # Windows: let Python 3.8+ default ProactorEventLoop be used (subprocess support)\n'
    '    )'
)

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: loop="none" patched into uvicorn.run()')
else:
    print('NOT FOUND - showing uvicorn.run context:')
    idx = content.find('uvicorn.run(')
    if idx >= 0:
        print(repr(content[idx:idx+400]))
