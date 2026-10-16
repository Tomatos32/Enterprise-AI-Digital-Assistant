@echo off
chcp 65001 >nul
title 启动企业级数字员工平台 (前后端)
set "ROOT_DIR=%~dp0"
set "ROOT_DIR=%ROOT_DIR:~0,-1%"

echo =================================================================
echo   🚀 正在拉起企业级 AI 数字员工平台 (FastAPI + Vue3)...
echo =================================================================
echo.

:: 提供前端启动模式选项
echo 请选择前端启动模式：
echo   [1] 启动自研沉浸式 Copilot 界面 (npm run dev) [默认推荐]
echo   [2] 启动 Dify 托管前台模式 (npm run dev:dify)
echo.
set /p UI_CHOICE="请输入选项 [1 或 2] (直接按回车默认选择 1): "

if "%UI_CHOICE%"=="2" (
    set "FRONTEND_CMD=npm run dev:dify"
    set "MODE_NAME=Dify 托管前台模式 (嵌入 Dify WebApp)"
) else (
    set "FRONTEND_CMD=npm run dev"
    set "MODE_NAME=自研沉浸式 Copilot 模式 (Vue3 + LangGraph)"
)

echo.
echo [*] 选择的前端模式: %MODE_NAME%
echo.

:: 1. 启动后端 FastAPI (8000 端口)
echo [*] [1/2] 正在新窗口启动 FastAPI 后端服务 (Port: 8000)...
start "Enterprise-AI: Backend (FastAPI)" cmd /k "chcp 65001 >nul && cd /d "%ROOT_DIR%" && set PYTHONPATH=. && "%ROOT_DIR%\backend\.venv\Scripts\uvicorn.exe" backend.main:app --host 127.0.0.1 --port 8000 --reload"

:: 2. 启动前端 Vite (5173 端口)
echo [*] [2/2] 正在新窗口启动 Vue3 前端工程 (Port: 5173)...
start "Enterprise-AI: Frontend (Vue3)" cmd /k "chcp 65001 >nul && cd /d "%ROOT_DIR%\frontend" && %FRONTEND_CMD%"

echo.
echo =================================================================
echo   🎉 前后端服务已在新终端窗口中成功启动！
echo   👉 浏览器访问:  http://localhost:5173
echo   👉 后端 API 文档: http://127.0.0.1:8000/docs
echo =================================================================
echo 提示: 如需安全终止前后端服务，请运行同目录下的 stop_app.bat
echo.
pause
