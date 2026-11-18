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
  "event": "user_message",
  "text": "我要采购3台测试机，帮我起草采购流程"
}
```

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

#### 2.4.1 上传知识库文档
- **接口路径**：`POST /knowledge/upload`
- **功能描述**：上传本地 PDF、Word、Excel 等文件，系统自动存入 S3 并发起 Celery 异步解析任务。
- **Content-Type**: `multipart/form-data`
- **请求参数**:
  - `file`: 二进制文件数据
  - `category`: 字符串，如 `IT_Policy`
  - `security_level`: 字符串，如 `CONFIDENTIAL`
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "文件上传成功，异步解析任务已提交",
    "data": {
      "doc_id": 105,
      "title": "IT采购管理条例.pdf",
      "file_type": "pdf",
      "status": "PARSING",
      "task_id": "celery-task-uuid-889100287"
    }
  }
  ```

#### 2.4.2 获取已上传文件列表
- **接口路径**：`GET /knowledge/documents`
- **功能描述**：获取当前企业上传的文档清单及其解析状态。
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": [
      {
        "doc_id": 105,
        "title": "IT采购管理条例.pdf",
        "file_type": "pdf",
        "file_size": 2049182,
        "status": "PARSED",
        "created_at": "2026-07-21T15:00:00Z"
      }
    ]
  }
  ```

#### 2.4.3 删除文档
- **接口路径**：`DELETE /knowledge/documents/{doc_id}`
- **功能描述**：删除文档的主表数据，并物理清理 Qdrant 中对应的向量 Point 集合。
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "文档及相关向量索引已彻底删除",
    "data": null
  }
  ```

#### 2.4.4 测试混合检索
- **接口路径**：`POST /knowledge/search`
- **功能描述**：直接调用混合检索（Dense + Sparse）与重排引擎，供开发与评估测试。
- **请求 Body (JSON)**:
  ```json
  {
    "query": "笔记本采购金额上限是多少",
    "department": "R&D",
    "top_k": 3
  }
  ```
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": [
      {
        "chunk_id": 1821,
        "doc_id": 105,
        "document_title": "IT采购管理条例.pdf",
        "text": "第二条：研发部门员工组装测试用机，单台预算上限为人民币 10,000 元...",
        "rerank_score": 0.9412
      }
    ]
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

