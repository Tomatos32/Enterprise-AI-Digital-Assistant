# Enterprise AI Digital Assistant - OpenAPI Specification
> 企业级 AI 数字员工平台接口设计规范 (V1.0)

---

## 1. 全局约定

### 1.1 基础路径 (Base URL)
- 系统所有 API 请求均基于统一前缀：`/api/v1`

### 1.2 认证授权 (Authentication)
- 采用 **JWT (JSON Web Token)** Bearer 认证机制。
- 客户端在 HTTP Header 中携带：`Authorization: Bearer <access_token>`。
- WebSocket 连接在握手建立阶段，通过 Query Parameter 携带 Token：`ws://domain/api/v1/chat/ws/{session_id}?token=<access_token>`。

### 1.3 通用响应格式 (Standard Response Format)
除流式推送（SSE / WebSockets）外，所有的常规 HTTP 请求均返回如下 JSON 格式：

```json
{
  "code": 200, 
  "message": "success",
  "data": {}
}
```

通用错误返回：
```json
{
  "code": 400,
  "message": "请求参数校验失败",
  "data": null
}
```

---

## 2. API 接口定义

### 2.1 认证管理 (Authentication)

#### 2.1.1 用户登录
- **接口路径**：`POST /auth/login`
- **功能描述**：输入账号密码，验证成功后返回 JWT Access Token 及标准化身份元数据（`username`、`display_name`、`role`、`role_label`、`department`）。
- **请求 Body (JSON)**:
  ```json
  {
    "username": "manager",
    "password": "<your-password>"
  }
  ```
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "role": "manager",
      "username": "manager",
      "display_name": "陈志远",
      "department": "采购管理部",
      "role_label": "部门主管"
    }
  }
  ```

#### 2.1.2 获取当前认证用户档案
- **接口路径**：`GET /auth/me`
- **鉴权要求**：Header 携带 `Authorization: Bearer <access_token>`。
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "username": "manager",
      "display_name": "陈志远",
      "role": "manager",
      "department": "采购管理部",
      "role_label": "部门主管"
    }
  }
  ```

