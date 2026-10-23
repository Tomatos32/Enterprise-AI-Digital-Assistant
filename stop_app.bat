@echo off
title 停止企业级数字员工平台 - 前后端服务
echo =================================================================
echo   正在停止前后端服务 [FastAPI + Vue3]...
echo =================================================================
echo.

echo [*] 正在停止后端端口 8000 对应进程...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do (
    echo     正在终止后端进程 PID: %%a
    taskkill /f /pid %%a 2>nul
)

echo [*] 正在停止前端端口 3000 对应进程...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING" 2^>nul') do (
    echo     正在终止前端进程 PID: %%a
    taskkill /f /pid %%a 2>nul
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul
)

echo [*] 正在关闭前后端终端窗口...
taskkill /f /fi "WINDOWTITLE eq Backend-FastAPI*" 2>nul
taskkill /f /fi "WINDOWTITLE eq Frontend-Vue3*" 2>nul

echo.
echo =================================================================
echo   前后端服务进程已全部停止，端口 8000 与 3000 已释放！
echo =================================================================
echo.
pause
