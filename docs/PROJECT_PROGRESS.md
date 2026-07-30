# Enterprise AI Digital Assistant - 项目进度与全量 Sprint 提示词规划文档

> **项目名称**: 基于 LangGraph + RAG + 企业工作流的企业级 AI 数字员工平台  
> **当前状态**: BOOTSTRAP MODE (引导构建阶段)  
> **更新时间**: 2026-07-30  
> **基准规范**: [docs/SPEC.MD](file:///g:/LLM_Learning/product/docs/SPEC.MD) & [AGENTS.md](file:///g:/LLM_Learning/product/AGENTS.md)  

---

## 1. 全局进度大盘 (Master Progress Overview)

```text
整体进度看板: [████████░░░░░░░░░░░░] 35% (Sprint 1 & 2 & 4 已完成核心骨架)
```

| Sprint 阶段 | 核心模块 | 状态 | 交付物 / 对应证据链 |
| :--- | :--- | :---: | :--- |
| **Sprint 1** | 基础框架搭建与环境联调 (FastAPI/JWT/RBAC/Docker) | ✅ **已闭环** | [Issue-0002](file:///.harness/runs/Issue-0002/), [Issue-0005](file:///.harness/runs/Issue-0005/) |
| **Sprint 2** | 知识库解析与多格式数据构建 (sample_kb / Loader) | 🟡 **阶段闭环** | [Issue-0004](file:///.harness/runs/Issue-0004/) (矢量管道待对接) |
| **Sprint 3** | Hybrid Retrieval 混合检索与 Reranker 引擎 | ⏳ **待开发** | 详见 3.2 节提示词模板 |
| **Sprint 4** | LangGraph 状态机核心框架 (StateGraph / Router) | 🟡 **骨架完成** | [Issue-0001](file:///.harness/runs/Issue-0001/) (完整拓扑待深化) |
| **Sprint 5** | Function Calling 工具注册与执行器 | ⏳ **待开发** | 详见 3.4 节提示词模板 |
| **Sprint 6** | 企业系统 Mock (ERP / OA / HR API) | ⏳ **待开发** | 详见 3.5 节提示词模板 |
| **Sprint 7** | Human-in-the-loop 人机协同审批流 | ⏳ **待开发** | 详见 3.6 节提示词模板 |
| **Sprint 8** | WebSocket 流式通信与 Vue3 对话 UI | ⏳ **待开发** | 详见 3.7 节提示词模板 |
| **Sprint 9** | Celery 异步任务队列 (OCR / Embedding) | ⏳ **待开发** | 详见 3.8 节提示词模板 |
| **Sprint 10** | AI Infra (vLLM / Prompt Cache / Token Monitor) | ⏳ **待开发** | 详见 3.9 节提示词模板 |
| **Sprint 11** | RAG Evaluation 自动化评估 (RAGAS) | ⏳ **待开发** | 详见 3.10 节提示词模板 |
| **Sprint 12** | 数字化转型 Demo 与 n8n / Dify 集成 | ⏳ **待开发** | 详见 3.11 节提示词模板 |

---

## 2. 已完成模块详解 (Completed Modules)

### 2.1 Sprint 1：基础框架搭建与环境联调
- **核心目标**：搭建工程脚手架，完成容器化基础中间件配置、全局异常处理拦截及 JWT / RBAC 安全防护。
- **调用技术栈**：FastAPI, Docker Compose, MySQL 8.0, Redis 7.0, Qdrant 1.8, PyJWT, bcrypt, Pydantic v2.
- **重点实现内容**：
  1. **全局异常处理与响应封装** ([backend/core/exceptions.py](file:///g:/LLM_Learning/product/backend/core/exceptions.py))：实现了 `StandardResponse` JSON 响应模型，定制 `AppException` 继承链（`AuthenticationError`, `PermissionDeniedError`），并在 [backend/main.py](file:///g:/LLM_Learning/product/backend/main.py) 注册统一 handlers。
  2. **JWT 安全认证** ([backend/core/security.py](file:///g:/LLM_Learning/product/backend/core/security.py))：使用原生 `bcrypt` 盐值哈希实现密码校验，提供 `create_access_token` 与 `decode_access_token`。
  3. **RBAC 角色权限中间件** ([backend/core/rbac.py](file:///g:/LLM_Learning/product/backend/core/rbac.py))：定义 `RoleEnum` (`admin`, `manager`, `employee`)，实现 `get_current_user` 依赖项及 `require_role(allowed_roles)` 工厂防护。
  4. **登录与受保护路由** ([backend/api/v1/auth.py](file:///g:/LLM_Learning/product/backend/api/v1/auth.py))：实现 `POST /api/v1/auth/login` 签发 Token，`GET /api/v1/auth/me` 及 `GET /api/v1/auth/admin-only` 阻断验证。
  5. **一键容器编排** ([docker-compose.yml](file:///g:/LLM_Learning/product/docker-compose.yml))：配置 MySQL 8.0、Redis 7.0、Qdrant v1.8.0 容器及健康检查探针。
- **物理交付物**：
  - `backend/main.py`
  - `backend/core/exceptions.py`
  - `backend/core/security.py`
  - `backend/core/rbac.py`
  - `backend/api/v1/auth.py`
  - `backend/api/v1/health.py`
  - `docker-compose.yml`
  - 单元测试：`backend/tests/unit/test_infra.py`, `backend/tests/unit/test_auth.py`

### 2.2 Sprint 2：知识库多格式样例数据生成与 Loader 解析
- **核心目标**：生成符合企业真实规范（包含 Human-in-the-loop 审批阈值）的多主题、多格式测试数据，并实现结构化 Loader。
- **调用技术栈**：PyPDF, OpenPyXL, ReportLab, LangChain Document.
- **重点实现内容**：
  1. **自动化数据生成脚本** ([backend/scripts/generate_sample_kb.py](file:///g:/LLM_Learning/product/backend/scripts/generate_sample_kb.py))：一键自动生成 HR、采购 SOP、IT 运维、财务报销等 4 份 Markdown 文档，利用 ReportLab 生成图文 PDF，利用 OpenPyXL 生成办公设备库存 Excel 表。
  2. **多格式 RAG Loader** ([backend/rag/loader.py](file:///g:/LLM_Learning/product/backend/rag/loader.py))：支持 Markdown、PDF 分页及 Excel 转 Markdown Table 结构解析，自动提取 `category`, `format`, `source` 等标准 Metadata。
- **物理交付物**：
  - [docs/sample_kb/](file:///g:/LLM_Learning/product/docs/sample_kb/)（包含 `01_HR`, `02_PROCUREMENT`, `03_IT`, `04_FINANCE` 及 `pdf/`, `excel/`）
  - `backend/scripts/generate_sample_kb.py`
  - `backend/rag/loader.py`
  - 单元测试：`backend/tests/unit/test_rag_data.py`

### 2.3 Sprint 4：LangGraph 状态机核心骨架 (Scaffold)
- **核心目标**：构建 LangGraph StateGraph 状态机拓扑与内存 Checkpointer 联调。
- **调用技术栈**：LangGraph, LangChain Messages, MemorySaver.
- **重点实现内容**：
  1. 定义共享强类型 `AgentState` 结构（包含 `messages`, `user_id`, `session_id`, `current_step`, `metadata`）。
  2. 实现 `chatbot_node` 节点与 `MemorySaver` checkpointer 绑定。
- **物理交付物**：
  - `backend/graph/state.py`
  - `backend/graph/workflow.py`
  - `backend/graph/nodes/chatbot.py`
  - 单元测试：`backend/tests/unit/test_graph.py`, `backend/tests/unit/test_graph_unittest.py`

---

## 3. 未完成模块重点规划与提示词模板 (Uncompleted Modules & Prompts)

你可直接复制以下**提示词模板**用于后续下发任务或指导 AI 开发！

---

### 3.1 Sprint 2 (剩余): 向量库持久化与知识库上传接口
* **技术栈**：Qdrant Python Client, BGE-M3 (FastEmbed / HuggingFace), FastAPI File Upload.
* **重点实现**：
  1. 编写 `backend/rag/vector_store.py` 实现 Qdrant Collection 初始化与 BGE-M3 Embedding Upsert。
  2. 实现 `POST /api/v1/knowledge/upload` 文件上传并触发文档切片（Chunk Size: 500, Overlap: 50）与向量入库。
* **交付物**：`POST /api/v1/knowledge/upload` 接口与对应的 `test_vector_store.py` 测试。

> #### 📋 提示词模板：`Prompt-Sprint-02-Vector`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0007：完成 Sprint 2 剩余任务“Qdrant 向量库 Embedding 持久化与知识库文件上传接口”。
> 
> 【具体要求】：
> 1. 修改 `backend/rag/vector_store.py`，使用 Qdrant Client 创建 Collection "enterprise_knowledge"，配置向量维度（BGE-M3 / 1024 维，Cosine 相似度）。
> 2. 实现 `upsert_documents(docs: List[Document])` 方法，将 `backend/rag/loader.py` 解析出的切片与 Metadata 批量写入 Qdrant。
> 3. 开发 FastAPI 端点 `POST /api/v1/knowledge/upload`（支持接收文件并在 backend/data/ 存盘后调用 Loader 自动入库）。
> 4. 编写 `backend/tests/unit/test_vector_store.py` 验证数据写入与 Qdrant 检索。
> 5. 遵从 Harness SOP，生成 `.harness/runs/Issue-0007/` 下 9 大证据包并确保 pytest 100% 通过。
> ```

---

### 3.2 Sprint 3: Hybrid Retrieval 混合检索与 Reranker 引擎
* **技术栈**：Qdrant Dense Vector, BM25 (rank_bm25), BGE-Reranker-Large, RRF 融合算法.
* **重点实现**：
  1. **BM25 检索器**：针对 Markdown 文本切片构建内存/Disk BM25 索引，支持精准专有名词搜索。
  2. **Dense 向量检索**：调用 Qdrant 进行 Top-20 语义检索。
  3. **RRF 归一化融合**：计算 $RRF\_Score = \sum \frac{1}{60 + rank}$ 融合得分。
  4. **Reranker 重排序**：引入 BGE-Reranker-Large（或 Mock 重排引擎）完成 Top-20 到 Top-5 的筛选。
* **交付物**：`POST /api/v1/knowledge/search` 接口与 `backend/rag/retriever.py`。

> #### 📋 提示词模板：`Prompt-Sprint-03-HybridSearch`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0008：实现 Sprint 3 “Hybrid Retrieval 混合检索与 Reranker 引擎”。
> 
> 【具体要求】：
> 1. 创建 `backend/rag/retriever.py`，实现 `HybridRetriever` 类。
> 2. 实现BM25关键词检索器（使用 rank_bm25 库）与 Qdrant Dense Vector 向量检索器。
> 3. 实现 RRF (Reciprocal Rank Fusion) 融合算法，合并 BM25 与 向量检索结果。
> 4. 集成 Reranker 逻辑（支持配置使用 BGE-Reranker 或轻量级评分），从 Top-20 筛选重排出 Top-5 最佳匹配片段。
> 5. 暴露 `POST /api/v1/knowledge/search` 接口，入参包含 `query`, `top_k`, `category_filter`。
> 6. 编写 `backend/tests/unit/test_retrieval.py` 验证问答召回率（如查询“采购60000元设备需要谁审批”准确召回双重审批规则）。
> 7. 刷盘 `.harness/runs/Issue-0008/` 证据包，保持全量测试绿灯。
> ```

---

### 3.3 Sprint 4 (深化): LangGraph 完整拓扑节点与路由引擎
* **技术栈**：LangGraph Conditional Edges, Intent Router Node, Memory Checkpointer.
* **重点实现**：
  1. **Intent Router**：意图分类节点（判断用户输入属于：知识库问答 `KNOWLEDGE`、工具调用 `TOOL`、审批流程 `APPROVAL` 或普通聊天 `CHAT`）。
  2. **Retrieve Node**：调用 `HybridRetriever` 将召回上下文注入 `AgentState`。
  3. **Generate Node**：组织 Prompt（包含 RAG 上下文与 Guardrails）生成回答。
* **交付物**：完整的 LangGraph 节点图拓扑 ([backend/graph/workflow.py](file:///g:/LLM_Learning/product/backend/graph/workflow.py)) 与单元测试。

> #### 📋 提示词模板：`Prompt-Sprint-04-LangGraphNodes`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0009：深化 Sprint 4 “LangGraph 完整节点拓扑与意图路由引擎”。
> 
> 【具体要求】：
> 1. 在 `backend/graph/nodes/` 下新增节点：
>    - `router_node.py`：使用 LLM 或规则实现 Intent Classification，输出路由目标。
>    - `retrieve_node.py`：调用 HybridRetriever 检索相关知识切片写入 State 的 `context` 字段。
>    - `generate_node.py`：根据 State 中的上下文和消息生成最终回答。
> 2. 在 `backend/graph/workflow.py` 中构建条件边（`add_conditional_edges`），实现 `START -> Intent Router -> (Retrieve / Tool / Chat) -> Generate -> END`。
> 3. 编写 `backend/tests/unit/test_graph_topology.py` 验证不同意图查询的节点转移轨迹。
> 4. 刷盘 `.harness/runs/Issue-0009/` 沙盒证据包。
> ```

---

### 3.4 Sprint 5: Function Calling & Tool Registry 工具注册器
* **技术栈**：FastAPI, JSON Schema, LangChain Tool Decorator, Function Calling.
* **重点实现**：
  1. **Tool Registry** ([backend/tools/registry.py](file:///g:/LLM_Learning/product/backend/tools/registry.py))：工具注册中心，统一管理工具的名称、描述、JSON Schema 契约与执行权限。
  2. **核心业务工具集** ([backend/tools/](file:///g:/LLM_Learning/product/backend/tools/))：
     - `query_employee(employee_id)`：查询员工信息与部门。
     - `query_inventory(item_name)`：查询设备库存与单价。
     - `create_ticket(title, priority, description)`：创建 IT 运维工单。
     - `create_purchase(item_name, count, total_price)`：创建采购申请。
     - `send_email(to, subject, body)`：发送通知邮件。
* **交付物**：`ToolRegistry` 模块及全套 JSON Schema 工具映射。

> #### 📋 提示词模板：`Prompt-Sprint-05-FunctionCalling`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0010：实现 Sprint 5 “Function Calling 工具注册器与 Tool Node”。
> 
> 【具体要求】：
> 1. 建立 `backend/tools/registry.py`，实现全局 `ToolRegistry`，支持自动导出符合 OpenAI/Qwen 规范的 JSON Schema 结构。
> 2. 在 `backend/tools/impl/` 中实现 5 个核心工具：`query_employee`, `query_inventory`, `create_ticket`, `create_purchase`, `send_email`。
> 3. 在 LangGraph 中集成 `tool_node`，当 Agent 输出 `tool_calls` 时自动路由至 `tool_node` 执行并写回 `ToolMessage`。
> 4. 编写 `backend/tests/unit/test_tools.py` 验证工具 Schema 生成与函数调用逻辑。
> 5. 刷盘 `.harness/runs/Issue-0010/` 证据包。
> ```

---

### 3.5 Sprint 6：企业系统 Mock (ERP / OA / HR API)
* **技术栈**：FastAPI Router Mock, SQLAlchemy, MySQL 8.0.
* **重点实现**：
  1. 在 `backend/api/v1/mock/` 中模拟三方企业系统的 RESTful API：
     - `GET /api/v1/mock/hr/employees/{id}`：HR 系统接口
     - `GET /api/v1/mock/erp/inventory`：ERP 库存接口
     - `POST /api/v1/mock/oa/tickets`：OA 工单系统接口
  2. 连接 MySQL 数据库读取持久化数据，保证 Mock 接口具有状态保持。
* **交付物**：`backend/api/v1/mock/` 完整 API 模块。

> #### 📋 提示词模板：`Prompt-Sprint-06-EnterpriseMock`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0011：实现 Sprint 6 “企业三方系统 Mock 接口与 MySQL 持久化”。
> 
> 【具体要求】：
> 1. 在 `backend/api/v1/mock/` 下创建：`hr_mock.py`, `erp_mock.py`, `oa_mock.py` 路由。
> 2. 使用 SQLAlchemy 模型访问 MySQL 中的 `User`, `Ticket`, `Inventory` 数据表。
> 3. 将 Sprint 5 中的 Tool 执行逻辑适配接入该 Mock REST API。
> 4. 编写 `backend/tests/unit/test_mock_systems.py` 验证 API 响应格式与数据库读写。
> 5. 刷盘 `.harness/runs/Issue-0011/` 沙盒证据包。
> ```

---

### 3.6 Sprint 7：Human-in-the-loop 人机协同审批流
* **技术栈**：LangGraph Interrupt & Resume, Checkpointer Threading, Approval State.
* **重点实现**：
  1. **审批阈值判断**：采购金额 $> 5,000$ 元时，Agent 自动进入 `Approval` 状态。
  2. **LangGraph 中断 (`interrupt`)**：挂起 Agent 状态机，将审批单写入 MySQL `Approval` 表，状态标记为 `PENDING`。
  3. **人机恢复 (`resume`)**：暴露 `POST /api/v1/approval/{id}/action`（传入 `approve` / `reject`），主管审批通过后恢复 LangGraph 状态机继续执行后续 Tool 调用。
* **交付物**：人机协同审批节点与 `backend/graph/nodes/approval_node.py`。

> #### 📋 提示词模板：`Prompt-Sprint-07-HumanInTheLoop`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0012：实现 Sprint 7 “Human-in-the-loop 人机协同审批流”。
> 
> 【具体要求】：
> 1. 在 `backend/graph/nodes/approval_node.py` 中实现审批拦截逻辑。
> 2. 使用 LangGraph 的 `interrupt()` 语法在需要主管审批的节点挂起状态机，保存 `thread_id` 与 State。
> 3. 实现审批控制 API `POST /api/v1/approval/action`，接收 `approval_id` 及决策，调用 graph 的 `Command(resume=...)` 恢复运行。
> 4. 编写 `backend/tests/unit/test_approval_flow.py` 模拟完整“申请 -> 中断挂起 -> 主管批准 -> 恢复继续执行”的全流程序。
> 5. 刷盘 `.harness/runs/Issue-0012/` 沙盒证据包。
> ```

---

### 3.7 Sprint 8：WebSocket 双工流式通道与前端 Vue3 对话 UI
* **技术栈**：FastAPI WebSocket, Async Generator, Vue 3, TailwindCSS / Flowbite.
* **重点实现**：
  1. **WebSocket 长连接接口** ([backend/api/v1/chat_ws.py](file:///g:/LLM_Learning/product/backend/api/v1/chat_ws.py))：支持实时 Token 级流式输出（Streaming）及 Agent 节点状态通知（如“正在查询知识库...”、“正在等待主管审批...”）。
  2. **Vue 3 极简 Chat UI** ([frontend/](file:///g:/LLM_Learning/product/frontend/))：实现响应式气泡对话界面、工具调用展示与审批卡片点击。
* **交付物**：WebSocket 实时通信通道及 Vue3 Chat 界面。

> #### 📋 提示词模板：`Prompt-Sprint-08-WebSocketUI`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0013：实现 Sprint 8 “WebSocket 双工流式通道与前端 Vue3 对话 UI”。
> 
> 【具体要求】：
> 1. 在 `backend/api/v1/chat_ws.py` 实现 WebSocket 路由 `/api/v1/ws/chat/{client_id}`。
> 2. 结合 LangGraph `astream_events` 实时向客户端推送 Token 流、思考链及工具执行步骤日志。
> 3. 在 `frontend/` 搭建 Vue3 + Vite + TailwindCSS 聊天组件，支持展示消息流、加载状态及审批卡片。
> 4. 编写 `backend/tests/unit/test_websocket.py` 进行 WS 消息握手与流式传输测试。
> 5. 刷盘 `.harness/runs/Issue-0013/` 证据包。
> ```

---

### 3.8 Sprint 9：Celery 异步任务队列 (OCR / Embedding / Indexing)
* **技术栈**：Celery 5.x, Redis Message Broker, Async Task Workers.
* **重点实现**：
  1. 搭建 Celery 应用 ([backend/tasks/celery_app.py](file:///g:/LLM_Learning/product/backend/tasks/celery_app.py))，使用 Redis 作为 Broker 与 Result Backend。
  2. 离线后台任务实现：
     - `task_process_pdf_ocr`：耗时大文件 OCR 识别任务。
     - `task_build_qdrant_index`：批量文档切片与 Embedding 向量化入库。
* **交付物**：Celery Task Worker 模块及状态查询接口 `GET /api/v1/tasks/{task_id}`。

> #### 📋 提示词模板：`Prompt-Sprint-09-CeleryTasks`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0014：实现 Sprint 9 “Celery 异步任务队列与大文件离线处理”。
> 
> 【具体要求】：
> 1. 在 `backend/tasks/` 下配置 `celery_app.py`，连接 Redis 作为消息队列。
> 2. 定义异步 Task：`async_ingest_document(file_path)`（负责后台解压、切片、Embedding 和写入 Qdrant）。
> 3. 改造 `POST /api/v1/knowledge/upload` 支持传入 `async=true` 参数提交 Celery 任务并立即返回 `task_id`。
> 4. 暴露 `GET /api/v1/tasks/{task_id}/status` 查询异步任务进度。
> 5. 编写 `backend/tests/unit/test_celery_tasks.py` 验证任务投递与状态回调。
> 6. 刷盘 `.harness/runs/Issue-0014/` 证据包。
> ```

---

### 3.9 Sprint 10：AI Infra (vLLM / Prompt Cache / Token Monitor / Fallback)
* **技术栈**：vLLM / Ollama (Local Inference), Redis Hash Cache, Token Counter, Model Fallback.
* **重点实现**：
  1. **Prompt Cache 机制**：针对长 System Prompt 计算 Hash 并在 Redis 缓存命中结果（命中率目标 $> 70\%$）。
  2. **Token Cost Monitor**：记录每次 LLM 调用的 Input/Output Token 数量并统计开销。
  3. **Model Fallback 降级**：优先级 `GPT-4o -> Qwen3 -> DeepSeek -> Rule Engine`。
* **交付物**：`backend/core/llm_infra.py` 基础设施封装。

> #### 📋 提示词模板：`Prompt-Sprint-10-AIInfra`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0015：实现 Sprint 10 “AI Infra 基础设施：Prompt Cache、Token Monitor 与 Fallback”。
> 
> 【具体要求】：
> 1. 在 `backend/core/llm_infra.py` 中实现 `LLMGateway` 类。
> 2. 基于 Redis 实现 Prompt Hash Cache 逻辑，重复 Prompt 直接返回缓存响应。
> 3. 实现 Token 统计与成本计算中间件，将开销日志写入 MySQL 或 Redis。
> 4. 实现模型降级策略（支持主模型超时或报错时自动 Try-Catch 切换至备选模型）。
> 5. 编写 `backend/tests/unit/test_llm_infra.py` 验证 Cache 命中与降级回退。
> 6. 刷盘 `.harness/runs/Issue-0015/` 沙盒证据包。
> ```

---

### 3.10 Sprint 11：RAG Evaluation 自动化评估 (RAGAS)
* **技术栈**：RAGAS Framework, Faithfulness, Context Recall, Answer Relevance, Benchmark Datasets.
* **重点实现**：
  1. 编写 [benchmark/eval_ragas.py](file:///g:/LLM_Learning/product/benchmark/) 评估脚本。
  2. 加载标注数据集 `benchmark/test-dataset.json`，计算 Faithfulness ($> 0.90$)、Recall 与 Precision。
  3. 自动导出 HTML / Markdown 评测报告。
* **交付物**：RAG 评估测试集与自动评测脚本。

> #### 📋 提示词模板：`Prompt-Sprint-11-RAGASEval`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0016：实现 Sprint 11 “RAGAS 自动化质量评估与回归测试套件”。
> 
> 【具体要求】：
> 1. 在 `benchmark/` 目录下构建标准评测数据集 `test-dataset.json`（包含 30 组 question, ground_truth, contexts）。
> 2. 编写 `benchmark/eval_ragas.py` 脚本，调用 RAGAS 评估库计算 Faithfulness, Answer Relevance, Context Recall 得分。
> 3. 当 Faithfulness < 0.90 时自动触发错误告警并阻止流水线发布。
> 4. 编写 `backend/tests/unit/test_eval_pipeline.py` 进行评估集成测试。
> 5. 刷盘 `.harness/runs/Issue-0016/` 证据包。
> ```

---

### 3.11 Sprint 12：数字化转型 Demo 与 n8n / Dify 工作流集成
* **技术栈**：n8n / Dify Webhook API, Mock Enterprise WeChat / Slack Bot.
* **重点实现**：
  1. 暴露 Webhook 端点 `POST /api/v1/webhook/workflow` 支持接收 n8n / Dify 的工作流事件触发。
  2. 实现 Mock 企业微信推送消息通知。
* **交付物**：全流程 SOP 自动化 Demo 接入。

> #### 📋 提示词模板：`Prompt-Sprint-12-DigitalDemo`
> ```markdown
> 请按照 Harness Engineering 规范指派 Issue-0017：实现 Sprint 12 “数字化转型 Demo 与 n8n / Dify Webhook 工作流集成”。
> 
> 【具体要求】：
> 1. 在 `backend/api/v1/workflow.py` 实现 Webhook 触发路由 `POST /api/v1/webhook/event`。
> 2. 模拟接入 n8n / Dify 节点，实现当审批通过后自动触发 Webhook 通知企微 Bot。
> 3. 整理全流程联调测试脚本，演示“用户提问 -> Intent Router -> RAG -> 审批 -> 企业工作流执行 -> 企微通知”闭环。
> 4. 刷盘 `.harness/runs/Issue-0017/` 证据包，完成项目终极归档。
> ```

---

## 4. 提示词模板使用指南 (How to Use Prompts)

当你准备开始推进任意未完成模块时，只需按照以下步骤操作：

1. **选择对应的提示词模板**（如 `Prompt-Sprint-03-HybridSearch`）。
2. **在对话中直接发送该提示词**。
3. **系统将自动切换为 Harness SOP 流程**：依次自动创建 `.harness/runs/Issue-XXXX/` 证据包、运行 `DeveloperAgent` 编码、触发 `pytest` / `ruff` 检查、调用 `ReviewerAgent` 审计并闭环关单！
