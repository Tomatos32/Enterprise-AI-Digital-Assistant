@echo off
title 启动企业级数字员工平台 - 前后端服务
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

echo =================================================================
echo   正在启动企业级 AI 数字员工平台 [FastAPI + Vue3]
echo =================================================================
echo.

echo 请选择前端启动模式：
echo   [1] 启动自研沉浸式 Copilot 界面 [默认推荐]
echo   [2] 启动 Dify 托管前台模式
echo.
set "UI_CHOICE=1"
set /p UI_CHOICE="请输入选项 1 或 2 (直接回车默认选择 1): "

if "%UI_CHOICE%"=="2" goto SELECT_DIFY
set "FRONTEND_CMD=npm run dev"
set "MODE_NAME=自研沉浸式 Copilot 模式"
goto START_SERVICES

:SELECT_DIFY
set "FRONTEND_CMD=npm run dev:dify"
set "MODE_NAME=Dify 托管前台模式"

:START_SERVICES
echo.
echo [*] 已选择前端模式: %MODE_NAME%
echo.

echo [*] [1/2] 正在新窗口启动 FastAPI 后端服务 [端口: 8000]...
start "Backend-FastAPI" cmd /k "cd /d %ROOT_DIR% && set PYTHONPATH=. && %ROOT_DIR%\backend\.venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000 --reload"

echo [*] [2/2] 正在新窗口启动 Vue3 前端服务 [端口: 5173]...
start "Frontend-Vue3" cmd /k "cd /d %ROOT_DIR%\frontend && %FRONTEND_CMD%"

echo.
echo =================================================================
echo   前后端服务已在新窗口中成功拉起！
echo   - 前端访问地址:   http://localhost:5173
echo   - 后端 API 文档:  http://127.0.0.1:8000/docs
echo =================================================================
echo 提示: 如需停止前后端服务，请运行同目录下的 stop_app.bat
echo.
pause
