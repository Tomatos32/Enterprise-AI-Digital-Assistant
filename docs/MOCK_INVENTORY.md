# 全局资产清单审计、真实化割接与个人可及落地规范
# Global Asset Inventory & Feasible Realization Specification

> **文档性质**：面向用户视角的真实化落地、可及性边界与 Mock 割接规范  
> **版本定义**：V2.0 (面向个人高保真可运行与交付视角全面纠偏)  
> **最后维护**：2026-09-23  

---

## 1. 现实边界与设计哲学纠偏 (Pragmatic Philosophy)

在前期开发阶段，项目规划了大量大型企业专有系统（如飞书人事、SAP ERP、泛微 OA、企业微信 Bot 等），并在核心链路（对话持久化、向量化 Embedding、LLM 生成）上大量采用了内存 Mock 与伪算法。

面向个人独立开发者与实际演示交付视角，必须明确**可及性边界 (Feasibility Boundaries)**：
1. **不可及/非核心企业系统（退居模拟桩）**：
   - 飞书开放平台、SAP ERP、泛微 e-cology、企业微信企业内审批网关等，由于个人开发者无企业组织认证、无内网专线、无百万级商业授权，**强制接入既不现实也无必要**。这部分保留清晰的**标准化 OpenAPI 协议模拟桩（Mock Stub）**即可，不再作为核心攻坚重点。
2. **个人完全能及且必须真实化的核心资产（主攻真实闭环）**：
   - **大模型推理引擎**：统一 OpenAI 兼容格式接口，真实支持商用模型（DeepSeek、通义千问 Qwen、OpenAI 等）以及本地自建推理引擎（vLLM、Ollama）。
   - **开源自建工作流平台**：全面真实打通个人可在本地或云端一键拉起的 **Dify**（Workflow/Agent API）与 **N8N**（Webhook 编排与事件处理）。
   - **真实向量数据库与知识库**：摒弃哈希正弦波伪向量，接入真实的轻量级 Embedding 模型（fastembed / BGE-M3 / OpenAI 兼容 Embedding），提供物理持久化的 Qdrant 存储、离线切片入库脚本与可视化健康探针。
   - **端到端 RAG 真实闭环**：用户输入 -> 意图与 Query 解析 -> 密集+稀疏检索 -> 真实重排 -> 检索相关性自校验 -> 真实 LLM 流式生成与溯源。
   - **数据库会话与工单持久化**：补充 `chat_sessions`、`chat_messages` 实体表，用真实数据库持久化替代易失的内存 `MemorySaver`。

---

