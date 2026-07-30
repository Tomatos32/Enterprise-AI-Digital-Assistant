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
- **功能描述**：输入账号密码，验证成功后返回 Access Token 及 Refresh Token。
- **请求 Body (JSON)**:
  ```json
  {
    "username": "zhangsan",
    "password": "SecurePassword123"
  }
  ```
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "登录成功",
    "data": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVC...",
      "token_type": "bearer",
      "expires_in": 1800,
      "user_info": {
        "id": 1,
        "username": "zhangsan",
        "department": "R&D",
        "role": "EMPLOYEE"
      }
    }
  }
  ```

#### 2.1.2 令牌刷新
- **接口路径**：`POST /auth/refresh`
- **功能描述**：使用 Refresh Token 获取新的 Access Token，保持登录状态。
- **请求 Body (JSON)**:
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVC..."
  }
  ```
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "token刷新成功",
    "data": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "expires_in": 1800
    }
  }
  ```

---

### 2.2 会话管理 (Session Management)

#### 2.2.1 获取历史会话列表
- **接口路径**：`GET /chat/sessions`
- **功能描述**：分页获取当前登录用户历史创建的所有会话列表。
- **请求 Query 参数**:
  - `page`: 整数，默认值 1
  - `size`: 整数，默认值 20
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "total": 12,
      "page": 1,
      "size": 20,
      "items": [
        {
          "session_id": "8f8b340a-24ad-47cc-980b-1934ba70a599",
          "title": "关于采购开发服务器的咨询",
          "langgraph_thread_id": "thread_8f8b340a_24ad",
          "created_at": "2026-07-21T15:00:00Z",
          "updated_at": "2026-07-21T15:10:00Z"
        }
      ]
    }
  }
  ```

#### 2.2.2 创建会话
- **接口路径**：`POST /chat/sessions`
- **功能描述**：新建一条会话 thread 并生成对应的唯一 ID。
- **请求 Body (JSON)**:
  ```json
  {
    "title": "新会话"
  }
  ```
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "会话创建成功",
    "data": {
      "session_id": "9a7d3bf0-15bd-44ee-a541-628b030bbbb0",
      "title": "新会话",
      "langgraph_thread_id": "thread_9a7d3bf0_15bd",
      "created_at": "2026-07-21T15:52:00Z"
    }
  }
  ```

#### 2.2.3 获取会话详情消息历史
- **接口路径**：`GET /chat/sessions/{session_id}/messages`
- **功能描述**：获取当前会话历史的消息列表，供前端重塑渲染对话上下文。
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": [
      {
        "id": 1001,
        "role": "user",
        "content": "请帮我查一下服务器的最新安全规范",
        "tool_calls": null,
        "created_at": "2026-07-21T15:01:00Z"
      },
      {
        "id": 1002,
        "role": "assistant",
        "content": "根据《企业核心服务器管理制度V2.0》，所有服务器...",
        "tool_calls": null,
        "created_at": "2026-07-21T15:01:05Z"
      }
    ]
  }
  ```

#### 2.2.4 删除会话
- **接口路径**：`DELETE /chat/sessions/{session_id}`
- **功能描述**：级联删除会话及历史消息。
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "会话删除成功",
    "data": null
  }
  ```

---

### 2.3 实时流式通信 (WebSocket)

#### 2.3.1 对话与执行流式管道 (Duplex Websocket)
- **协议地址**：`WS /chat/ws/{session_id}`
- **鉴权要求**：在握手 Query 中提供 Token。
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

#### 2.5.1 获取当前待办审批列表
- **接口路径**：`GET /workflow/approvals`
- **功能描述**：主管级账户登录后，查询分配给其个人的待审批任务。
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": [
      {
        "approval_id": 182,
        "ticket_id": 10092,
        "title": "研发部张三的测试机采购申请",
        "description": "物料编码: PC-TEST-002, 数量: 3台, 总价: 13,500元",
        "langgraph_thread_id": "thread_8f8b340a_24ad",
        "created_at": "2026-07-21T15:53:00Z"
      }
    ]
  }
  ```

#### 2.5.2 处理审批单 (批准/拒绝)
- **接口路径**：`POST /workflow/approvals/{approval_id}/action`
- **功能描述**：审批同意或驳回。审批通过后，调用内部 LangGraph Thread Resume 命令，唤醒对应的智能体线程。
- **请求 Body (JSON)**:
  ```json
  {
    "status": "APPROVED",
    "comments": "情况属实，予以通过"
  }
  ```
- **响应 Data**:
  ```json
  {
    "code": 200,
    "message": "审批提交成功，相关智能体已恢复运行",
    "data": {
      "approval_id": 182,
      "status": "APPROVED",
      "resumed_thread_id": "thread_8f8b340a_24ad"
    }
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
