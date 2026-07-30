# ADR-0001: 采用 LangGraph 作为 Agent 有向图状态机编排引擎

- **Status**: Accepted
- **Date**: 2026-07-21
- **Deciders**: AI System Architect

## Context (背景)
企业数字员工平台需要支持复杂 SOP 长流程拆解、多路工具并发调用以及针对采购等高风险任务的“人机协同审批 (Human-in-the-loop)”。传统的无状态 Agent（如原生 LangChain `AgentExecutor`）存在无法中断与恢复、状态可控性差、长对话记忆易爆等痛点。

## Decision (最终决策)
决定采用 **LangGraph** 作为核心智能体编排引擎。主要设计点包括：
1. 声明显式强类型的全局状态 `AgentState`。
2. 使用 `PostgresCheckpointer` 实现持久化状态快照。
3. 利用 LangGraph 原生的 `interrupt()` 与 `update_state()` 实现无缝人机协同挂起与恢复。

## Consequences (影响与权衡)
- **正面**:
  - 解决了跨 HTTP / WebSocket 连接的长会话状态中断与恢复难题。
  - 节点的执行路径透明可追踪，便于进行故障回溯与质量评估。
- **负面/成本**:
  - 相比无状态逻辑增加了 Postgres/MySQL 状态存盘的额外开销。
  - 需要在代码规范中严密约束状态机的转换条件。
