# Enterprise AI Digital Assistant - Interactive Demo Launcher (PowerShell)
param(
    [string]$Mode = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RootDir

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   🚀 企业级 AI 数字人助手 - 交互 Demo 启动器" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$PythonExe = Join-Path $RootDir "backend\.venv\Scripts\python.exe"
$UvicornExe = Join-Path $RootDir "backend\.venv\Scripts\uvicorn.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[-] 未找到虚拟环境 Python: $PythonExe" -ForegroundColor Red
    exit 1
}

# 交互式选择菜单（如果未传入 -Mode 参数）
if (-not $Mode) {
    Write-Host "请选择需要启动的交互模式：" -ForegroundColor Yellow
    Write-Host "  [1] 启动完整 Web UI 实时交互 (FastAPI + Vue3 界面) [默认]" -ForegroundColor Green
    Write-Host "  [2] 运行 CLI 端到端全链路闭环自动化演练脚本"
    Write-Host "  [3] 仅启动 FastAPI 后端服务 (访问 http://127.0.0.1:8000/docs)"
    Write-Host "-----------------------------------------------------------------" -ForegroundColor Gray
    try {
        $choice = Read-Host "请输入编号 [1-3] (直接按回车默认选择 1)"
    } catch {
        $choice = "1"
    }

    if ($choice -eq "2") {
        $Mode = "cli"
    } elseif ($choice -eq "3") {
        $Mode = "backend"
    } else {
        $Mode = "web"
    }
}

if ($Mode -eq "cli") {
    Write-Host "[*] 启动模式: CLI 端到端全链路闭环自动化演示..." -ForegroundColor Yellow
    $env:PYTHONPATH = "."
    & $PythonExe "backend\scripts\demo_e2e_closed_loop.py"
    exit 0
}

if ($Mode -eq "backend") {
    Write-Host "[*] 启动模式: 仅后端服务 (FastAPI / Swagger API)..." -ForegroundColor Yellow
    Write-Host "[*] 服务地址: http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host "[*] Swagger 文档: http://127.0.0.1:8000/docs" -ForegroundColor Green
    $env:PYTHONPATH = "."
    & $UvicornExe "backend.main:app" --host 127.0.0.1 --port 8000 --reload
    exit 0
}

if ($Mode -eq "web") {
    Write-Host "[*] 启动模式: 完整 Web UI 实时流式交互界面..." -ForegroundColor Yellow
    Write-Host "[1/2] 正在新窗口启动 FastAPI 后端服务 (Port 8000)..." -ForegroundColor Cyan
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "cd '$RootDir'; `$env:PYTHONPATH='.'; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Write-Host 'FastAPI Backend Running on http://127.0.0.1:8000' -ForegroundColor Green; & '$UvicornExe' backend.main:app --host 127.0.0.1 --port 8000 --reload"

    Write-Host "[2/2] 正在新窗口启动 Vue3 前端界面 (Port 3000)..." -ForegroundColor Cyan
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "cd '$RootDir\frontend'; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Write-Host 'Vue3 Frontend Running on http://localhost:3000' -ForegroundColor Green; npm.cmd run dev"

    Write-Host ""
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host "🎉 交互环境已在新窗口中成功启动！" -ForegroundColor Green
    Write-Host "👉 请在浏览器中打开: http://localhost:3000" -ForegroundColor Yellow
    Write-Host "👉 后端 API 文档:    http://127.0.0.1:8000/docs" -ForegroundColor Yellow
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host "提示: 关闭弹出的两个 PowerShell 窗口即可停止服务。" -ForegroundColor Gray
}

