"""验证两个 MCP 服务是否在线"""
import urllib.request
import json

SERVICES = {
    "code_index_mcp": "http://192.168.24.73:18085/mcp",
    "code_ast_mcp":   "http://192.168.24.73:18086/mcp",
}

INIT_BODY = json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "check-script", "version": "1.0"}
    }
}).encode()

def check(name, url):
    try:
        req = urllib.request.Request(
            url,
            data=INIT_BODY,
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            status = r.status
            raw = r.read().decode()
        # 解析 data: 行
        for line in raw.splitlines():
            if line.startswith("data:"):
                payload = json.loads(line[5:].strip())
                server_name = payload.get("result", {}).get("serverInfo", {}).get("name", "?")
                proto = payload.get("result", {}).get("protocolVersion", "?")
                print(f"  [{name}] ✓ HTTP {status} | server={server_name} | protocol={proto}")
                return True
        print(f"  [{name}] ✓ HTTP {status} | (no data: line in response)")
        return True
    except Exception as e:
        print(f"  [{name}] ✗ FAILED: {e}")
        return False

print("=== MCP 服务在线检查 ===")
results = {}
for name, url in SERVICES.items():
    print(f"  检查 {url} ...")
    results[name] = check(name, url)

print()
if all(results.values()):
    print("✅ 两个 MCP 服务均在线，可以启动平台测试")
else:
    failed = [k for k, v in results.items() if not v]
    print(f"❌ 以下服务不在线，需先启动：{failed}")
