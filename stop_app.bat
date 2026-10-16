@echo off
chcp 65001 >nul
title 停止企业级数字员工平台 (前后端)
echo =================================================================
echo   🛑 正在停止企业级 AI 数字员工平台 (后端 FastAPI + 前端 Vue3)...
echo =================================================================
echo.

:: 1. 精准终止 8000 端口 (FastAPI 后端)
echo [*] 正在释放后端端口 8000 对应进程...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do (
    echo     正在终止进程 PID: %%a
    taskkill /f /pid %%a 2>nul
)

:: 2. 精准终止 5173 端口 (Vite 前端)
echo [*] 正在释放前端端口 5173 对应进程...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING" 2^>nul') do (
    echo     正在终止进程 PID: %%a
    taskkill /f /pid %%a 2>nul
)

:: 3. 备用安全检查：释放 3000 端口 (若有旧残留)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul
)

:: 4. 关闭对应的终端窗口
echo [*] 正在关闭前后端终端窗口...
taskkill /f /fi "WINDOWTITLE eq Enterprise-AI: Backend*" 2>nul
taskkill /f /fi "WINDOWTITLE eq Enterprise-AI: Frontend*" 2>nul

echo.
echo =================================================================
echo   [√] 前端与后端服务进程已全部安全停止！端口 8000 与 5173 已释放。
echo =================================================================
echo.
pause
