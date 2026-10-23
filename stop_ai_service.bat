@echo off
title 停止 AI 底座服务 - Ollama 与 Dify
echo =================================================================
echo   正在停止 AI 算力底座 [Dify 容器集群 + Ollama 引擎]...
echo =================================================================
echo.

:: 1. 检查 Docker 状态并停止 Dify
echo [*] [1/2] 正在检查 Docker 容器集群...
docker info >nul 2>nul
if %errorlevel% equ 0 goto STOP_DIFY
echo [*] Docker 引擎未在运行，已跳过 Dify 容器关闭。
goto STOP_OLLAMA

:STOP_DIFY
echo [*] 正在停止 Dify Docker 容器集群 [docker compose down]...
cd /d "G:\dify\docker"
docker compose down

:STOP_OLLAMA
:: 2. 释放 Ollama 模型显存占用并关闭终端窗口
echo [*] [2/2] 正在释放 Ollama 显存并关闭终端窗口...
cd /d "G:\Ollama_1\Ollama"
ollama stop qwen3.5:2b 2>nul
taskkill /f /fi "WINDOWTITLE eq Ollama-Engine*" 2>nul

echo.
echo =================================================================
echo   AI 算力底座已安全停止，Ollama 显存已释放！
echo =================================================================
echo.
pause
