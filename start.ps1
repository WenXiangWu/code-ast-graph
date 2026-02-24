# Code AST Graph - 同时启动前后端
# 用法: .\start.ps1  或  powershell -File start.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Code AST Graph - 启动前后端服务" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 启动后端（后台进程）
$backendProcess = Start-Process -FilePath "python" -ArgumentList "run.py" `
    -WorkingDirectory $ProjectRoot `
    -PassThru `
    -NoNewWindow

Write-Host "[后端] 已启动 (PID: $($backendProcess.Id))" -ForegroundColor Blue

# 等待后端就绪
Write-Host "[等待] 后端启动中..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    # 启动前端（前台，占用当前终端）
    Write-Host "[前端] 启动中..." -ForegroundColor Green
    Set-Location (Join-Path $ProjectRoot "frontend")
    npm run dev
}
finally {
    # 退出时停止后端
    if ($backendProcess -and !$backendProcess.HasExited) {
        Write-Host "`n[清理] 停止后端服务 (PID: $($backendProcess.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