## 2. 全景资产状态与割接规划矩阵 (Master Realization Matrix)

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              面向个人可运行交付的 5 大维度资产真实化分级图                               │
├──────────────────┬──────────────────┬──────────────────┬──────────────────┬────────────────────────────┤
│ 1. 核心大模型与生成 │ 2. 知识库与向量库  │ 3. 数据库与会话  │ 4. 开源工作流平台 │ 5. 企业业务系统 (模拟桩)   │
│    (LLM / vLLM)  │    (Vector & RAG)│    (MySQL/SQLite)│    (Dify / N8N)  │    (HR / ERP / OA)         │
├──────────────────┼──────────────────┼──────────────────┼──────────────────┼────────────────────────────┤
│ 🔴 现状: 假字符串 │ 🔴 现状: 伪哈希  │ 🔴 现状: 缺表    │ 🟡 现状: 内存队列 │ 🟢 定位: 标准化轻量模拟桩  │
│ 🎯 目标: 真实API/│ 🎯 目标: 真实Embed│ 🎯 目标: Session/│ 🎯 目标: 真实API/ │ 🎯 目标: 保持标准 REST API │
│    vLLM 流式生成  │    一键构建与探针│    Message持久化 │    Webhook 双向流│    个人无需购买真实企业软件 │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┴────────────────────────────┘
```

| 序号 | 资产模块 | 当前现状排查 (Current State) | 纠偏后的真实化方案 (Realization Plan) | 可行性等级与配置项 |
| :---: | :--- | :--- | :--- | :--- |
| **01** | **LLM 网关与降级 (大模型生成引擎)** | `generate_node.py` 截取检索内容前 150 字符硬编码拼装文本；`llm_gateway.py` 为休眠模拟 | 接入通用 OpenAI 兼容客户端（`AsyncOpenAI` / LangChain），支持真实 API（DeepSeek / Qwen / OpenAI）与本地自建 **vLLM / Ollama** | **P0 (必须真实化)**<br/>`LLM_PROVIDER=openai/deepseek/vllm`<br/>`OPENAI_API_BASE=...`<br/>`OPENAI_API_KEY=...`<br/>`LLM_MODEL=...` |
| **02** | **冷启动知识库文档 (Embedding 与向量底座)** | `vector_store.py` 使用 `hashlib.sha256 + sin` 计算伪向量；连不上远程则降级为内存易失库 | 引入真实的轻量级 Embedding 引擎（默认支持 `fastembed` 本地免配置运行 / BGE-M3 / OpenAI Embedding API）；提供 Qdrant 物理持久化目录与健康探测 | **P0 (必须真实化)**<br/>`EMBEDDING_PROVIDER=fastembed/bge/openai`<br/>`QDRANT_HOST=localhost`<br/>`QDRANT_PORT=6333` |
| **03** | **端到端 RAG 闭环与自校验** | 无语义 Rerank，无相关性校验，无幻觉反思，直接输出拼接假文本 | 实现真实 Top-K 检索 -> 真实重排得分计算 -> 检索相关性阈值过滤与自校验（低相关性时反思并引导提问） -> LLM 结合上下文生成并附带标注引用 | **P0 (必须真实化)**<br/>`RAG_RERANK_ENABLED=True`<br/>`RAG_SCORE_THRESHOLD=0.3` |
| **04** | **对话会话与历史消息存储 (E2E 演示数据库与持久化)** | 缺失 `chat_sessions` 和 `chat_messages` 表；LangGraph 仅使用内存 `MemorySaver` | 新建 SQLAlchemy ORM 模型，支持多会话隔离、历史消息分页查询与前端回显；替换 Checkpointer 为数据库持久化存储 | **P0 (必须真实化)**<br/>`DB_PERSIST_CHAT=True`<br/>`SQLALCHEMY_DATABASE_URI=...` |
| **05** | **知识库批量构建与探针** | 每次检索时临时读本地文件临时 upsert；开发者无法得知库内现状 | 编写一键离线切片入库脚本 `scripts/ingest_knowledge.py`；新增 `GET /api/v1/knowledge/status` 实时查看集合点数、向量维度与分段详情 | **P1 (必须真实化)**<br/>支持一键构建与控制台可视化查询 |
| **06** | **n8n / Dify 事件联动 (开源工作流平台接入)** | `workflow.py` 内部使用 `EVENT_HISTORY` 内存列表 | 真实对接个人部署的 **Dify**（通过 REST API 触发 Agent/Chatflow）与 **N8N**（通过 Webhook 接收审批事件并执行后续自动化） | **P1 (个人完全可及)**<br/>`DIFY_API_BASE=http://localhost:8001/v1`<br/>`DIFY_API_KEY=...`<br/>`N8N_WEBHOOK_URL=http://localhost:5678/webhook/...` |
| **07** | **工单流转与人机协同审批** | ORM 表已有，但缺乏统一查询接口与前端会话上下文强绑定 | 完善工单与审批列表 REST API，支持根据会话 ID 联动查看、通过/驳回审批，与真实会话流互通 | **P1 (必须真实化)**<br/>`POST /api/v1/approval/action` 真实写库并唤醒状态机 |
| **08** | **HR 员工信息查询** | `backend/api/v1/mock/hr_mock.py` 查本地 MySQL `users` 表 | **保留本地标准化模拟桩**（个人无需购买飞书/北森账号，本地数据库即可完美支撑员工信息查询与演示） | **P3 (维持优质模拟桩)**<br/>`USE_MOCK_SYSTEMS=True` |
| **09** | **ERP 物料库存查询** | `backend/api/v1/mock/erp_mock.py` 读取本地 `inventories` 表 | **保留本地标准化模拟桩**（个人无需对接 SAP/用友/金蝶，本地模拟桩具备完整的物料查询能力） | **P3 (维持优质模拟桩)**<br/>`USE_MOCK_SYSTEMS=True` |
| **10** | **ERP 采购订单创建** | `backend/api/v1/mock/erp_mock.py` 向本地 `purchases` 表插入记录 | **保留本地标准化模拟桩**（本地模拟桩具备完整的单据生成与采购流程流转） | **P3 (维持优质模拟桩)**<br/>`USE_MOCK_SYSTEMS=True` |
| **11** | **OA 故障工单流转** | `backend/api/v1/mock/oa_mock.py` 读写本地 `tickets` 表 | **保留本地标准化模拟桩**（个人无需对接 Jira/泛微，本地模拟桩具备完整的 SLA 与状态流转逻辑） | **P3 (维持优质模拟桩)**<br/>`USE_MOCK_SYSTEMS=True` |
| **12** | **企业微信 Bot 通知** | `workflow.py` 内存收集卡片消息 | **双模支持**：未配 Webhook 时在管理界面回显卡片数据；配置真实 Webhook 时一键向真实群发送 Markdown 卡片 | **P2 (可选配置)**<br/>`WECOM_WEBHOOK_URL=...` |

