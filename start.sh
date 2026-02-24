#!/bin/bash
# Code AST Graph - 同时启动前后端
# 用法: ./start.sh  或  bash start.sh
# Windows: 建议用 start.ps1；若用 Git Bash 运行本脚本，会尝试自动加入 Node 路径

set -e
cd "$(dirname "$0")"

# Windows/Git Bash: 若 node 未在 PATH 中，尝试加入常见 Node 安装目录
if ! command -v node >/dev/null 2>&1; then
  for dir in "/c/Program Files/nodejs" "/c/nvm4w/nodejs" "/c/nodejs"; do
    if [ -x "$dir/node.exe" ] 2>/dev/null; then
      export PATH="$dir:$PATH"
      break
    fi
  done
fi

echo "============================================================"
echo "  Code AST Graph - 启动前后端服务"
echo "============================================================"

# 启动后端（后台）
python run.py &
BACKEND_PID=$!
echo "[后端] 已启动 (PID: $BACKEND_PID)"

# 等待后端就绪
echo "[等待] 后端启动中..."
sleep 3

# 退出时清理
cleanup() {
    echo ""
    echo "[清理] 停止后端服务..."
    kill $BACKEND_PID 2>/dev/null || true
    trap - SIGINT SIGTERM EXIT
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 启动前端（前台）
echo "[前端] 启动中..."
cd frontend
if ! command -v node >/dev/null 2>&1; then
  echo "[错误] 未找到 node，请确保已安装 Node.js 且在 PATH 中"
  echo "Windows 用户建议在 PowerShell 中运行: .\\start.ps1"
  kill $BACKEND_PID 2>/dev/null || true
  exit 1
fi
npm run dev