#### 2.1.3 获取演示身份列表（仅限开发/测试或 Mock 模式）
- **接口路径**：`GET /auth/identities`
- **功能描述**：返回用于角色上下文切换的非敏感身份列表（绝不包含密码或密码哈希）；在 `ENVIRONMENT=production` 且 `USE_MOCK_SYSTEMS=False` 时返回 `403`。
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": [
      {
        "username": "employee",
        "display_name": "林小晴",
        "role": "employee",
        "role_label": "普通员工",
        "department": "人力资源部"
      },
      {
        "username": "manager",
        "display_name": "陈志远",
        "role": "manager",
        "role_label": "部门主管",
        "department": "采购管理部"
      },
      {
        "username": "admin",
        "display_name": "周明辉",
        "role": "admin",
        "role_label": "系统管理员",
        "department": "IT 系统管理部"
      }
    ]
  }
  ```

#### 2.1.4 快捷角色上下文切换（仅限开发/测试或 Mock 模式）
- **接口路径**：`POST /auth/switch-role`
- **功能描述**：在开发/演示模式下签发目标身份的真实 JWT Access Token；生产环境禁用并返回 `403`。
- **请求 Body (JSON)**:
  ```json
  {
    "username": "admin"
  }
  ```
- **响应 Data**：与 `POST /auth/login` 保持一致。

---

### 2.2 会话管理 (Session Management)

> **身份归属隔离约定**：当请求携带 `Authorization: Bearer <access_token>` 时，所有会话接口强制以当前认证用户 `current_user.username` 作为归属边界（忽略外部伪造的 `user_id` 参数），跨用户读写/改名/删除/中断会话返回 HTTP `403`。未携带 Header 时保持无头测试向后兼容。

#### 2.2.1 获取历史会话列表
- **接口路径**：`GET /chat/sessions`
- **功能描述**：按 `updated_at` 倒序获取当前用户未删除的历史会话列表（携带 Bearer Token 时自动按 `current_user.username` 过滤）。
- **请求 Query 参数**:
  - `user_id`: 字符串（无 Token 时的兼容过滤键，默认值 `u_ws_default`）
  - `limit`: 整数，默认值 `50`（1~100）
  - `offset`: 整数，默认值 `0`
- **响应 Data**:
  ```json
  [
    {
      "id": 1,
      "session_id": "sess_9a7d3bf015bd",
      "user_id": "employee",
      "title": "关于采购开发服务器的咨询",
      "is_deleted": false,
      "created_at": "2026-11-16T15:00:00",
      "updated_at": "2026-11-16T15:10:00"
    }
  ]
  ```

#### 2.2.2 创建会话
- **接口路径**：`POST /chat/sessions`
- **功能描述**：新建一条持久化会话；携带 Bearer Token 时强制绑定 `current_user.username`。
- **请求 Body (JSON)**:
  ```json
  {
    "title": "新对话",
    "user_id": "employee"
  }
  ```

#### 2.2.3 获取会话详情消息历史
- **接口路径**：`GET /chat/sessions/{session_id}/messages`
- **功能描述**：获取当前会话历史消息（含 `thought`、`duration_seconds`、`thought_steps`、`sources`），跨用户访问返回 `403`。

#### 2.2.4 重命名与删除会话
- **接口路径**：`PUT /chat/sessions/{session_id}/title`、`DELETE /chat/sessions/{session_id}`
- **功能描述**：重命名或软删除指定会话，携带 Bearer Token 时校验会话归属权，越权返回 `403`。

---

### 2.3 实时流式通信 (WebSocket)

#### 2.3.1 对话与执行流式管道 (Duplex Websocket)
- **协议地址**：`WS /ws/chat/{client_id}?token=<access_token>`
- **鉴权要求**：推荐在握手 Query `?token=<access_token>` 或 `Authorization: Bearer <token>` 中提供 JWT。若提供无效/过期 Token，服务端下发 `{"type": "error", "status": 401}` 并以关闭码 `4401` 断开；若绑定已有会话但归属其他用户，下发 `{"type": "error", "status": 403}` 拒绝写入。
- **工作流向说明**：
  1. 客户端发送 JSON 格式的用户请求消息。
  2. 服务端实时推送各个中间节点状态（Intent Router、Retrieval、Tool Call 等）的事件，并以分片流式输出（Tokens Chunk）最终回复。

##### 1. 客户端输入消息 (Client Message Payload)
```json
{
  "query": "请帮我核对研发部 MacBook Pro 采购申请的最新制度标准，并提交审批。",
  "session_id": "sess_a1b2c3d4",
  "metadata": {
    "data_source": "ERP 采购与供应链",
    "data_source_id": "erp_sap",
    "slash_command": ""
  }
}
```
> **数据源与快捷指令元数据契约 (`Issue-0060`)**：
> - `metadata.data_source_id`：支持 `kb_all`（全量企业规章制度库 -> `retrieve`）、`db_mysql`（MySQL 业务台账 -> `tool`）、`erp_sap`（ERP 采购与供应链 -> 按制度咨询/审批/库存动态分流），向后兼容仅传 `metadata.data_source` 名称。
> - `metadata.slash_command`：支持 `/kb`（制度检索）、`/audit`（无提交意图时为角色感知只读待审查询，仅 `manager`/`admin` 可阅全局队列，普通员工与未认证调用严格 fail-closed 拦截；含采购提交意图时路由至 `approval`）、`/help`（功能与快捷指令指引）、`/ticket`（快速建单）。
> - **内部路由与改写事件隔离 (`Issue-0060` & `Issue-0061`)**：LangGraph 混合认知路由器 (`router` 节点) 与多轮上下文 Query 改写器 (`retrieve` 节点) 的轻量非思考 LLM 调用均已与客户端事件流完全隔离（`callbacks=[]` + `langgraph_node in ("router", "retrieve")` / `internal_router` / `internal_rewriter` 过滤），绝不向用户流推送内部 JSON，亦不污染 TTFT 首字延迟指标。服务端 `state["metadata"]` 内部留存改写诊断字段（`rewritten_query`、`sub_queries`、`detected_domains`、`domain_weights`、`rewrite_method`、`coreference_resolved`、`anchor_topic`），不暴露给普通员工前端视图。

##### 2. 服务端实时推送事件序列 (Server Message Payloads)

- **意图路由判定状态事件 (Event: `node_intent`)**
  ```json
  {
    "event": "node_intent",
    "intent": "WORKFLOW_PURCHASE",
    "message": "数字员工正在为您规划采购申报流程..."
  }
  ```

- **RAG 检索动作事件 (Event: `node_retrieve`)**
  ```json
  {
    "event": "node_retrieve",
    "status": "searching",
    "message": "正在知识库中匹配《企业IT采购资产明细与合规标准》..."
  }
  ```

- **RAG 检索上下文推送 (Event: `node_retrieve_result`)**
  ```json
  {
    "event": "node_retrieve_result",
    "sources": [
      {
        "doc_id": 12,
        "title": "IT采购管理条例.pdf",
        "chunk_id": 156,
        "score": 0.892
      }
    ]
  }
  ```

- **工具执行开始事件 (Event: `node_tool_start`)**
  ```json
  {
    "event": "node_tool_start",
    "tool_name": "query_inventory",
    "arguments": {
      "item_code": "PC-TEST-002"
    }
  }
  ```

- **工具执行完毕事件 (Event: `node_tool_end`)**
  ```json
  {
    "event": "node_tool_end",
    "tool_name": "query_inventory",
    "status": "success",
    "result": {
      "available_quantity": 0,
      "price": 4500.00
    }
  }
  ```

- **流式文本分片事件 (Event: `text_chunk`)**
  ```json
  {
    "event": "text_chunk",
    "delta": "根据"
  }
  ```

- **中途人工审批拦截事件 (Event: `approval_interrupt`)**
  ```json
  {
    "event": "approval_interrupt",
    "approval_id": 182,
    "ticket_id": 10092,
    "message": "由于采购总金额(13,500元)超限，此任务已被挂起，正在向您的主管[张经理]发起审批申请。审批通过后，我将在此为您继续执行。"
  }
  ```

- **最终生成完成事件 (Event: `done`)**
  ```json
  {
    "event": "done",
    "session_id": "8f8b340a-24ad-47cc-980b-1934ba70a599",
    "summary": {
      "prompt_tokens": 1540,
      "completion_tokens": 420,
      "cost_usd": 0.000483
    }
  }
  ```

---

### 2.4 知识库管理 (RAG Management)

> **RBAC 权限边界**：`GET /knowledge/status` 与 `GET/POST /knowledge/search` 对已登录全部角色（`employee`、`manager`、`admin`）开放；文档上传（`POST /knowledge/upload`）、文档台账查询（`GET /knowledge/documents`）与全库重建/增量同步（`POST /knowledge/sync`）强制要求 `Depends(require_role([RoleEnum.ADMIN]))`（未认证返回 `401`，非管理员返回 `403`）。

#### 2.4.1 查询知识库向量底座状态
- **接口路径**：`GET /knowledge/status`
- **鉴权要求**：`employee` / `manager` / `admin`（未认证返回 `401`）
- **功能描述**：返回 Qdrant 运行模式、集合名称、点位总数、向量维度、Embedding 引擎与内置/上传文档统计。

#### 2.4.2 获取已索引知识文档清单（管理员专属）
- **接口路径**：`GET /knowledge/documents`
- **鉴权要求**：仅限 `admin`（非管理员返回 `403`）
- **功能描述**：返回 `docs/sample_kb/` 内置标准制度库与 `backend/data/` 管理员上传文档台账（含分类、格式、体积、切片数、执行模式与最近更新时间）。

#### 2.4.3 上传知识库文档（管理员专属）
- **接口路径**：`POST /knowledge/upload`
- **鉴权要求**：仅限 `admin`（非管理员返回 `403`）
- **功能描述**：接收单文件（白名单 `.md`、`.pdf`、`.xlsx`、`.xls`、`.txt`，防路径穿越、非空且 ≤ 20 MB），支持同步快速入库（`is_async=false`）与异步入库（`is_async=true`：优先 Celery 队列，Redis/Worker 未启动时自动平滑降级至 FastAPI 后台异步任务队列 `async_fallback`）。
- **Content-Type**: `multipart/form-data`
- **请求参数**:
  - `file`: 二进制文件数据
  - `category`: 可选业务分类（如 `HR`、`PROCUREMENT`、`FINANCE`、`IT`、`SECURITY`、`CS`、`GENERAL`）
  - `is_async`: 布尔值（默认 `false`）
- **响应 Data（同步模式示例）**:
  ```json
  {
    "code": 200,
    "message": "Knowledge document uploaded and indexed successfully",
    "data": {
      "filename": "gpu_quota_policy.md",
      "filepath": "backend/data/gpu_quota_policy.md",
      "size_bytes": 124,
      "category": "IT",
      "chunks_indexed": 1,
      "chunks_count": 1,
      "task_id": "sync-a1b2c3d4e5f6",
      "status": "COMPLETED",
      "execution_mode": "sync",
      "is_async": false,
      "uploader": "admin"
    }
  }
  ```
- **响应 Data（异步/降级模式示例）**:
  ```json
  {
    "code": 200,
    "message": "Async document ingestion task submitted via local fallback queue",
    "data": {
      "filename": "async_policy.pdf",
      "filepath": "backend/data/async_policy.pdf",
      "size_bytes": 48120,
      "category": "PROCUREMENT",
      "task_id": "fb-9f8e7d6c5b4a",
      "status": "SUBMITTED",
      "is_async": true,
      "execution_mode": "async_fallback",
      "fallback_reason": "Redis Broker (localhost:6379) 未在线 (ConnectionRefusedError)，已平滑降级为后台异步队列",
      "uploader": "admin"
    }
  }
  ```

#### 2.4.4 全库索引同步与重建（管理员专属）
- **接口路径**：`POST /knowledge/sync`
- **鉴权要求**：仅限 `admin`（非管理员返回 `403`）
- **请求 Query 参数**:
  - `recreate`: 布尔值（默认 `false`；`true` 时清空重建 Qdrant 集合并重新全量向量化内置库与上传库）
- **功能描述**：重索引 `docs/sample_kb/` 与 `backend/data/` 有效文档，刷新 `HybridRetriever` BM25 索引并返回同步自检报告与任务 ID。

#### 2.4.5 混合检索知识库
- **接口路径**：`POST /knowledge/search`、`GET /knowledge/search`
- **鉴权要求**：`employee` / `manager` / `admin`（未认证返回 `401`）
- **功能描述**：执行 Qdrant 稠密检索 + BM25 稀疏检索 + RRF 融合 + Reranker 重排。
- **POST 请求 Body (JSON)**:
  ```json
  {
    "query": "笔记本采购金额上限是多少",
    "top_k": 5,
    "category_filter": "PROCUREMENT"
  }
  ```
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "Hybrid retrieval completed",
    "data": {
      "query": "笔记本采购金额上限是多少",
      "count": 1,
      "results": [
        {
          "content": "采购超过 5,000 元需提交主管审批...",
          "metadata": {
            "filename": "02_PROCUREMENT_采购与供应链合规SOP.md",
            "category": "PROCUREMENT",
            "rerank_score": 0.9412
          }
        }
      ]
    }
  }
  ```