---

## 3. 核心真实化改造技术方案详述

### 3.1 改造一：统一 LLM 调用层与 vLLM/Ollama 适配
- **痛点**：目前 `generate_node` 仅仅是字符串截取拼接，没有流式输出，更没有大模型推理。
- **真实化方案**：
  1. 在 `backend/core/llm.py` 中封装统一的 `get_chat_llm()` 工厂函数，返回标准 LangChain `BaseChatModel` 或 `AsyncOpenAI` 实例。
  2. 支持标准环境变量切换：
     ```bash
     # 方案 A: 商业大模型 (以 DeepSeek / 通义千问 / OpenAI 为例)
     OPENAI_API_BASE=https://api.deepseek.com/v1
     OPENAI_API_KEY=sk-your-deepseek-key
     LLM_MODEL=deepseek-chat
     
     # 方案 B: 本地推理引擎 (vLLM 或 Ollama)
     OPENAI_API_BASE=http://localhost:8000/v1
     OPENAI_API_KEY=EMPTY
     LLM_MODEL=qwen2.5-7b-instruct
     ```
  3. 重构 `generate_node`，利用 Prompt 模板注入 System Prompt、历史对话与检索到的 Context，调用真实模型完成生成并流式输出。

### 3.2 改造二：真实 Embedding 与 Qdrant 离线切片管理
- **痛点**：当前使用 sha256 + sin 生成无意义伪向量，无法进行任何语义召回；且每次运行实时遍历文件，Qdrant 状态黑盒不可见。
- **真实化方案**：
  1. 引入免网络、轻量级的本地向量计算（如 `fastembed`，内置 `bge-small-zh-v1.5`，CPU 秒级加载），或配置远程 Embedding API。
  2. 编写 `backend/scripts/ingest_knowledge.py` 命令行工具：
     ```bash
     python -m backend.scripts.ingest_knowledge --kb-dir docs/sample_kb --recreate
     ```
     输出明确的控制台日志：文档解析数、生成切片数、写入 Qdrant 点位数量、耗时，并执行一道语义自检测试题。
  3. 提供 `GET /api/v1/knowledge/status` 接口，返回：
     - Qdrant 运行模式（物理服务 / 本地嵌入）；
     - 当前集合名称与点数（Points Count）；
     - 向量维度与距离度量（1024/512, Cosine）；
     - 已索引知识库文档列表与切片概览。

### 3.3 改造三：端到端 RAG 闭环与自校验
- **痛点**：检索结果无论相关与否均直接拼装，缺乏相关性过滤与自校验，存在严重幻觉隐患。
- **真实化方案**：
  1. **双路召回**：BM25 关键词匹配 + 真实密集向量检索。
  2. **相关性过滤与 Rerank**：对候选文档计算相关性得分，低于阈值（如 < 0.25）的切片予以剔除。
  3. **自校验与反思 (Self-Correction)**：若最终有效上下文为空，自动触发 `No-Context-Fallback` 机制，告知用户知识库中未检索到相关内容，并提供针对性的追问指引，而不是胡乱生成。
  4. **溯源标注**：在最终生成的回复末尾自动附加引用源 `[参考来源: 采购审批管理制度.md (第 3 章)]`。

