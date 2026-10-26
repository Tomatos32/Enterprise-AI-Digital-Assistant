# Issue-0045: 架构与技术实施方案 (plan.md)

> **Sprint**：Sprint R-04  
> **设计人**：PlannerAgent / DeveloperAgent  
> **时间**：2026-10-26T08:35:00Z  

---

## 1. 架构流转设计

```text
[WebSocket Client / Vue3] 
       │ (用户发问 "hi" 或中途中断/重连)
       ▼
[chat_ws.py]
       │
       ├─► safe_send_json()  ──► 检查 websocket.client_state == CONNECTED
       │                         若已 close 则优雅终止，彻底杜绝 RuntimeError
       │
       ▼ LangGraph
[generate_node.py (chat intent)]
       │
       ▼ System Prompt 自然化
[自然亲切的数字员工人设，面对日常问候以纯正自然中文轻松回应，消除机械背诵]
       │
       ▼
[Qwen3.5:2b 真实流式输出自然回答]
```

---

## 2. 实施矩阵

1. **Task 1: 安全发送器与异常治理 (`chat_ws.py`)**：
   - 提取全局辅助函数 `safe_send_json(websocket, payload)`；
   - 替换所有 `await websocket.send_text(...)`；
   - 即使客户端中途关闭连接，流式循环与退出逻辑均平滑收尾，不再抛出异常。
2. **Task 2: 会话消息查询 404 自愈 (`chat.py`)**：
   - 在 `get_session_messages` 中，当 `session_id` 未查找到时，自动创建记录或返回空列表，避免控制台 404 告警。
3. **Task 3: 提示词人设解绑 (`generate_node.py`)**：
   - 调整对话分支的 System Prompt，移除机械业务清单强求。