---

### 2.5 流程与审批控制 (Workflow & Approval)

> **角色权限边界**：当请求携带 `Authorization: Bearer <access_token>` 时，审批查询与审批决策接口严格限制 `manager`（部门主管）或 `admin`（系统管理员）访问；普通员工（`employee`）越权访问返回 HTTP `403`。

#### 2.5.1 获取待审批与全量审批列表
- **接口路径**：`GET /approval/pending`、`GET /approval/list`
- **功能描述**：部门主管或系统管理员获取待处理（`PENDING`）或全部历史审批单据列表。
- **响应 Data**:
  ```json
  {
    "status": "SUCCESS",
    "count": 1,
    "data": [
      {
        "approval_id": "APP-20261116-1001",
        "thread_id": "sess_8f8b340a24ad",
        "item_name": "MacBook Pro 16",
        "quantity": 1,
        "unit_price": 22999.0,
        "total_price": 22999.0,
        "department": "采购管理部",
        "reason": "AI 数字人研发高配置要求",
        "status": "PENDING",
        "created_at": "2026-11-16 15:53:00"
      }
    ]
  }
  ```

#### 2.5.2 处理审批单 (批准/拒绝)
- **接口路径**：`POST /approval/action`
- **功能描述**：主管或管理员审批同意或驳回，唤醒对应的 LangGraph 挂起线程并附带动态审批人署名（`<姓名> (<部门> · <角色>)`）推送通知。
- **请求 Body (JSON)**:
  ```json
  {
    "approval_id": "APP-20261116-1001",
    "action": "approve",
    "comment": "情况属实，予以通过"
  }
  ```
