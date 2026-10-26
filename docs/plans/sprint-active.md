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

- [x] **Sprint F-09: ChatGPT / Claude 原生 Web 交互与 Vuebits 旗舰动效组件集成 - [100% COMPLETED]**
  - [x] Checkpoint 1: 依赖装配与注册表固化（`@hugeicons/vue`, `@hugeicons/core-free-icons`, `motion-v`, `lucide-vue-next`）
  - [x] Checkpoint 2: 日间温润白与夜间曜石灰双主题色彩令牌与背景无缝拟合（`src/index.css`, `tailwind.config.js`）
  - [x] Checkpoint 3: Vuebits 12 大旗舰原子组件套件落地（`PromptBar`, `ThoughtLine`, `CallChip`, `VoicePill`, `FolderFloat`, `LineSidebar` 等）
  - [x] Checkpoint 4: 输入交互区升维（`PromptBar` 充能发送、停止方块、`@` 数据源菜单、`/` 指令菜单与语音胶囊）
  - [x] Checkpoint 5: 思维链与工具调用重塑（`ThoughtLine` 呼吸秒表、模糊交叉收拢、`CallChip` 进度擦除与毫秒计时）
  - [x] Checkpoint 6: 侧栏光标邻近微动（`LineSidebar`）、知识库卡片云（`FolderFloat`）与金属流光徽章（`ShinyText`）
  - [x] Checkpoint 7: 全站 100% 消除系统 Emoji 符号，清空所有技术调试注释与占位符
  - [x] Checkpoint 8: 生产构建通过（`npm run build`），WCAG AA/AAA 对比度核验与 8 大证据包落盘 (ReviewScore: 98, APPROVED)

- [ ] **Sprint R-04: 个人可及的开源工作流平台集成与个人运行指南 (Workflows & Runbook)**
  - [ ] Checkpoint 1: 真实对接个人部署的 N8N Webhook（大额审批与工单创建事件真实推送）
  - [ ] Checkpoint 2: 真实对接 Dify Workflow API（支持复杂子任务委托执行）
  - [ ] Checkpoint 3: 固化 HR / ERP / OA 本地开箱即用模拟桩，确保无外部网络与商业账号下系统自闭环运行
  - [ ] Checkpoint 4: 编写个人高保真部署与运行指南 `docs/PERSONAL_RUNBOOK.md`

- [x] **Issue-0041: 前端多会话真实历史拉取、状态解绑与大模型 502 阻断自愈 (Session Persistence & Frontend Hardening) - [100% COMPLETED]**
  - [x] Checkpoint 1: 改造 `chatStore.js` 对接后端 `/api/v1/chat/sessions` 与历史消息拉取 API
  - [x] Checkpoint 2: 修复 `ChatContainer.vue` 会话切换消息丢失问题，实现历史消息真实回显
  - [x] Checkpoint 3: 优化 `useChatStream.js`，动态透传 activeSessionId，并在新建会话与异常时强制复位 `isStreaming` 发送锁
  - [x] Checkpoint 4: 修复 TaskManager 缺失 remove_task 导致的崩溃异常，完善未拉起本地 Ollama 时的交互引导提示

- [x] **Issue-0042: 跨平台 Windows 原生运维启停脚本套件治理、字符集修复与 Docker 守护进程自愈唤醒 (Ops-0003) - [100% COMPLETED]**
  - [x] Checkpoint 1: 将全部 4 个批处理脚本重构转换为 Windows 原生 ANSI/GBK 编码与标准 CRLF (`\r\n`) 换行符
  - [x] Checkpoint 2: 消除 `if-else` 中小括号提前截断语法错误，改用安全标签跳转 (`goto`) 并移除多字节 Emoji 干扰
  - [x] Checkpoint 3: 增加 Docker 守护进程连通性探活 (`docker info`)、Docker Desktop 自动唤醒与 45s 渐进式轮询重试机制
  - [x] Checkpoint 4: 完善安全释放脚本 `stop_app.bat` 与 `stop_ai_service.bat` 的防御性检测与资源清理

- [x] **Issue-0043: 本地大模型代理穿透直连修复与端到端真实推理闭环 (Real Model Connectivity) - [100% COMPLETED]**
  - [x] Checkpoint 1: 在 `backend/core/llm.py` 中禁用本地回环系统代理继承 (`trust_env=False`)，彻底根除 502 错误
  - [x] Checkpoint 2: 规范大模型端点地址，将 `localhost` 自动转为 `127.0.0.1` 规避 Windows IPv6 解析异常
  - [x] Checkpoint 3: 重构 `ResilientChatModel` 底层调用封装，修复 LangChain 私有 `_agenerate` 异常
  - [x] Checkpoint 4: 实测验证本地 Ollama `qwen3.5:2b` 端到端自然推理生成通过

- [x] **Issue-0044: 前端输入框交互净化与无套话纯净流式生成 (UI Cleanup & Clean Streaming) - [100% COMPLETED]**
  - [x] Checkpoint 1: 从 `PromptBar.vue` 彻底移除冗余的 `GlideSelect` 模型选择组件与多余依赖
  - [x] Checkpoint 2: 净化 `LocalEnterpriseChatModel`，彻底消除 `Hello! I have processed your message` 机械套话
  - [x] Checkpoint 3: 在 `StreamingSanitizer` 与 WebSocket `complete` 帧发送层自动过滤 `[Chat Answer]: ` 等技术代号
  - [x] Checkpoint 4: 增强 `generate_node.py` 防御机制，模型生成为空时自动触发高质量领域兜底合成

- [x] **Issue-0045: WebSocket 断开安全防御、会话 404 容错自愈与人设去客服套话 (WebSocket Resilience & Persona) - [100% COMPLETED]**
  - [x] Checkpoint 1: 在 `chat_ws.py` 实现 `safe_send_json` 防御机制，彻底消除 closed socket 后的 ASGI 发送崩溃
  - [x] Checkpoint 2: 前端 `chatStore.js` 增加对旧前端缓存 404 响应的自愈重注册处理，防止页面卡死
  - [x] Checkpoint 3: 重构普通对话分支提示词，消除“每次必须背诵三项业务范围”的机械客服限制，提供灵动自然问候
  - [x] Checkpoint 4: 完善全流程单元测试回归与生产构建验证

---

## Historical Achievements (已交付稳态资产):
- [x] 前端现代化终端体验重塑 (Sprint F-01 ~ F-08 全部闭环，Vue3 + Tailwind + 响应式布局 + 人机协同审批卡片 100% 就绪)
- [x] LangGraph 状态机拓扑与意图路由核心框架 (StateGraph 骨架、条件边、工具注册器)
- [x] 基础设施与代码质量体系 (Ruff 0 错误 / 0 警告，自动化测试套件基线)
- [x] 多模态文档解析器骨架 (双栏重构、跨页表格合并与 Excel 表头解析基线)
