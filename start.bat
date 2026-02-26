@echo off
chcp 65001 > nul
echo ============================================================
echo 🚀 Code AST Graph 一键启动脚本
echo ============================================================
echo.

echo [1/3] 启动 Neo4j...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ❌ Neo4j 启动失败
    pause
    exit /b 1
)

echo.
echo [2/3] 等待 Neo4j 完全启动（约 30 秒）...
timeout /t 30 /nobreak > nul

echo.
echo [3/3] 检查 Neo4j 连接...
python test_neo4j_connection.py
if %errorlevel% neq 0 (
    echo ⚠️  Neo4j 可能还在启动中，请稍后再试
    echo 可以运行: docker-compose logs -f neo4j
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅ Neo4j 启动成功！
echo ============================================================
echo.
echo 服务地址:
echo   • Neo4j Browser: http://localhost:17474
echo   • Neo4j Bolt:    bolt://localhost:17687
echo   • 用户名: neo4j
echo   • 密码: jqassistant123
echo.
echo 下一步:
echo   1. 启动后端: python run.py
echo   2. 启动前端: cd frontend ^&^& npm run dev
echo   3. 导入项目: 访问前端界面操作
echo ============================================================
pause
