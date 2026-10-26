# Issue-0045: WebSocket 断开安全防御、会话 404 容错自愈与人设去客服套话 (issue.md)

> **Sprint**：Sprint R-04 (WebSocket Lifecycle Resilience & Conversational Persona)  
> **负责人**：Bootstrap Orchestrator / DeveloperAgent  
> **时间**：2026-10-26T08:30:00Z  
> **关联痛点**：用户输入“hi”时后端抛出 `RuntimeError: Unexpected ASGI message 'websocket.send', after sending 'websocket.close'` 双重异常；历史会话报 404；且即使连通了 Ollama，打招呼时模型总是固定背诵“查制度、走流程、协同办公”等客服清单，体验死板像兜底。

---

## 1. 现象复盘与核心根因分析 (Root Causes)

1. **WebSocket 断连并发发送致命异常 (RuntimeError)**：
   - 当客户端触发中断 (`POST /api/v1/chat/abort`)、刷新页面或网络瞬断时，底层连接已进入 `websocket.close` 状态。
   - `backend/api/v1/chat_ws.py` 中所有的 `websocket.send_text(...)` 均为裸调用，未校验 `websocket.client_state == WebSocketState.CONNECTED`。
   - 向已关闭的 WebSocket 发送帧直接触发 Uvicorn 协议保护异常；更严重的是，外层 `except Exception as e:` 捕获后，**又再次尝试调用 `websocket.send_text` 发送错误消息**，导致发生二次异常并被强制捕获打印为重大错误。
2. **浏览器旧会话请求后端抛出 404**：
   - 浏览器本地存储 `localStorage` 中留存有历史测试的旧会话 ID（形如 `session_1792989955052_mlyg`）。
   - 用户切换会话时，前端向后端请求 `GET /api/v1/chat/sessions/{session_id}/messages`，后端在数据库未查到该历史 ID 直接抛出 404。
   - 需实现后端容错自愈（若不存在自动创建或返回空列表）与前端坏死会话清理。
3. **对话人设 Prompt 过度约束（打招呼变成背客服话术）**：
   - 在 `backend/graph/nodes/generate_node.py` 的普通对话分支中，原有 System Prompt 指令：
     `“简明介绍你能协助用户处理的业务范围（解读规章制度、审批门禁指引、工单流转与协同处理等）。”`
   - 这一指令导致 Qwen 模型在面对用户日常问候“hi”、“你好”时，每次都机械地背诵一遍企业功能清单，导致用户误以为大模型没有连上、系统触发了本地死板的兜底模板。

---

## 2. 交付与验收目标 (Definition of Done)

1. **WebSocket 安全发送封装 (`safe_send_json`)** (`backend/api/v1/chat_ws.py`)：
   - 封装 `safe_send_json` 方法，发送前检查连接状态，并在异常时静默丢弃，杜绝 `Unexpected ASGI message after close` 崩溃。
2. **后端会话 API 容错降级** (`backend/api/v1/chat.py`)：
   - 当请求的 `session_id` 在数据库中不存在时，不再直接 404 报错中断，而是优雅返回空数组 `[]` 并自动补全会话记录，确保前端历史会话平滑切换无报错。
3. **System Prompt 人设自然化改造** (`backend/graph/nodes/generate_node.py`)：
   - 针对普通对话（`intent == "chat"`），允许大模型自然、灵动、亲切地与用户打招呼交流，去除机械强加的“每次必须背诵三项业务范围”的硬性说辞。
4. **自动化测试与全量回归**：
   - 验证单测 100% 通过，终端 0 堆栈报错，问答自然流畅。
