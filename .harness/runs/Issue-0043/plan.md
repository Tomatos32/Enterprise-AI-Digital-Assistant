# Issue-0043: 架构方案与实施设计 (plan.md)

> **Sprint**：Sprint R-04  
> **设计人**：PlannerAgent / Architect  
> **时间**：2026-10-22T01:05:00Z  

---

## 1. 架构拓扑设计

```text
       [FastAPI 业务节点 (generate_node)]
                      │
                      ▼
               get_chat_llm()
                      │
                      ▼
             ResilientChatModel
                      │
                      ▼
            ChatOpenAI 客户端
         ┌────────────┴────────────┐
         │ 显式注入 trust_env=False │
         │   (绕过 7897 代理端口)   │
         └────────────┬────────────┘
                      │
                      ▼ (直连 127.0.0.1:11434)
              Ollama 算力引擎
           (模型: qwen3.5:2b / 8b)
```

---

## 2. 实施任务分解

1. **Task 1: 客户端隔离与直连通信**：
   - 在 `backend/core/llm.py` 中引入 `httpx`，对 `127.0.0.1` 实例化独立的 `custom_async_client` 与 `custom_sync_client`，禁用环境代理继承。
2. **Task 2: 调用链方法重塑**：
   - 修复 `_agenerate` 兼容性，确保 `ainvoke` 与 `astream` 在真实流式场景下均能稳定获取 `AIMessage` 与 Token。
3. **Task 3: 连通性真实验证**：
   - 编写探针脚本直连 Ollama `qwen3.5:2b`，验证问答与流式生成。
