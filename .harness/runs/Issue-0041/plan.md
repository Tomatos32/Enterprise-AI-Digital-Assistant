# Issue-0041: 技术架构与研发实施方案 (plan.md)

> **Sprint**：Sprint R-04 (Session Persistence & Frontend Hardening)  
> **设计人**：PlannerAgent / DeveloperAgent  
> **时间**：2026-10-21T08:05:00Z  

---

## 1. 架构流转与交互拓扑

```text
                  ┌────────────────────────────────────────────────────────┐
                  │                 Vue3 前端工作台交互层                   │
                  └───────▲────────────────────────────────────────▲───────┘
                          │ 1. 切换会话 GET /sessions/{id}/messages │ 2. WS 提问发送当前 activeSessionId
                          │ (加载历史消息回显到 messages.value)      │ (新建对话重置 isStreaming=false)
                  ┌───────┴──────────────┐         ┌───────────────┴───────┐
                  │ 会话管理 REST API     │         │ WebSocket 双向流式路由 │
                  │ /api/v1/chat/sessions│         │ /api/v1/ws/chat/{cid} │
                  └───────┬──────────────┘         └───────────────┬───────┘
                          │                                        │
                          │                                        │ 3. LLM 故障检测与容灾降级
                          ▼                                        ▼
                  ┌───────────────┐                        ┌───────────────┐
                  │ 数据库持久化层 │                        │ ResilientChat │
                  │ MySQL / SQLite│                        │ 502 -> Fallback
                  └───────────────┘                        └───────────────┘
```

---

## 2. 实施计划与改造矩阵

### Task 1: 前端 `chatStore.js` 接入后端会话持久化 API
- 替换纯 `localStorage` 假数据，新增 `fetchSessions()` 接口拉取后端 `GET /api/v1/chat/sessions`。
- 新增 `loadSessionMessages(sessionId)`，调用 `GET /api/v1/chat/sessions/${sessionId}/messages`。
- 将从后端拉取的 `ChatMessageResponse` 列表映射为前端统一的 `MessageItem` 结构（包含 sender: 'user' | 'ai', sources, content, timestamp）。

### Task 2: 修复 `ChatContainer.vue` 切换会话与消息清空缺陷
- 在 `watch(() => chatStore.activeSessionId)` 中，不再简单 `messages.value = []`，而是异步调用 `loadSessionMessages` 将历史消息填充进当前会话视图。
- 新建对话操作时，触发后端 `POST /api/v1/chat/sessions` 创建真实会话，并强制复位 `useChatStream` 的内部状态（`isStreaming.value = false`）。

### Task 3: 改造 `useChatStream.js` 的会话透传与异常保护
- 改造 `sendMessage` 函数，接收当前的 `activeSessionId` 作为参数，不再硬编码随机 `s_vue3_${Date.now()}`。
- 在 `handleWsEvent` 中的 `error`、`cancelled`、`complete` 分支中，确保始终执行 `isStreaming.value = false`。
- 提供 `resetStreamingState()` 方法供外部在新建会话或强制打断时直接调用，防止输入框死锁。

### Task 4: 后端 LLM 502 错误日志提示友好化
- 当捕获到 502（连接拒绝）时，在系统提示中友好告知用户“Ollama 本地服务未运行，已为您自动切换到内置离线规则模型。如需真实 Qwen 大模型推理，请运行 start_ai_service.bat”。
