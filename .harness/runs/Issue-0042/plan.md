# Issue-0042: 技术架构与运维实施方案 (plan.md)

> **Sprint**：Ops-0003 (Windows Native Operations & Local AI Automation)  
> **设计人**：PlannerAgent / OpsAgent  
> **时间**：2026-10-21T08:35:00Z  

---

## 1. 架构拓扑与自愈流程设计

```text
                        start_ai_service.bat 执行
                                  │
                                  ├──────────────────────────────┐
                                  ▼                              ▼
                       [新窗口拉起 Ollama]              [Docker 引擎状态探测]
                     cd G:\Ollama_1\Ollama              docker info >nul 2>nul
                  set OLLAMA_HOST=0.0.0.0:11434                  │
                     ollama run qwen3.5:2b             ┌─────────┴─────────┐
                                                       ▼                   ▼
                                                  [状态: 已就绪]      [状态: 未运行]
                                                       │                   │
                                                       │      自动唤醒 Docker Desktop.exe
                                                       │                   │
                                                       │        轮询等待就绪 (最长 45s)
                                                       │                   │
                                                       ├───────────────────┘
                                                       ▼
                                            [启动 Dify 容器编排]
                                             cd G:\dify\docker
                                            docker compose up -d
                                                       │
                                                       ▼
                                            [完成输出控制台访问信息]
```

---

## 2. 实施矩阵

1. **Task 1: 物理编码与字符集治理**：
   - 编写自动化编译生成脚本，使用二进制 GBK 编码与 `\r\n` 格式覆写全部 4 个批处理文件。
   - 彻底废弃所有包含中括号、特殊 Emoji 的变量和标题，确保 cmd 解释器以最高稳定性执行。

2. **Task 2: 前后端交互式启动流解耦 (`start_app.bat`)**：
   - 采用标准 `goto` 跳转分离 `SELECT_DIFY` 与默认 Copilot 模式。
   - 分别在新终端中挂载 `FastAPI` (8000端口) 与 `Vite` (5173端口)，并附带环境健康提示。

3. **Task 3: Docker 守护进程自愈等待机制 (`start_ai_service.bat`)**：
   - 引入 `docker info >nul 2>nul` 连通性校验；
   - 引入 `if exist ... start "" "Docker Desktop.exe"` 唤醒机制；
   - 引入循环计数器 `:WAIT_DOCKER_LOOP` 与 3 秒间隔探针，达成自愈闭环。

4. **Task 4: 安全终止脚本幂等性加固 (`stop_app.bat` & `stop_ai_service.bat`)**：
   - 释放端口前使用 `findstr "LISTENING"` 过滤，避免误杀无关连接；
   - 停止 Dify 前检查 Docker 进程，若引擎未运行则跳过 `compose down`，避免控制台报错。
