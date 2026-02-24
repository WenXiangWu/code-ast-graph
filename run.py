#!/usr/bin/env python3
"""
Code AST Graph - 代码知识图谱分析工具
启动脚本 - 启动 FastAPI 后端服务
"""

import os
import sys
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

if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", "8000"))
    print("=" * 60)
    print("🚀 Code AST Graph 后端服务启动中...")
    print("=" * 60)
    print("访问地址:")
    print(f"  • API 文档: http://localhost:{port}/docs")
    print(f"  • API: http://localhost:{port}")
    print("=" * 60)
    frontend_port = os.getenv("FRONTEND_PORT", "3000")
    print(f"前端应用请单独启动: cd frontend && npm run dev (端口: {frontend_port})")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