- **响应 Data**:
  ```json
  {
    "status": "SUCCESS",
    "approval_id": "APP-20261116-1001",
    "thread_id": "sess_8f8b340a24ad",
    "action": "approve",
    "approver": "陈志远 (采购管理部 · 部门主管)",
    "db_status": "APPROVED",
    "graph_output": "Resumed"
  }
  ```

---

### 2.6 运维监控与成本分析 (Analytics)

#### 2.6.1 获取 Token 用量与成本看板
- **接口路径**：`GET /analytics/token-usage`
- **功能描述**：按时间窗口（如日、周、月）统计大模型 Token 消耗及美元开销占比。
- **请求 Query 参数**:
  - `start_date`: 格式 `YYYY-MM-DD`
  - `end_date`: 格式 `YYYY-MM-DD`
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "total_cost_usd": 154.281,
      "total_tokens": 12894100,
      "model_distribution": [
        {
          "model_name": "GPT-4o-Mini",
          "tokens_used": 8942100,
          "cost_usd": 124.52
        },
        {
          "model_name": "Local-Qwen-72B",
          "tokens_used": 3952000,
          "cost_usd": 29.761
        }
      ]
    }
  }
  ```

---

### 2.7 管理员大模型参数与节点配置中心 (Admin Control Plane)

> **严格鉴权与零密钥外泄规范**：本分组全部接口强制要求 `Depends(require_role([RoleEnum.ADMIN]))`；未登录返回 HTTP `401`，普通员工（`employee`）与部门主管（`manager`）越权访问返回 HTTP `403`。所有响应均只返回脱敏后的密钥掩码与布尔配置状态，**严禁回传明文 `LLM_API_KEY` 或 `SECRET_KEY`**。

#### 2.7.1 读取脱敏运行时配置与引擎预设
- **接口路径**：`GET /admin/config`
- **功能描述**：读取当前生效的白名单大模型参数、LangGraph / RAG 检索配置、脱敏凭据状态、引擎遥测及预设清单。
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "管理员运行时配置读取成功",
    "data": {
      "llm_provider": "auto",
      "llm_model": "deepseek-chat",
      "llm_api_base": null,
      "llm_thinking": false,
      "llm_temperature": 0.2,
      "llm_max_tokens": 4096,
      "rag_top_k": 3,
      "rag_min_score": 0.16,
      "system_prompt_instruction": "",
      "api_key_configured": false,
      "api_key_masked": "未配置",
      "jwt_secret_configured": true,
      "jwt_secret_masked": "****** (HS256 已启用保护)",
      "active_engine": "LocalEnterpriseChatModel",
      "updated_at": null,
      "updated_by": null
    }
  }
  ```

