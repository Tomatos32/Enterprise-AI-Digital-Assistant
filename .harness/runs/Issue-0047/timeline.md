# Issue-0047: 执行时序流转记 (timeline.md)

| 阶段 | 动作 | 执行主体 | 时间戳 | 产出物 |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1: Issue Ingestion** | 针对单次提问多次回复、心跳被当作提问无限流式与 abort 后冒出新回复建立 Issue-0047 | Bootstrap Orchestrator | 2026-10-27T01:00:00Z | `issue.md` |
| **Stage 2: Root Cause Analysis** | 定位确认心跳 Ping 漏判分流、主协程未独立任务化与输入防重缺乏等三大根因 | Architect / Developer | 2026-10-27T01:05:00Z | `plan.md` |
| **Stage 3: Dev - Backend Task Isolation**| 重构 `chat_ws.py`，拦截 ping 包并以 `create_task` 隔离问答，实现精准 abort | DeveloperAgent | 2026-10-27T01:15:00Z | `chat_ws.py` |
| **Stage 4: Dev - Frontend Debounce** | 在 `useChatStream.js` 与 `PromptBar.vue` 落实单例连接与发送防抖 | DeveloperAgent | 2026-10-27T01:25:00Z | `PromptBar.vue`, `useChatStream.js` |
