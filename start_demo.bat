@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -File "%~dp0start_demo.ps1" %*
if %errorlevel% neq 0 pause