#### 2.7.2 更新并热生效白名单参数
- **接口路径**：`PUT /admin/config`
- **功能描述**：校验并热更新白名单参数（同步刷新内存 `settings`、持久化非密钥字段至 `logs/runtime_config.json`，并立即作用于 `get_chat_llm`、`HybridRetriever`、`retrieve_node` 与 `generate_node`）。支持只写字段 `llm_api_key`（留空或含 `****` 掩码保留原值）与 `clear_api_key`。
- **请求 Body (JSON)**:
  ```json
  {
    "llm_provider": "ollama",
    "llm_model": "qwen3.5:2b",
    "llm_api_base": "http://127.0.0.1:11434",
    "llm_thinking": true,
    "llm_temperature": 0.25,
    "llm_max_tokens": 4096,
    "rag_top_k": 5,
    "rag_min_score": 0.24,
    "system_prompt_instruction": "涉及报销与采购金额时须列出审批层级。"
  }
  ```

#### 2.7.3 恢复启动基线默认配置
- **接口路径**：`POST /admin/config/reset`
- **功能描述**：将全部运行时白名单参数与 `LLM_API_KEY` 恢复至进程启动期基线值，并清理 `logs/runtime_config.json` 覆盖文件。

#### 2.7.4 非破坏性连通性探活测试
- **接口路径**：`POST /admin/config/probe`
- **功能描述**：针对当前或表单预览的 `llm_provider`、`llm_model`、`llm_api_base`、`llm_thinking` 执行非破坏性连通性探活（Ollama `/api/tags`、OpenAI 兼容 `/models` 或离线 `local_fallback`），并返回本地 Qdrant 向量集合健康点数与延迟毫秒数。

