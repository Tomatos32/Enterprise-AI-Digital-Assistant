# Active Sprint Execution Plan (Pragmatic Realization & Reality Hardening Mode)
> Enterprise AI Digital Assistant - Active Task Checkpoint Board

---

## Active Status: PRAGMATIC REALIZATION & HARDENING MODE (务实真实化重构与交付攻坚模式)

### Mode Objective (模式目标与方向纠偏)
面向个人独立开发者真实可运行、可交付、可 Demo 体验视角，卸除不可及的企业专属假设（飞书/SAP/泛微降级为标准模拟桩），系统性补齐会话持久化、真实向量化 Embedding、端到端 RAG 自校验与流式大模型生成、开源工作流（Dify/N8N）真实打通。

### Active & Upcoming Pragmatic Hardening Sprints (真实化攻坚战役计划):
- [x] **Sprint R-01: 数据库与会话持久化真身落地 (Chat & Session Persistence) - [100% COMPLETED]**
  - [x] Checkpoint 1: 新建 `ChatSession` 与 `ChatMessage` SQLAlchemy ORM 模型（包含 session_id、role、content、sources、时间戳）
  - [x] Checkpoint 2: 编写会话管理 REST API（会话列表、历史记录加载、删除会话、修改标题）
  - [x] Checkpoint 3: 改造 WebSocket 流程，对话提问与回答真实写库
  - [x] Checkpoint 4: 编写全量单元测试与管道测试 `test_chat_persistence.py` (5/5 PASS, 241/241 PASS)

- [x] **Sprint R-02: 真实向量库底座与知识库离线构建全可观测 (Real Vector & Ingestion) - [100% COMPLETED]**
  - [x] Checkpoint 1: 替换伪哈希向量，构建多后端统一嵌入引擎（`FastEmbedEngine`、`OpenAIEmbeddingEngine` 与零依赖 `LocalSemanticEngine`，消灭 sha256 伪向量）
  - [x] Checkpoint 2: 编写一键离线切片入库脚本 `backend/scripts/ingest_knowledge.py`，支持递归扫描解析、切片、Embedding 入库与自检探针
  - [x] Checkpoint 3: 提供 `GET /api/v1/knowledge/status` 与 `POST /api/v1/knowledge/sync` 实时监控探针（返回集合点数、向量维度、入库文档清单）
  - [x] Checkpoint 4: 固化 Qdrant 物理持久化目录与连接自愈重试机制
  - [x] Checkpoint 5: 重构 Reranker 覆盖度打分算法，完成全仓 247 项自动化测试全通 (6/6 PASS, 247/247 PASS)

- [x] **Sprint R-03: 端到端真实 RAG 闭环与大模型流式生成 (Real RAG Pipeline & LLM) - [100% COMPLETED]**
  - [x] Checkpoint 1: 封装通用 OpenAI 兼容大模型客户端（`get_chat_llm`），支持一键配置 DeepSeek、通义千问、OpenAI 或本地 vLLM / Ollama，并配备 `ResilientChatModel` 自动自愈降级
  - [x] Checkpoint 2: 重构 `generate_node.py`，注入 System Prompt、多轮历史对话与结构化 Context，调用真实 ChatModel 生成真实规范回答
  - [x] Checkpoint 3: 打通 WebSocket 真正的逐字 Token 流式推送（`on_chat_model_stream`）与实时打字机动效（实测 99 个 token 逐字捕获）
  - [x] Checkpoint 4: 引入检索相关性阈值过滤与无相关内容时的优雅自校验反思（Self-Correction），附带精确来源溯源
  - [x] Checkpoint 5: 编写完整测试套件 `test_rag_pipeline_and_streaming.py`，全仓 253 项测试 100% 通过 (6/6 PASS, 253/253 PASS)

- [ ] **Sprint R-04: 个人可及的开源工作流平台集成与个人运行指南 (Workflows & Runbook)**
  - [ ] Checkpoint 1: 真实对接个人部署的 N8N Webhook（大额审批与工单创建事件真实推送）
  - [ ] Checkpoint 2: 真实对接 Dify Workflow API（支持复杂子任务委托执行）
  - [ ] Checkpoint 3: 固化 HR / ERP / OA 本地开箱即用模拟桩，确保无外部网络与商业账号下系统自闭环运行
  - [ ] Checkpoint 4: 编写个人高保真部署与运行指南 `docs/PERSONAL_RUNBOOK.md`

---

## Historical Achievements (已交付稳态资产):
- [x] 前端现代化终端体验重塑 (Sprint F-01 ~ F-08 全部闭环，Vue3 + Tailwind + 响应式布局 + 人机协同审批卡片 100% 就绪)
- [x] LangGraph 状态机拓扑与意图路由核心框架 (StateGraph 骨架、条件边、工具注册器)
- [x] 基础设施与代码质量体系 (Ruff 0 错误 / 0 警告，自动化测试套件基线)
- [x] 多模态文档解析器骨架 (双栏重构、跨页表格合并与 Excel 表头解析基线)
