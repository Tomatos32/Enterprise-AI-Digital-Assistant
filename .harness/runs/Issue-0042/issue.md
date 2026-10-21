# Issue-0042: 跨平台 Windows 原生运维启停脚本套件治理、字符集修复与 Docker 守护进程自愈唤醒 (issue.md)

> **Sprint**：Ops-0003 (Windows Native Operations & Local AI Automation)  
> **负责人**：Bootstrap Orchestrator / OpsAgent  
> **时间**：2026-10-21T08:30:00Z  
> **关联痛点**：用户反馈在 Windows 环境下运行 `start_app.bat` 与 `start_ai_service.bat` 出现严重解析报错（`'OT_DIR'`, `'ND_CMD"'`, `'ma'`, `'ocker'` 等乱码指令），且拉起 Dify 容器时由于 Docker Desktop 未就绪抛出命名管道不可达异常 `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`。

---

## 1. 核心需求与背景

为了实现个人开发者在 Windows 本地环境下的一键极速开箱体验，项目规划了前后端一键启停套件与本地 AI 底座（Ollama + Dify）编排套件。然而在实测落地过程中，遇到了以下两大核心痛点：

1. **Windows `cmd.exe` 字符集与换行符灾难**：
   - 传统脚本以无 BOM 的 UTF-8 编码与 `\n` (LF) 换行符保存，中文 Windows 默认使用 GBK (CP936) 逐字节解释。多字节中文字符与 Emoji 符号导致命令偏移错位，吞掉关键字母（`ollama` -> `'ma'`、`docker` -> `'ocker'`）。
   - 批处理 `if (...) else (...)` 结构在处理含小括号 `()` 的变量字符串时提前闭合截断，引发 `'ND_CMD"'` 语法报错。
2. **Docker Desktop 离线状态下的管道报错阻断**：
   - 运行 `start_ai_service.bat` 时，若宿主机上的 Docker Desktop 尚未启动或正在初始化，`docker compose up -d` 会直接向控制台抛出 `unable to get image ... open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified` 致命异常并中断流程。
   - 缺乏前置健康探活、自动唤醒与渐进轮询重试机制。

---

## 2. 交付与验收目标 (Definition of Done)

1. **前后端启停脚本套件 (`start_app.bat` & `stop_app.bat`)**：
   - 全面转为 Windows 原生 **ANSI / GBK (CP936)** 编码与标准 **CRLF (`\r\n`)** 换行符。
   - 消除容易引发代码块截断的小括号嵌套，改用标签跳转 (`goto`)。
   - 支持交互式选择模式：`[1] 自研沉浸式 Copilot 模式 (5173 端口)` 与 `[2] Dify 托管前台模式 (npm run dev:dify)`。
   - `stop_app.bat` 精准停止端口 8000、5173、3000 并安全释放对应 cmd 终端窗口。
2. **AI 底座启停脚本套件 (`start_ai_service.bat` & `stop_ai_service.bat`)**：
   - 精准锚定用户指定命令：`G:\Ollama_1\Ollama` 运行 `ollama run qwen3.5:2b`（设置 `OLLAMA_HOST=0.0.0.0:11434` 保证容器跨网通信）。
   - **Docker 引擎智能探活与自愈拉起**：在执行 compose 前先执行 `docker info`；若检测未运行，自动向系统请求拉起 `C:\Program Files\Docker\Docker\Docker Desktop.exe`，并提供最多 45 秒渐进式轮询探针；若超时给出清晰诊断提示，绝不异常崩溃。
   - `stop_ai_service.bat` 具备 Docker 状态防御检测，安全下线 Dify 容器并卸载 Ollama 模型显存占用。
3. **验证与测试**：
   - 语法静态验证：通过 `cmd.exe /c` 运行各脚本，确保 0 乱码、0 语法截断报错。