---

### 2.8 管理员知识入库与异步任务中心 (Admin Tasks Center)

> **严格鉴权规范**：本分组全部接口强制要求 `Depends(require_role([RoleEnum.ADMIN]))`；未认证返回 HTTP `401`，`employee` / `manager` 越权返回 HTTP `403`。状态查询自动兼容 Celery `AsyncResult` 与本地线程安全台账 `logs/knowledge_tasks_ledger.json`，Redis 离线时不报错崩溃。

#### 2.8.1 获取近期文档入库与同步任务台账
- **接口路径**：`GET /tasks`
- **请求 Query 参数**:
  - `limit`: 整数（1~100，默认 `30`）
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "Tasks ledger retrieved successfully",
    "data": {
      "tasks": [],
      "summary": {
        "total": 2,
        "running": 0,
        "completed": 2,
        "failed": 0
      },
      "celery_eager_mode": false
    }
  }
  ```

#### 2.8.2 查询单个异步/同步任务进度与 5 阶段明细
- **接口路径**：`GET /tasks/{task_id}/status`
- **功能描述**：返回单条任务状态（`PENDING` / `PROGRESS` / `SUCCESS` / `FAILURE`）、当前阶段（`QUEUED` / `PARSING` / `CHUNKING` / `INDEXING` / `COMPLETED` / `FAILED`）、百分比进度与 5 阶段 `steps` 数组（供前端 `@vue-bits/StatusMark` 渲染）。
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "Task 'sync-a1b2c3d4e5f6' status retrieved",
    "data": {
      "task_id": "sync-a1b2c3d4e5f6",
      "status": "SUCCESS",
      "stage": "COMPLETED",
      "stage_label": "向量入库与索引刷新完成",
      "ready": true,
      "successful": true,
      "progress": { "current": 100, "total": 100 },
      "steps": [
        { "key": "QUEUED", "label": "任务排队", "status": "success" },
        { "key": "PARSING", "label": "文档解析", "status": "success" },
        { "key": "CHUNKING", "label": "语义切片", "status": "success" },
        { "key": "INDEXING", "label": "向量入库", "status": "success" },
        { "key": "COMPLETED", "label": "完成入库", "status": "success" }
      ]
    }
  }
  ```

