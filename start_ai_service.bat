@echo off
title 启动 AI 底座服务 - Ollama 与 Dify
echo =================================================================
echo   正在启动本地 AI 算力底座 [Ollama + Dify Docker]
echo =================================================================
echo.

echo [*] [1/2] 正在新窗口启动 Ollama 运行 qwen3.5:2b...
start "Ollama-Engine" cmd /k "cd /d G:\Ollama_1\Ollama && set OLLAMA_HOST=0.0.0.0:11434 && set OLLAMA_ORIGINS=* && set OLLAMA_KEEP_ALIVE=-1 && echo 正在加载 qwen3.5:2b 模型... && ollama run qwen3.5:2b"

echo [*] [2/2] 正在启动 Dify Docker 编排集群 [docker compose up -d]...
cd /d "G:\dify\docker"
docker compose up -d

echo.
echo =================================================================
echo   AI 底座服务启动完毕！
echo   - Dify 控制台: http://localhost
echo   - Ollama 端点: http://localhost:11434
echo =================================================================
echo 提示: 如需停止服务，请运行同目录下的 stop_ai_service.bat
echo.
pause
