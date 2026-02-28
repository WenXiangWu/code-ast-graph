import urllib.request, json, re

base = "http://localhost:18086/mcp"
H = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Host": "10.72.97.76:18086",
}

def post(payload):
    req = urllib.request.Request(base, data=json.dumps(payload).encode(), headers=H)
    resp = urllib.request.urlopen(req)
    body = resp.read().decode()
    return resp.status, body

# Step 1: initialize
status, body = post({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    }
})
print(f"[initialize] status={status}")

# Step 2: tools/list (stateless - no session id needed)
status, body = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
tools = [m.group(1) for m in re.finditer(r'"name":"([^"]+)"', body)]
print(f"[tools/list] status={status}, tools={tools}")

# Step 3: call ast_list_projects
status, body = post({
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {"name": "ast_list_projects", "arguments": {}}
})
print(f"[ast_list_projects] status={status}")
data_match = re.search(r'data: (.+)', body)
if data_match:
    rpc = json.loads(data_match.group(1))
    content = rpc.get("result", {}).get("content", [])
    if content:
        inner = json.loads(content[0].get("text", "{}"))
        print(f"  projects total: {inner.get('total', 0)}")
        for p in inner.get("projects", [])[:3]:
            print(f"    - {p['name']}")