### 3.4 改造四：数据库会话历史持久化
- **痛点**：数据库只有用户和业务表，没有对话表；LangGraph 使用内存 MemorySaver，重启即丢失。
- **真实化方案**：
  1. 在 `backend/models/chat.py` 中新增：
     - `ChatSession`: `id`, `session_id`, `user_id`, `title`, `created_at`, `updated_at`
     - `ChatMessage`: `id`, `session_id`, `role` (user/assistant/system/tool), `content`, `sources`, `created_at`
  2. 暴露标准 REST API：
     - `GET /api/v1/chat/sessions`：获取当前用户历史会话列表（供前端侧边栏历史抽屉回显）；
     - `GET /api/v1/chat/sessions/{session_id}/messages`：加载指定会话的历史聊天记录；
     - `DELETE /api/v1/chat/sessions/{session_id}`：删除会话。
  3. WebSocket 对话开始与结束时，自动将提问与回答真实存入数据库。

### 3.5 改造五：个人可及的开源工作流平台真实集成 (Dify & N8N)
- **痛点**：过去代码中只在内存列表记录了假事件，没有真正和外部平台对话。
- **真实化方案**：
  1. **N8N 真实联动**：当发生大额采购或报修工单创建时，系统真正通过 HTTP POST 向用户配置的 N8N Webhook 发送 JSON 载荷，可触发 N8N 后续的邮件、自动化脚本或通知流。
  2. **Dify 真实联动**：系统提供专用适配器，支持调用本地/云端部署的 Dify Workflow API，将复杂业务子流程委托给 Dify 执行并取回结果。

---

## 4. 生产/个人开发一键配置模板 (`.env.example`)

用户仅需在根目录配置 `.env` 即可完成全部真实能力的挂载：

```bash
# ==============================================================================
# Enterprise AI Digital Assistant - 个人可运行高保真配置模板 (.env)
# ==============================================================================

# 1. 核心运行模式
ENVIRONMENT=development
DEBUG=true
USE_MOCK_SYSTEMS=true   # HR/ERP/OA 保留高质量本地标准化模拟桩

# 2. 真实大模型配置 (支持 DeepSeek / 通义千问 / OpenAI / vLLM / Ollama)
OPENAI_API_BASE=https://api.deepseek.com/v1
OPENAI_API_KEY=sk-your-real-api-key
LLM_MODEL=deepseek-chat

# 若使用本地 vLLM 或 Ollama:
# OPENAI_API_BASE=http://localhost:8000/v1
# OPENAI_API_KEY=EMPTY
# LLM_MODEL=qwen2.5-7b-instruct

# 3. 真实 Embedding 向量计算配置 (fastembed: 本地免GPU极速运行; openai: API模式)
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5

# 4. 向量数据库 Qdrant 配置 (支持本地 Docker 或内嵌存储)
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=enterprise_knowledge

# 5. 持久化关系数据库 (默认支持零配置 SQLite，亦可直连本地 MySQL)
SQLALCHEMY_DATABASE_URI=sqlite:///./enterprise_ai.db
# 或使用 MySQL: mysql+pymysql://root:password@localhost:3306/enterprise_ai

# 6. 开源工作流平台对接 (选填，自建 Dify / N8N 时生效)
DIFY_API_BASE=http://localhost:8001/v1
DIFY_API_KEY=app-your-dify-api-key
N8N_WEBHOOK_URL=http://localhost:5678/webhook/your-webhook-uuid

# 7. 企业微信机器人通知 (选填，填写后审批消息将真实推送到群)
WECOM_WEBHOOK_URL=
```

---

## 5. 总结

通过本次纠偏：
1. **去伪存真**：剔除了纸面宣传中的不可及假设，锁定了个人开发者完全掌控的五大核心能力；
2. **彻底消灭 Fake Mock**：假 Embedding、假 LLM 生成、假会话记忆将被真实工业级实现全面替换；
3. **交付高保真产品**：用户 demo 时将拥有真实的 AI 多轮对话、真实的知识库规章问答、真实的会话历史留存与真实的本地工作流自动化！
