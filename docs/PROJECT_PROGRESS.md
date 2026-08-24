# Enterprise AI Digital Assistant - 项目进度与全量 Sprint 提示词规划文档

> **项目名称**: 基于 LangGraph + RAG + 企业工作流的企业级 AI 数字员工平台  
> **当前状态**: BOOTSTRAP MODE / FULLY COMPLETED (已完成 Sprint 1~12 全量闭环)  
> **更新时间**: 2026-08-24  
> **基准规范**: [docs/SPEC.MD](file:///g:/LLM_Learning/product/docs/SPEC.MD) & [AGENTS.md](file:///g:/LLM_Learning/product/AGENTS.md)  

---

## 1. 全局进度大盘 (Master Progress Overview)

```text
整体进度看板: [████████████████████] 100% (Sprint 1 ~ 12 已全量闭环关单)
```

| Sprint 阶段 | 核心模块 | 状态 | 交付物 / 对应证据链 |
| :--- | :--- | :---: | :--- |
| **Sprint 1** | 基础框架搭建与环境联调 (FastAPI/JWT/RBAC/Docker) | ✅ **已闭环** | [Issue-0002](file:///.harness/runs/Issue-0002/), [Issue-0005](file:///.harness/runs/Issue-0005/) |
| **Sprint 2** | 知识库多格式解析、数据构建与 Qdrant 向量库持久化 | ✅ **已闭环** | [Issue-0004](file:///.harness/runs/Issue-0004/), [Issue-0010](file:///.harness/runs/Issue-0010/), [Issue-0007](file:///.harness/runs/Issue-0007/) |
| **Sprint 3** | Hybrid Retrieval 混合检索与 Reranker 引擎 | ✅ **已闭环** | [Issue-0008](file:///.harness/runs/Issue-0008/) |
| **Sprint 4** | LangGraph 状态机拓扑、意图路由引擎与条件边 | ✅ **已闭环** | [Issue-0001](file:///.harness/runs/Issue-0001/), [Issue-0011](file:///.harness/runs/Issue-0011/) |
| **Sprint 5** | Function Calling 工具注册器与 Tool Node | ✅ **已闭环** | [Issue-0012](file:///.harness/runs/Issue-0012/) |
| **Sprint 6** | 企业三方系统 Mock (ERP / OA / HR API) 与 MySQL 持久化 | ✅ **已闭环** | [Issue-0013](file:///.harness/runs/Issue-0013/) |
| **Sprint 7** | Human-in-the-loop 人机协同审批流与三层 AI 中断响应机制 | ✅ **已闭环** | [Issue-0014](file:///.harness/runs/Issue-0014/) |
| **Sprint 8** | WebSocket 双工流式通道与前端 Vue3 对话 UI | ✅ **已闭环** | [Issue-0015](file:///.harness/runs/Issue-0015/) |
| **Sprint 9** | Celery 异步任务队列 (OCR / Embedding / Indexing) | ✅ **已闭环** | [Issue-0016](file:///.harness/runs/Issue-0016/) |
| **Sprint 10** | AI Infra (vLLM / Prompt Cache / Token Monitor / Fallback) | ✅ **已闭环** | [Issue-0017](file:///.harness/runs/Issue-0017/) |
| **Sprint 11** | RAG Evaluation 自动化评估 (RAGAS 评估套件与 0.90 门禁) | ✅ **已闭环** | [Issue-0018](file:///.harness/runs/Issue-0018/) |
| **Sprint 12** | 数字化转型 Demo 与 n8n / Dify 工作流集成 | ✅ **已闭环** | [Issue-0019](file:///.harness/runs/Issue-0019/) |

---

## 2. 已完成模块详解 (Completed Modules)

### 2.1 Sprint 1：基础框架搭建与环境联调
- **核心目标**：搭建工程脚手架，完成容器化基础中间件配置、全局异常处理拦截及 JWT / RBAC 安全防护。
- **调用技术栈**：FastAPI, Docker Compose, MySQL 8.0, Redis 7.0, Qdrant 1.8, PyJWT, bcrypt, Pydantic v2.
- **物理交付物**：[Issue-0002](file:///.harness/runs/Issue-0002/), [Issue-0005](file:///.harness/runs/Issue-0005/)

### 2.2 Sprint 2：知识库多格式数据构建与 Qdrant 向量持久化
- **核心目标**：生成符合企业真实规范（包含 Human-in-the-loop 审批阈值）的多主题、多格式测试数据，并实现结构化 Loader 与 Qdrant 向量入库。
- **调用技术栈**：PyPDF, OpenPyXL, ReportLab, LangChain Document, Qdrant Client, BGE-M3.
- **物理交付物**：[Issue-0004](file:///.harness/runs/Issue-0004/), [Issue-0010](file:///.harness/runs/Issue-0010/), [Issue-0007](file:///.harness/runs/Issue-0007/)

### 2.3 Sprint 3：Hybrid Retrieval 混合检索与 Reranker 引擎
- **核心目标**：实现 BM25 文本检索与 Dense Vector 向量检索的 RRF 融合，并集成 Reranker 筛选 Top-5。
- **调用技术栈**：rank_bm25, Qdrant Vector Search, RRF Algorithm, CrossEncoder/Reranker.
- **物理交付物**：[Issue-0008](file:///.harness/runs/Issue-0008/)

### 2.4 Sprint 4：LangGraph 状态机拓扑与意图路由引擎
- **核心目标**：构建 LangGraph StateGraph 状态机，实现 `Intent Router -> (Retrieve / Tool / Chat) -> Generate` 完整节点拓扑与 MemorySaver 持久化。
- **调用技术栈**：LangGraph, StateGraph, Conditional Edges, MemorySaver.
- **物理交付物**：[Issue-0001](file:///.harness/runs/Issue-0001/), [Issue-0011](file:///.harness/runs/Issue-0011/)

### 2.5 Sprint 5：Function Calling 工具注册器与 Tool Node
- **核心目标**：建立全局 `ToolRegistry`，实现 5 大企业核心工具 (`query_employee`, `query_inventory`, `create_ticket`, `create_purchase`, `send_email`)，并在 LangGraph 中集成 `tool_node` 写回 `ToolMessage`。
- **调用技术栈**：OpenAI/Qwen JSON Schema, ToolRegistry, LangChain ToolMessage.
- **物理交付物**：[Issue-0012](file:///.harness/runs/Issue-0012/)

### 2.6 Sprint 6：企业三方系统 Mock 接口与 MySQL 持久化
- **核心目标**：创建 HR、ERP、OA 三大系统 Mock REST API (`/api/v1/mock/`)，建立 SQLAlchemy ORM 模型 (`User`, `Inventory`, `Ticket`, `Purchase`) 访问 MySQL 数据，并将 Sprint 5 工具适配打通。
- **调用技术栈**：SQLAlchemy ORM, FastAPI Sub-routers, MySQL 8.0, Seed Generator.
- **物理交付物**：[Issue-0013](file:///.harness/runs/Issue-0013/)

### 2.7 Sprint 7：Human-in-the-loop 人机协同审批流与三层 AI 中断响应机制
- **核心目标**：实现采购金额大于 5,000 元时的 LangGraph `interrupt()` 挂起与 `resume()` 恢复机制，并集成“三层 AI 输出中断响应机制”。
- **调用技术栈**：LangGraph Interrupt & Resume, Checkpointer Threading, FastAPI Abort handling, Approval State.
- **物理交付物**：[Issue-0014](file:///.harness/runs/Issue-0014/)

### 2.8 Sprint 8：WebSocket 双工流式通道与前端 Vue3 对话 UI
- **核心目标**：实现 WebSocket 双工长连接，结合 LangGraph `astream_events` 推送 Token 流与节点日志，并在 Vue3 客户端搭建响应式 Chat UI。
- **调用技术栈**：FastAPI WebSocket, Async Generator, Vue 3, TailwindCSS.
- **物理交付物**：[Issue-0015](file:///.harness/runs/Issue-0015/)

### 2.9 Sprint 9：Celery 异步任务队列与大文件离线处理
- **核心目标**：配置 Celery 实例连接 Redis，实现异步文档处理 Task (`async_ingest_document`)，暴露 `GET /api/v1/tasks/{task_id}/status` 查询与进度回调。
- **调用技术栈**：Celery 5.x, Redis Message Broker, Async Task Workers.
- **物理交付物**：[Issue-0016](file:///.harness/runs/Issue-0016/)

### 2.10 Sprint 10：AI Infra (Prompt Cache / Token Monitor / Model Fallback)
- **核心目标**：实现 `LLMGateway` 网关，集成 Redis SHA-256 Prompt Hash 缓存、Token 数量与 USD 成本统计监控，以及主备模型自动降级回退机制。
- **调用技术栈**：Redis SHA-256 Prompt Hash, Token Counter & Cost Calculation, Model Fallback.
- **物理交付物**：[Issue-0017](file:///.harness/runs/Issue-0017/)

### 2.11 Sprint 11：RAG Evaluation 自动化评估套件与门禁阻断
- **核心目标**：构建包含 30 组样本的企业级 RAG 标准评测数据集 `test-dataset.json`，编写 `eval_ragas.py` 评估 Faithfulness, Answer Relevance, Context Recall 得分，并在 Faithfulness < 0.90 时阻断 CI 流水线。
- **调用技术栈**：RAGAS Framework, Datasets, Faithfulness Gate Check.
- **物理交付物**：[Issue-0018](file:///.harness/runs/Issue-0018/)

### 2.12 Sprint 12：数字化转型 Demo 与 n8n / Dify 工作流集成
- **核心目标**：实现 Webhook 触发路由 `POST /api/v1/webhook/event` 接入 n8n / Dify 工作流，模拟审批通过后自动推送企业微信 Bot 通知，完成全流程 SOP 自动化 Demo 闭环。
- **调用技术栈**：n8n / Dify Webhook API, Mock Enterprise WeChat Bot, End-to-End SOP Automation.
- **物理交付物**：[Issue-0019](file:///.harness/runs/Issue-0019/)

---

## 3. “三层 AI 输出中断响应机制” 专项设计 (Three-Layer Response Cancellation Architecture)

在 AI 实时生成/流式输出或工具调用的过程中，用户触发“终止生成”（Stop Generation / Abort）时，系统提供完整、可靠的**三层响应与中断机制**，防止资源浪费与数据库脏数据产生：

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 第一层：前端/传输层 (Client Transport Layer)                           │
│ ├─ Vue3 / JS AbortController.abort() 发送中断信号                       │
│ └─ WebSocket / SSE 发送 {"type": "abort", "thread_id": "..."}          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 第二层：服务端/分发层 (Server Dispatcher Layer)                          │
│ ├─ FastAPI 检测 request.is_disconnected() / Redis PubSub 中断通道       │
│ └─ 触发 Python asyncio.Task.cancel() 终止流式 Generator 协程            │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 第三层：LangGraph 引擎与工具副作用防护层 (Engine & Side-Effect Guard)    │
│ ├─ 终止 LLM HTTP Streaming 链接 (即刻停止 Token 消耗)                   │
│ ├─ 保存当前快照至 LangGraph Checkpointer (标记 state.status = CANCELLED) │
│ └─ 工具副作用护栏：读工具即刻释放；写工具 (如采购/工单) 校验事务与回滚状态   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 全量 Sprint 终极闭环归档总结 (Final Archival Summary)

全量 Sprint（Sprint 1 ~ 12）已严格按照 Harness Engineering 最高物理规范履约完成，所有 Issue（Issue-0001 至 Issue-0019）均在 `.harness/runs/` 下建立了全量 9 大只读证据包，`ruff check` 零告警，全量 67 项自动化单元测试 100% 通过。