---

### 2.9 管理员系统遥测、工具审计与 SLA 监控看板 (Admin Monitoring & SLA)

> **严格鉴权与零密钥外泄规范**：本分组接口强制要求 `Depends(require_role([RoleEnum.ADMIN]))`；未认证返回 HTTP `401`，普通员工（`employee`）与部门主管（`manager`）越权访问返回 HTTP `403`。所有响应均只返回脱敏后的密钥掩码（`api_key_masked`）与脱敏工具审计摘要（自动抹除 `sk-*` / `Bearer *` 凭据片段），**严禁回传明文 `LLM_API_KEY` 或 `SECRET_KEY`**。

#### 2.9.1 获取系统遥测、工具审计与 P0~P4 SLA 监控全景
- **接口路径**：`GET /admin/monitoring/overview`
- **功能描述**：聚合实时组件健康探针（关系型数据库、Redis、Qdrant 向量库、当前活跃大模型引擎）、Prometheus 运行态指标（活跃 WebSocket 连接、Celery 队列深度、按模型拆分的输入/输出 Token、Prompt Cache 命中率、非累积 5 档 TTFT 首字延迟分桶）、`ToolRegistry` 工具调用统计与近期脱敏审计流水，以及数据库会话/消息、审批闭环率与 P0~P4 企业服务工单 SLA 履约全景。
- **请求 Query 参数**:
  - `audit_limit`: 整数（1~100，默认 `20`），控制返回的近期工具调用安全审计流水条数
  - `ticket_limit`: 整数（1~100，默认 `20`），控制返回的近期企业服务工单台账条数
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "系统遥测、工具审计与 SLA 监控全景已加载",
    "data": {
      "generated_at": "2026-11-19T09:34:30.165344+00:00",
      "operator": {
        "username": "admin",
        "display_name": "周明辉",
        "role": "admin",
        "department": "IT 系统管理部"
      },
      "system_health": {
        "overall_status": "DEGRADED",
        "components": [],
        "llm_engine": {
          "provider": "ollama",
          "model": "qwen3.5:2b",
          "active_engine": "NativeOllamaChatModel",
          "thinking": false,
          "has_api_key": true,
          "api_key_masked": "**** (已配置)",
          "endpoint": "http://127.0.0.1:11434"
        },
        "qdrant": {
          "status": "healthy",
          "client_mode": "local_storage",
          "collection_name": "enterprise_knowledge",
          "points_count": 7365,
          "vector_size": 1024
        },
        "active_ingestion_tasks": 0
      },
      "telemetry": {
        "active_websocket_connections": 0,
        "celery_queue_depth": 0,
        "tokens": { "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "by_model": [] },
        "prompt_cache": { "hits": 0, "misses": 0, "total_lookups": 0, "hit_rate_percent": 0.0 },
        "ttft": { "total_observations": 0, "avg_ms": 0.0, "buckets": [] },
        "tools": { "registered_count": 6, "total_calls": 0, "success_calls": 0, "error_calls": 0, "success_rate_percent": 0.0, "by_tool": [], "recent_audits": [] }
      },
      "business": {
        "chat": { "active_sessions": 0, "total_sessions": 0, "total_messages": 0, "user_messages": 0, "assistant_messages": 0, "avg_thinking_seconds": 0.0 },
        "approvals": { "pending_count": 0, "approved_count": 0, "rejected_count": 0, "closed_count": 0, "total_count": 0, "closure_rate_percent": 0.0 },
        "sla": { "total_tickets": 0, "open_tickets": 0, "closed_tickets": 0, "breached_tickets": 0, "overall_compliance_percent": 100.0, "tiers": [], "recent_tickets": [] }
      }
    }
  }
  ```



