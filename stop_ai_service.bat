@echo off
title 停止 AI 底座服务 - Ollama 与 Dify
echo =================================================================
echo   正在停止 AI 算力底座 [Dify 容器集群 + Ollama 引擎]...
echo =================================================================
echo.

echo [*] [1/2] 正在停止 Dify Docker 容器集群 [docker compose down]...
cd /d "G:\dify\docker"
docker compose down

echo [*] [2/2] 正在释放 Ollama 显存并关闭终端窗口...
cd /d "G:\Ollama_1\Ollama"
ollama stop qwen3.5:2b 2>nul
taskkill /f /fi "WINDOWTITLE eq Ollama-Engine*" 2>nul

echo.
echo =================================================================
echo   Dify 容器集群已安全停止，Ollama 显存已释放！
echo =================================================================
echo.
pause
