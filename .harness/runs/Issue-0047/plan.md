# Issue-0047: 技术架构与隔离实施方案 (plan.md)

> **Sprint**：Sprint R-04  
> **设计人**：PlannerAgent / Architect  
> **时间**：2026-10-27T01:05:00Z  

---

## 1. 架构拓扑与协程隔离设计

```text
[WebSocket 客户端]
        │
        ▼
websocket_chat_endpoint (主常驻监听协程，绝不被 cancel，连接永不断)
        │
        ├─► type == "ping" ──► 瞬间返回 pong 立即 continue (不调模型)
        │
        ├─► message 为空   ──► 瞬间忽略 continue (不调模型)
        │
        └─► 有效提问 message
                │
                ▼
        [创建独立 worker_task] ──► asyncio.create_task(process_ws_chat_stream(...))
                │
                ├─► 注册到 task_manager.register_task(thread_id, worker_task)
                │
                ├─► 用户若点击中止 ──► /abort 精准取消 worker_task (瞬间刹车)
                │
                └─► 生成完成后 ──► 自动 unregister_task，主 WebSocket 平稳待机
```

---

## 2. 实施矩阵

1. **后端心跳阻断与任务隔离 (`chat_ws.py`)**：
   - 增加 `if data.get("type") == "ping":` 立即处理分支；
   - 提取 `worker_task`，主接收循环不被任何单个问答阻塞。
2. **前端连接单例与状态流转防抖 (`useChatStream.js`)**：
   - `connect()` 增加 `isConnecting` 与 `ws.readyState` 校验；
   - `sendMessage` 增加 `if (isStreaming.value) return;` 严格防重入。
3. **输入组件输入法与键盘防抖 (`PromptBar.vue`)**：
   - 增加 `if (e.isComposing) return;`；
   - 增加 `isSending` 防抖锁。
