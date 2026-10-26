# Issue-0046: 实施方案与重构拓扑 (plan.md)

> **Sprint**：Sprint R-04 / Sprint F-09 Sub-branch  
> **设计人**：PlannerAgent / Architect  
> **时间**：2026-10-26T09:05:00Z  

---

## 1. 架构拓扑

```text
[Ollama qwen3.5:2b 推理引擎]
             │
             ├─► SSE delta.reasoning ──► chat_ws.py 发送 {"type": "thought", "content": ...}
             │                                   │
             │                                   ▼
             │                        useChatStream.js 累加 currentMsg.thought
             │                                   │
             │                                   ▼
             │                   ThoughtBadge.vue -> ThoughtLine.vue (Vue Bits 原版动效展示)
             │
             └─► SSE delta.content  ──► chat_ws.py 发送 {"type": "token", "content": ...}
                                                 │ (首个 token 到达，ThoughtLine 停止打表并记录真实秒数)
                                                 ▼
                                        complete 帧到达 ──► 强制 isStreaming = false
                                                             (发送按钮秒变发送箭头)
```

---

## 2. 实施矩阵

1. **Task 1: Vue Bits 官方规范组件引入与汉化微调** (`ThoughtLine.vue`)：
   - 依赖装配 `@hugeicons/core-free-icons` 与 `motion-v`；
   - 增加 `preview` 插槽与 Prop 渲染真实思考长文本。
2. **Task 2: ThoughtBadge 数据源真身割接** (`ThoughtBadge.vue`)：
   - 清理所有伪数据，Props 驱动；
   - 动态计算 `actualDuration`。
3. **Task 3: WebSocket 终态强制守卫** (`useChatStream.js`)：
   - 重构 `handleWsEvent`，消除状态闭锁。
4. **Task 4: 后端思考流透传适配** (`chat_ws.py`)：
   - 提取 `reasoning_content`，新增 `thought` 事件。
