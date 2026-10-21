# Issue-0041: 前端多会话真实历史加载、会话状态脱节与大模型 502 阻断自愈 (issue.md)

> **Sprint**：Sprint R-04 (Session Persistence & Frontend Hardening)  
> **负责人**：Bootstrap Orchestrator / DeveloperAgent  
> **时间**：2026-10-21T08:00:00Z  
> **关联痛点**：用户实测反馈“新建对话后无法发出提问，原有其他对话历史提问也消失，怀疑为数据库问题”，伴随日志 `Failed to obtain server version`、`Failed to initialize FastEmbed` 与 `Primary ChatModel _astream failed: Error code: 502`。

---

## 1. 现象还原与核心排查结论

经过全链路代码与运行态审查，**排查结论如下：本故障绝非数据库损坏或数据库故障，核心根因在于「前端状态管理与会话数据未对接」以及「Ollama 未启动导致 502 触发前端流式状态挂起」**。

### 1.1 核心根因分析 (Root Causes)

1. **会话历史加载缺失（“旧对话历史消失”的真正原因）**：
   - 在 `frontend/src/components/ChatContainer.vue` 中存在以下监听代码：
     ```javascript
     watch(() => chatStore.activeSessionId, (newId) => {
       if (newId) {
         currentThreadId.value = newId;
         messages.value = []; // 直接暴力清空消息数组
       }
     });
     ```
   - 切换或新建会话时，前端直接清空了当前消息列表 `messages.value = []`，**从未调用后端已就绪的 REST API (`GET /api/v1/chat/sessions/{session_id}/messages`) 进行历史记录回放**。
   - 前端 `chatStore.js` 内部数据完全存储在本地 `localStorage`，与后端已落库的 SQLite / MySQL 处于割裂状态。

2. **新建对话无法发出提问的阻断点（输入框被死锁）**：
   - `frontend/src/components/chat/ChatInput.vue` 中有保护判断：
     ```javascript
     const handleSend = (payload) => {
       if (props.disabled || props.isStreaming) return;
       emit('send', payload);
     };
     ```
   - 当大模型服务不可用（例如 Ollama 未运行返回 502）时，WebSocket 的异常处理分支若未妥善触发 `complete` 或前端 `isStreaming.value` 未被重置为 `false`，界面就会一直停留在“思考中/流式中”。
   - 此时用户即便点击“新建对话”，由于全局 `isStreaming` 仍为 `true`，点击发送会被直接拦截，表现为无法输入/无法发出提问。
   - 此外，`useChatStream.js` 在发送时硬编码了 `session_id: "s_vue3_" + Date.now()`，没有与 `chatStore.activeSessionId` 绑定，每次提问都在数据库生成一个孤立的新会话。

3. **后端日志警告解读**：
   - `UserWarning: Failed to obtain server version`: Qdrant 远程服务未运行，已自愈降级到本地持久化磁盘存储，属于良性警告。
   - `Failed to initialize FastEmbed model`: 本地环境未装包，已自愈降级到内置零依赖 `LocalSemanticEmbeddingEngine`，属于良性警告。
   - `Primary ChatModel _astream failed: Error code: 502`: 配置了本地 Ollama（`http://localhost:11434/v1`），但当时**本地尚未执行 `start_ai_service.bat` 拉起 Ollama 进程**，导致请求返回 502 Connection Refused。虽然系统自动降级到了 `LocalEnterpriseChatModel`，但前端状态未能平滑复位。

---

## 2. 交付与验收目标 (Definition of Done)

1. **前端会话与数据库全链路对接** (`frontend/src/stores/chatStore.js` & `ChatContainer.vue`)：
   - 启动时自动从后端 `GET /api/v1/chat/sessions` 同步持久化会话列表。
   - 切换会话时，自动调用 `GET /api/v1/chat/sessions/{id}/messages` 加载真实历史消息并规范反序列化为渲染对象。
   - 修复切换会话导致历史提问消息清空消失的体验断层。
2. **状态解绑与输入锁自愈** (`frontend/src/composables/useChatStream.js` & `ChatInput.vue`)：
   - 新建对话与会话切换时，强制重置 `isStreaming = false` 与活动节点状态，彻底解除发送输入锁。
   - `sendMessage` 改用真实的当前活跃会话 ID（`chatStore.activeSessionId`），确保前后端 Session 一致性。
3. **大模型网关 502 容错增强** (`backend/core/llm.py` & `backend/api/v1/chat_ws.py`)：
   - 优化 502 错误捕获，确保即便主大模型不可达，降级后的备用回答流能完整发送 `complete` 帧并正确落地。
   - 前端 WebSocket 捕获异常后强制将 `isStreaming` 置为 `false`，给出明确的“本地大模型底座未启动提示（可运行 start_ai_service.bat 拉起）”。
4. **验证与回归**：
   - 验证新建会话 -> 提问 -> 切换会话 -> 历史消息回显 -> 再次提问的全闭环流程。
