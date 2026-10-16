@echo off
chcp 65001 >nul
title 启动 AI 底座服务 (Ollama + Dify)
echo =================================================================
echo   🚀 正在拉起本地 AI 算力底座 (Ollama qwen3.5:2b + Dify 容器)...
echo =================================================================
echo.

:: 1. 配置 Ollama 环境变量（确保跨容器/跨域通信畅通）
set OLLAMA_HOST=0.0.0.0:11434
set OLLAMA_ORIGINS=*
set OLLAMA_KEEP_ALIVE=-1

:: 2. 拉起 Ollama 并加载 qwen3.5:2b 模型
echo [*] [1/2] 正在新窗口启动 Ollama 并运行 qwen3.5:2b 模型...
start "AI-Engine: Ollama (qwen3.5:2b)" cmd /k "chcp 65001 >nul && cd /d G:\Ollama_1\Ollama && set OLLAMA_HOST=0.0.0.0:11434 && set OLLAMA_ORIGINS=* && set OLLAMA_KEEP_ALIVE=-1 && echo 正在加载模型 qwen3.5:2b... && ollama.exe run qwen3.5:2b"

:: 3. 切换至 Dify docker 目录启动容器编排
echo [*] [2/2] 正在启动 Dify Docker 编排集群 (docker compose up -d)...
cd /d "G:\dify\docker"
docker compose up -d

echo.
echo =================================================================
echo   🎉 AI 底座服务启动完毕！
echo   👉 Dify 控制台: http://localhost
echo   👉 Dify WebApp: http://localhost/chat/wG0kGeUGzYwpQ8uw
echo   👉 Ollama 端点: http://localhost:11434
echo =================================================================
echo 提示: 如需停止服务，请直接运行同目录下的 stop_ai_service.bat
echo.
pause
