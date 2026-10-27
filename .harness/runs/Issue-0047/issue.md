# Issue-0047: WebSocket 心跳提问混淆治理、协程独立任务化隔离与输入防重抖动抑制 (issue.md)

> **Sprint**：Sprint R-04 (WebSocket Task Isolation & Anti-Duplicate Stream)  
> **负责人**：Bootstrap Orchestrator / DeveloperAgent  
> **时间**：2026-10-27T01:00:00Z  
> **关联原始任务**：`Issue-0045`（WebSocket 状态防御）与 `Issue-0046`（流式状态机复位）  
> **关联痛点**：
> 1. 用户输入一次提问后，收到多次重复回复，且系统像是时刻在进行流式传输重复向模型发问；
> 2. 手动点击停止按钮，虽然后端 `/abort` 返回 200，但过一段时间后端又冒出新的回复；
> 3. 前端与后端的连接、心跳与会话生成协程存在严重的耦合和重入竞争。

---

## 1. 现象复盘与核心根因分析 (Root Causes)

1. **心跳 Ping 包被后端当作提问消息消费（最严重的死循环源头）**：
   - 前端 `useChatStream.js` 每 30 秒发送一个保活心跳：`ws.send(JSON.stringify({ type: 'ping', timestamp: ... }))`；
   - 后端 `websocket_chat_endpoint` 的 `while True:` 循环中，**完全没有对 `data.get("type") == "ping"` 进行判定分流**，直接将其透传进 `process_ws_chat_stream`！
   - 空 `message` 被 LangGraph 作为输入调用大模型生成，导致系统“时刻在进行流式传输重复向模型提问”，心跳包成了幽灵提问源头！
2. **WebSocket 主接收协程与流式工作协程未隔离（导致 Abort 失效与残留生成）**：
   - 后端将 `process_ws_chat_stream` 直接同步 `await` 在 `websocket_chat_endpoint` 主接收循环中，并且把主接收 Task 注册到了 `task_manager`；
   - 当用户点击暂停调用 `/abort` 时，cancel 的是整个主连接协程而不是具体的模型生成任务，导致大模型后台生成无法立即终止；且主连接断开后前端 3 秒内自动重连，引发多轮重复回复。
3. **前端 WebSocket 多实例并发与回车重入无防抖**：
   - 前端 `connect()` 函数在重连时未检查已有连接状态，连接闪断时可能产生多个活跃的 WebSocket 实例同时往界面推送重复 token；
   - `PromptBar.vue` 缺乏 `e.isComposing` 中文输入法防护与防抖锁，导致一次输入可能触发多次事件发射。

---

## 2. 交付与验收目标 (Definition of Done)

1. **心跳与空消息严格分流** (`backend/api/v1/chat_ws.py`)：
   - 收到 `type: "ping"` 时，直接响应 `{"type": "pong"}` 并立刻 `continue`，绝不触发模型调用；
   - 收到空 `message` 时直接跳过，杜绝任何幽灵生成。
2. **流式任务独立协程化与精准 Abort** (`backend/api/v1/chat_ws.py`)：
   - 每次提问派发独立的 `asyncio.create_task`，主 WebSocket 循环保持监听；
   - `task_manager` 严格绑定并取消该生成 Task，中止时瞬间切断大模型流，且主连接绝不断线。
3. **前端单例连接与防抖保护** (`useChatStream.js` & `PromptBar.vue`)：
   - 增加连接状态锁，杜绝多实例重复连接；
   - 输入框增加 300ms 发送锁与 `e.isComposing` 选词保护，彻底消灭重复发送与多次回复。
4. **验证与回归**：
   - 验证单次提问仅产生唯一回复；验证点击暂停后毫秒级停机，绝不再冒出任何后续回复。
