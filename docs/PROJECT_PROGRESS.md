# Enterprise AI Digital Assistant - 项目进度与全量 Sprint 提示词规划文档

> **项目名称**: 基于 LangGraph + RAG + 企业工作流的企业级 AI 数字员工平台  
> **当前状态**: BOOTSTRAP MODE (引导构建阶段)  
> **更新时间**: 2026-08-03  
> **基准规范**: [docs/SPEC.MD](file:///g:/LLM_Learning/product/docs/SPEC.MD) & [AGENTS.md](file:///g:/LLM_Learning/product/AGENTS.md)  

---

## 1. 全局进度大盘 (Master Progress Overview)

```text
整体进度看板: [██████████████░░░░░░] 60% (Sprint 1 ~ 6 已全量完成闭环)
```

| Sprint 阶段 | 核心模块 | 状态 | 交付物 / 对应证据链 |
| :--- | :--- | :---: | :--- |
| **Sprint 1** | 基础框架搭建与环境联调 (FastAPI/JWT/RBAC/Docker) | ✅ **已闭环** | [Issue-0002](file:///.harness/runs/Issue-0002/), [Issue-0005](file:///.harness/runs/Issue-0005/) |
| **Sprint 2** | 知识库多格式解析、数据构建与 Qdrant 向量库持久化 | ✅ **已闭环** | [Issue-0004](file:///.harness/runs/Issue-0004/), [Issue-0010](file:///.harness/runs/Issue-0010/), [Issue-0007](file:///.harness/runs/Issue-0007/) |
| **Sprint 3** | Hybrid Retrieval 混合检索与 Reranker 引擎 | ✅ **已闭环** | [Issue-0008](file:///.harness/runs/Issue-0008/) |
| **Sprint 4** | LangGraph 状态机拓扑、意图路由引擎与条件边 | ✅ **已闭环** | [Issue-0001](file:///.harness/runs/Issue-0001/), [Issue-0011](file:///.harness/runs/Issue-0011/) |
| **Sprint 5** | Function Calling 工具注册器与 Tool Node | ✅ **已闭环** | [Issue-0012](file:///.harness/runs/Issue-0012/) |
| **Sprint 6** | 企业三方系统 Mock (ERP / OA / HR API) 与 MySQL 持久化 | ✅ **已闭环** | [Issue-0013](file:///.harness/runs/Issue-0013/) |
| **Sprint 7** | Human-in-the-loop 人机协同审批流与三层 AI 中断响应机制 | ⏳ **当前开发** | **Issue-0014** (详见 3.1 节提示词) |
| **Sprint 8** | WebSocket 双工流式通道与前端 Vue3 对话 UI | ⏳ **待开发** | **Issue-0015** (详见 3.2 节提示词) |
| **Sprint 9** | Celery 异步任务队列 (OCR / Embedding / Indexing) | ⏳ **待开发** | **Issue-0016** (详见 3.3 节提示词) |
| **Sprint 10** | AI Infra (vLLM / Prompt Cache / Token Monitor / Fallback) | ⏳ **待开发** | **Issue-0017** (详见 3.4 节提示词) |
| **Sprint 11** | RAG Evaluation 自动化评估 (RAGAS 评估套件) | ⏳ **待开发** | **Issue-0018** (详见 3.5 节提示词) |
| **Sprint 12** | 数字化转型 Demo 与 n8n / Dify 工作流集成 | ⏳ **待开发** | **Issue-0019** (详见 3.6 节提示词) |

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

---

## 3. “三层 AI 输出中断响应机制” 专项设计 (Three-Layer Response Cancellation Architecture)

在 AI 实时生成/流式输出或工具调用的过程中，用户触发“终止生成”（Stop Generation / Abort）时，系统必须提供完整、可靠的**三层响应与中断机制**，防止资源浪费与数据库脏数据产生：

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

### 三层机制核心实现要点：
1. **第一层（前端/传输层）**：
   - 客户端 Fetch 使用 `AbortController`，在点击“停止”按钮时执行 `controller.abort()`，断开 HTTP SSE / WebSocket 传输，并在 UI 呈现“已由用户终止”阻断状态。
2. **第二层（服务端/分发层）**：
   - FastAPI Async Generator 实时监听通道状态。若检测到客户端断开连接，立即捕获 `asyncio.CancelledError`，通过 Redis PubSub 或协程 Task 机制向后台 Task 注入 Cancel 信号。
3. **第三层（LangGraph 引擎与工具副作用防护层）**：
   - **LLM 调用中断**：向底层 LLM 客户端（vLLM / Qwen / OpenAI）发送 cancellation 信号，终止未完成 Token 的计算开销。
   - **状态机快照与历史一致性**：使用 `MemorySaver` 将当前已生成的部分内容保存为中断快照，在 `metadata` 中记录 `status: "CANCELLED"`，确保会话上下文不损坏。
   - **工具副作用护栏 (Side-Effect Guard)**：
     - 查询类只读工具（`query_employee`, `query_inventory`）：直接中断释放。
     - 写操作/状态变更类工具（`create_purchase`, `create_ticket`）：若在中途终止且尚未提交数据库事务，取消 DB Commit；若已提交，则标记工单为 `USER_CANCELLED` 挂起状态。

---

## 4. 未完成模块重点规划与提示词模板 (Uncompleted Modules & Prompts)

当前按顺序已规划至 **Issue-0014 (Sprint 7)**。

---

### 4.1 Sprint 7：Human-in-the-loop 人机协同审批流与三层 AI 中断响应机制
* **核心目标**：实现采购金额大于 5,000 元时的 LangGraph `interrupt()` 挂起与 `resume()` 恢复机制，并集成“三层 AI 输出中断响应机制”。
* **技术栈**：LangGraph Interrupt & Resume, Checkpointer Threading, FastAPI Abort handling, Approval State.
* **重点实现**：
  1. **审批节点与阈值判断**：`approval_node.py` 判断采购金额 $> 5,000$ 元时，Agent 自动调用 `interrupt()` 挂起状态机，保存 `thread_id` 与 State。
  2. **人机恢复控制 API**：暴露 `POST /api/v1/approval/action`（接收 `approval_id` 及 `approve`/`reject` 决策），恢复 LangGraph 执行。
  3. **三层 AI 中断响应服务**：实现 `POST /api/v1/chat/abort` 及 SSE/WS 中断信号处理，妥善保存取消快照与防脏数据写回。
* **交付物**：`backend/graph/nodes/approval_node.py`、审批/中断 API 与单元测试。

> #### 📋 提示词模板：`Prompt-Sprint-07-HumanInTheLoopAndAbort`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0014：实现 Sprint 7 “Human-in-the-loop 人机协同审批流与三层 AI 中断响应机制”。
> 
> 【具体要求】：
> 1. 在 `backend/graph/nodes/approval_node.py` 中实现审批拦截逻辑：当采购金额 > 5,000 元时使用 LangGraph `interrupt()` 挂起状态机。
> 2. 实现审批控制 API `POST /api/v1/approval/action`，接收 `approval_id` 及决策（`approve` / `reject`），调用 graph 的 `Command(resume=...)` 恢复运行。
> 3. 设计并实现“三层 AI 输出中断机制”：
>    - 暴露 `POST /api/v1/chat/abort` 中断 API。
>    - 捕获 `asyncio.CancelledError`，中止流式 Token 输出与未执行工具。
>    - 在 LangGraph Checkpointer 中保存 `status="CANCELLED"` 的中断快照。
> 4. 编写 `backend/tests/unit/test_approval_flow.py` 验证“申请 -> 中断挂起 -> 批准/拒绝 -> 恢复运行”及“用户主动中断 AI 输出”全流程。
> 5. 刷盘 `.harness/runs/Issue-0014/` 沙盒证据包。
> ```

---

### 4.2 Sprint 8：WebSocket 双工流式通道与前端 Vue3 对话 UI
* **技术栈**：FastAPI WebSocket, Async Generator, Vue 3, TailwindCSS / Flowbite.
* **重点实现**：
  1. **WebSocket 长连接接口** ([backend/api/v1/chat_ws.py](file:///g:/LLM_Learning/product/backend/api/v1/chat_ws.py))：支持实时 Token 级流式输出（Streaming）、Abort 终止信号及 Agent 节点状态通知。
  2. **Vue 3 极简 Chat UI** ([frontend/](file:///g:/LLM_Learning/product/frontend/))：实现响应式气泡对话界面、工具调用展示与审批卡片点击。
* **交付物**：WebSocket 实时通信通道及 Vue3 Chat 界面。

> #### 📋 提示词模板：`Prompt-Sprint-08-WebSocketUI`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0015：实现 Sprint 8 “WebSocket 双工流式通道与前端 Vue3 对话 UI”。
> 
> 【具体要求】：
> 1. 在 `backend/api/v1/chat_ws.py` 实现 WebSocket 路由 `/api/v1/ws/chat/{client_id}`。
> 2. 结合 LangGraph `astream_events` 实时向客户端推送 Token 流、思考链及工具执行步骤日志。
> 3. 在 `frontend/` 搭建 Vue3 + Vite + TailwindCSS 聊天组件，支持展示消息流、加载状态、停止生成按钮及审批卡片。
> 4. 编写 `backend/tests/unit/test_websocket.py` 进行 WS 消息握手与流式传输测试。
> 5. 刷盘 `.harness/runs/Issue-0015/` 证据包。
> ```

---

### 4.3 Sprint 9：Celery 异步任务队列 (OCR / Embedding / Indexing)
* **技术栈**：Celery 5.x, Redis Message Broker, Async Task Workers.
* **重点实现**：
  1. 搭建 Celery 应用 ([backend/tasks/celery_app.py](file:///g:/LLM_Learning/product/backend/tasks/celery_app.py))，使用 Redis 作为 Broker 与 Result Backend。
  2. 实现 `async_ingest_document` 耗时文件后台解压、切片、Embedding 和写入 Qdrant。
* **交付物**：Celery Task Worker 模块及状态查询接口 `GET /api/v1/tasks/{task_id}`。

> #### 📋 提示词模板：`Prompt-Sprint-09-CeleryTasks`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0016：实现 Sprint 9 “Celery 异步任务队列与大文件离线处理”。
> 
> 【具体要求】：
> 1. 在 `backend/tasks/` 下配置 `celery_app.py`，连接 Redis 作为消息队列。
> 2. 定义异步 Task：`async_ingest_document(file_path)`（负责后台解压、切片、Embedding 和写入 Qdrant）。
> 3. 改造 `POST /api/v1/knowledge/upload` 支持传入 `async=true` 参数提交 Celery 任务并立即返回 `task_id`。
> 4. 暴露 `GET /api/v1/tasks/{task_id}/status` 查询异步任务进度。
> 5. 编写 `backend/tests/unit/test_celery_tasks.py` 验证任务投递与状态回调。
> 6. 刷盘 `.harness/runs/Issue-0016/` 证据包。
> ```

---

### 4.4 Sprint 10：AI Infra (vLLM / Prompt Cache / Token Monitor / Fallback)
* **技术栈**：vLLM / Ollama (Local Inference), Redis Hash Cache, Token Counter, Model Fallback.
* **重点实现**：
  1. **Prompt Cache 机制**：针对长 System Prompt 计算 Hash 并在 Redis 缓存命中结果（命中率目标 $> 70\%$）。
  2. **Token Cost Monitor**：记录每次 LLM 调用的 Input/Output Token 数量并统计开销。
  3. **Model Fallback 降级**：优先级 `GPT-4o -> Qwen3 -> DeepSeek -> Rule Engine`。
* **交付物**：`backend/core/llm_infra.py` 基础设施封装。

> #### 📋 提示词模板：`Prompt-Sprint-10-AIInfra`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0017：实现 Sprint 10 “AI Infra 基础设施：Prompt Cache、Token Monitor 与 Fallback”。
> 
> 【具体要求】：
> 1. 在 `backend/core/llm_infra.py` 中实现 `LLMGateway` 类。
> 2. 基于 Redis 实现 Prompt Hash Cache 逻辑，重复 Prompt 直接返回缓存响应。
> 3. 实现 Token 统计与成本计算中间件，将开销日志写入 MySQL 或 Redis。
> 4. 实现模型降级策略（支持主模型超时或报错时自动 Try-Catch 切换至备选模型）。
> 5. 编写 `backend/tests/unit/test_llm_infra.py` 验证 Cache 命中与降级回退。
> 6. 刷盘 `.harness/runs/Issue-0017/` 沙盒证据包。
> ```

---

### 4.5 Sprint 11：RAG Evaluation 自动化评估 (RAGAS)
* **技术栈**：RAGAS Framework, Faithfulness, Context Recall, Answer Relevance, Benchmark Datasets.
* **重点实现**：
  1. 编写 [benchmark/eval_ragas.py](file:///g:/LLM_Learning/product/benchmark/) 评估脚本。
  2. 加载标注数据集 `benchmark/test-dataset.json`，计算 Faithfulness ($> 0.90$)、Recall 与 Precision。
* **交付物**：RAG 评估测试集与自动评测脚本。

> #### 📋 提示词模板：`Prompt-Sprint-11-RAGASEval`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0018：实现 Sprint 11 “RAGAS 自动化质量评估与回归测试套件”。
> 
> 【具体要求】：
> 1. 在 `benchmark/` 目录下构建标准评测数据集 `test-dataset.json`（包含 30 组 question, ground_truth, contexts）。
> 2. 编写 `benchmark/eval_ragas.py` 脚本，调用 RAGAS 评估库计算 Faithfulness, Answer Relevance, Context Recall 得分。
> 3. 当 Faithfulness < 0.90 时自动触发错误告警并阻止流水线发布。
> 4. 编写 `backend/tests/unit/test_eval_pipeline.py` 进行评估集成测试。
> 5. 刷盘 `.harness/runs/Issue-0018/` 证据包。
> ```

---

### 4.6 Sprint 12：数字化转型 Demo 与 n8n / Dify 工作流集成
* **技术栈**：n8n / Dify Webhook API, Mock Enterprise WeChat / Slack Bot.
* **重点实现**：
  1. 暴露 Webhook 端点 `POST /api/v1/webhook/workflow` 支持接收 n8n / Dify 的工作流事件触发。
  2. 实现 Mock 企业微信推送消息通知。
* **交付物**：全流程 SOP 自动化 Demo 接入。

> #### 📋 提示词模板：`Prompt-Sprint-12-DigitalDemo`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0019：实现 Sprint 12 “数字化转型 Demo 与 n8n / Dify Webhook 工作流集成”。
> 
> 【具体要求】：
> 1. 在 `backend/api/v1/workflow.py` 实现 Webhook 触发路由 `POST /api/v1/webhook/event`。
> 2. 模拟接入 n8n / Dify 节点，实现当审批通过后自动触发 Webhook 通知企微 Bot。
> 3. 整理全流程联调测试脚本，演示“用户提问 -> Intent Router -> RAG -> 审批 -> 企业工作流执行 -> 企微通知”闭环。
> 4. 刷盘 `.harness/runs/Issue-0019/` 证据包，完成项目终极归档。
> ```

---

## 5. 提示词模板使用指南 (How to Use Prompts)

当准备开始推进后续未完成模块时，只需按照以下步骤操作：

1. **选择对应的提示词模板**（如当前准备开发 Sprint 7 时选择 `Prompt-Sprint-07-HumanInTheLoopAndAbort`）。
2. **在对话中直接发送该提示词**。
3. **系统将自动切换为 Harness SOP 流程**：依次自动创建 `.harness/runs/Issue-XXXX/` 证据包、运行 `DeveloperAgent` 编码、触发 `pytest` / `ruff` 检查、调用 `ReviewerAgent` 审计并闭环关单！
