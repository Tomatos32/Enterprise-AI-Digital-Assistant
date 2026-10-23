@echo off
title 启动 AI 底座服务 - Ollama 与 Dify
echo =================================================================
echo   正在启动本地 AI 算力底座 [Ollama + Dify Docker]
echo =================================================================
echo.

:: 1. 启动 Ollama 并运行 qwen3.5:2b 模型
echo [*] [1/2] 正在新窗口启动 Ollama 运行 qwen3.5:2b...
start "Ollama-Engine" cmd /k "cd /d G:\Ollama_1\Ollama && set OLLAMA_HOST=0.0.0.0:11434 && set OLLAMA_ORIGINS=* && set OLLAMA_KEEP_ALIVE=-1 && echo 正在加载 qwen3.5:2b 模型... && ollama run qwen3.5:2b"

:: 2. 检查 Docker 守护进程连通性
echo [*] [2/2] 正在检查 Docker 引擎运行状态...
docker info >nul 2>nul
if %errorlevel% equ 0 goto DOCKER_ALREADY_RUNNING

echo [*] 检测到 Docker 守护进程未启动，正在尝试唤醒 Docker Desktop...
if not exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" goto DOCKER_NOT_FOUND

start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo [*] 已向系统发出 Docker Desktop 启动指令，正在等待 Docker 引擎就绪...
echo [*] 首次启动冷拉起通常需要 15 到 35 秒，请耐心稍候...
goto WAIT_DOCKER_INIT

:DOCKER_NOT_FOUND
echo [-] 未在默认路径发现 Docker Desktop，请确保已安装并启动 Docker。
goto WAIT_DOCKER_INIT

:WAIT_DOCKER_INIT
set WAIT_COUNT=0

:WAIT_DOCKER_LOOP
timeout /t 3 /nobreak >nul
set /a WAIT_COUNT+=3
docker info >nul 2>nul
if %errorlevel% equ 0 goto DOCKER_SUCCESS
if %WAIT_COUNT% geq 60 goto DOCKER_TIMEOUT
echo [*] Docker 正在后台初始化中... 已等待 %WAIT_COUNT% 秒 / 60 秒
goto WAIT_DOCKER_LOOP

:DOCKER_SUCCESS
echo [*] Docker 引擎已成功就绪！耗时约 %WAIT_COUNT% 秒。
goto DOCKER_DEPLOY

:DOCKER_ALREADY_RUNNING
echo [*] Docker 引擎已处于就绪运行状态。
goto DOCKER_DEPLOY

:DOCKER_DEPLOY
echo [*] 正在启动 Dify Docker 编排集群 [docker compose up -d]...
cd /d "G:\dify\docker"
docker compose up -d
goto SUMMARY

:DOCKER_TIMEOUT
echo.
echo =================================================================
echo   [-] 警告: Docker 引擎等待超时 (60秒)。
echo   可能的原因：
echo   1. Docker Desktop 仍在后台初始化中；
echo   2. 本地虚拟化引擎 (WSL2 / Hyper-V) 启动较慢。
echo   建议：请检查任务栏右下角 Docker 鲸鱼图标是否变为绿色 (Engine running)，
echo         然后再运行此脚本，或者按任意键继续。
echo =================================================================
echo.
pause
goto SUMMARY

:SUMMARY
echo.
echo =================================================================
echo   AI 底座服务启动完毕！
echo   - Dify 控制台: http://localhost
echo   - Ollama 端点: http://localhost:11434
echo =================================================================
echo 提示: 如需停止服务，请运行同目录下的 stop_ai_service.bat
echo.
pause
