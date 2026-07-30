# System Context & Domain Glossary
> 企业级 AI 数字员工平台项目核心概念与术语定义

---

## 1. 核心术语定义 (Glossary)

| 术语名称 | 全称 / 对应英文 | 定义与业务含义 |
| :--- | :--- | :--- |
| **AgentState** | Agent Graph State | LangGraph 中贯穿全图的有向共享状态字典，包含消息历史、意图、工具列表与审批标识。 |
| **HITL** | Human-in-the-loop | 人机协同机制。高风险 Tool 执行前抛出 `interrupt()` 挂起状态机，等待人工审批通过后 `resume()`。 |
| **Checkpointer** | LangGraph State Checkpointer | 持久化快照机制。将带有 `thread_id` 的 Graph 状态存入 MySQL/PostgreSQL，便于中断与跨 HTTP 会话唤醒。 |
| **Hybrid Retrieval** | BM25 + Vector Search | 混合检索管道。组合稠密向量（BGE-M3）与稀疏关键词匹配（BM25），通过 RRF（互惠排名融合）归一化。 |
| **Reranker** | BGE-Reranker-Large | 交叉编码重排模型。对 RRF 混合候选集进行二次精细语义打分，筛选最高相关的 Top-K 上下文。 |
| **Prompt Cache** | vLLM Automatic Prefix Caching | 本地推理 KV 缓存复用技术。对多轮对话及知识库前缀避免重复 Prefill 计算，大幅提升吞吐、降低延迟。 |
| **Harness** | Agent Harness Engineering | 围绕 AI Agent 构建的规则、测试门禁、自动化文档更新与约束边界，支撑 AI 自主开发（Self-Developing）。 |

---

## 2. 系统边界与组件职责 (System Boundaries)

```text
[Web Client (Vue3)] <── WebSocket / REST ──> [FastAPI Gateway] <──> [LangGraph State Core]
                                                                        │
                                                    ┌───────────────────┼───────────────────┐
                                                    ▼                   ▼                   ▼
                                             [Qdrant Vector]      [MySQL Store]       [vLLM Inference]
```
