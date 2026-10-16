@echo off
chcp 65001 >nul
title 停止 AI 底座服务 (Ollama + Dify)
echo =================================================================
echo   🛑 正在停止 AI 算力底座 (Dify 容器集群 + Ollama 引擎)...
echo =================================================================
echo.

:: 1. 停止并释放 Dify Docker 容器
echo [*] [1/2] 正在停止 Dify Docker 容器集群 (docker compose down)...
cd /d "G:\dify\docker"
docker compose down

:: 2. 卸载 Ollama 模型显存占用并关闭进程
echo [*] [2/2] 正在释放 Ollama 显存并关闭会话窗口...
cd /d "G:\Ollama_1\Ollama"
ollama.exe stop qwen3.5:2b 2>nul
taskkill /f /fi "WINDOWTITLE eq AI-Engine: Ollama (qwen3.5:2b)*" 2>nul

echo.
echo =================================================================
echo   [√] Dify 容器集群已安全停止，Ollama 模型显存已成功卸载！
echo =================================================================
echo.
pause
