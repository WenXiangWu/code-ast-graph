#!/usr/bin/env python3
"""
Code AST Graph - 代码知识图谱分析工具
启动脚本 - 同时启动 FastAPI 后端 + MCP Server
"""

import os
import sys
import signal
import subprocess
import atexit
from pathlib import Path

# 设置 UTF-8 编码（Windows 兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

# 导入并启动后端服务
import uvicorn
from backend.main import app

_mcp_proc: subprocess.Popen | None = None


def _start_mcp_server(mcp_port: int) -> subprocess.Popen | None:
    """后台启动 MCP server，返回进程对象"""
    cmd = [
        sys.executable, "-m", "backend.mcp_server",
        "--port", str(mcp_port)
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        print(f"[MCP Server] 已启动 (PID: {proc.pid})，端口: {mcp_port}")
        print(f"[MCP Server] 访问入口: http://localhost:{mcp_port}/mcp")
        return proc
    except Exception as e:
        print(f"[MCP Server] 启动失败: {e}")
        return None


def _cleanup_mcp():
    """退出时清理 MCP server 进程"""
    global _mcp_proc
    if _mcp_proc and _mcp_proc.poll() is None:
        print(f"\n[清理] 停止 MCP Server (PID: {_mcp_proc.pid})...")
        _mcp_proc.terminate()
        try:
            _mcp_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _mcp_proc.kill()


if __name__ == "__main__":
    backend_port = int(os.getenv("BACKEND_PORT", "18001"))
    mcp_port = int(os.getenv("MCP_PORT", "18086"))
    frontend_port = os.getenv("FRONTEND_PORT", "3001")

    print("=" * 60)
    print("  Code AST Graph - 启动服务")
    print("=" * 60)
    print(f"  • FastAPI 后端 : http://localhost:{backend_port}")
    print(f"  • API 文档     : http://localhost:{backend_port}/docs")
    print(f"  • MCP Server   : http://localhost:{mcp_port}/mcp")
    print(f"  • 前端应用     : http://localhost:{frontend_port}  (需单独启动)")
    print("=" * 60)

    # 启动 MCP server（后台子进程）
    _mcp_proc = _start_mcp_server(mcp_port)
    atexit.register(_cleanup_mcp)

    # Windows 下 SIGTERM 不存在，仅注册 SIGINT
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, lambda *_: (_cleanup_mcp(), sys.exit(0)))

    # 启动 FastAPI 主服务（阻塞）
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=backend_port,
        log_level="info"
    )
