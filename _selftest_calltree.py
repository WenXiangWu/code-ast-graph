#!/usr/bin/env python3
"""
自测脚本：验证 /api/mcp/query 返回完整调用树
Terminal 267-274
"""
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# 读取后端端口
env_path = Path(__file__).parent / ".env"
port = 18001
for line in env_path.read_text(encoding="utf-8").splitlines():
    if line.startswith("BACKEND_PORT="):
        port = int(line.split("=", 1)[1].strip())
        break

BASE_URL = f"http://localhost:{port}"

def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def print_tree(node, indent=0):
    """递归打印调用树结构"""
    prefix = "  " * indent
    ntype  = node.get("node_type", "?")
    cname  = node.get("class_name") or ""
    mname  = node.get("method_name") or ""
    proj   = node.get("project") or ""
    label  = f"[{ntype}] {proj}.{cname}.{mname}" if mname else f"[{ntype}] {proj}.{cname}"
    print(f"{prefix}{label}")
    for child in node.get("children", []):
        print_tree(child, indent + 1)


def count_nodes(node):
    return 1 + sum(count_nodes(c) for c in node.get("children", []))


print(f"=== 自测 /api/mcp/query  (port={port}) ===\n")

payload = {
    "project":   "official-room-pro-web",
    "class_fqn": "com.yupaopao.chatroom.official.room.web.controller.NobleController",
    "method":    "openNoble",
    "max_depth": 10,
}

try:
    result = post("/api/mcp/query", payload)
except urllib.error.URLError as e:
    print(f"[ERROR] 无法连接后端 {BASE_URL}: {e}")
    sys.exit(1)

print(f"success  : {result.get('success')}")
print(f"message  : {result.get('message')}")

call_tree = result.get("call_tree")
if call_tree:
    total = count_nodes(call_tree)
    print(f"\n调用树节点总数: {total}")
    print("\n--- 调用树结构 ---")
    print_tree(call_tree)
else:
    print("\n[!] call_tree 为空 / None，返回字段列表:")
    print(list(result.keys()))

# 同时测试 /api/mcp/query/stats 对比
print("\n\n=== 对比 /api/mcp/query/stats ===")
stats = post("/api/mcp/query/stats", payload)
print(f"class_stats 数量 : {len(stats.get('class_stats', []))}")
print(f"tables 数量      : {len(stats.get('tables', []))}")
print(f"mq_list 数量     : {len(stats.get('mq_list', []))}")
