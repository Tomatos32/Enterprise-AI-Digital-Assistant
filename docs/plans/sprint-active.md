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

- [x] **Issue-0046: Ollama 思考链真实透传、ThoughtLine 动效规范化重塑与发送状态解闭锁 (ThoughtLine & Real CoT) - [100% COMPLETED]**
  - [x] Checkpoint 1: 基于 Vue Bits 官方规范（TypeScript + Tailwind + @hugeicons/core-free-icons）重塑 `<ThoughtLine />` 组件
  - [x] Checkpoint 2: 彻底清除 ThoughtBadge 中 1.8 秒硬编码计时，改为从提问到首字动态打表记录真实思考耗时
  - [x] Checkpoint 3: 彻底清除固定 4 步采购意图、42ms/18ms 假工具卡片与写死采购制度引用，实现 100% 真实数据驱动
  - [x] Checkpoint 4: 修复 useChatStream 中 complete 事件守卫，终态强制复位 isStreaming，彻底解决发送键卡在停止方块
  - [x] Checkpoint 5: 后端 chat_ws.py 支持透传 Ollama reasoning 思考流，ThoughtLine 展开支持查看真实推理过程

- [x] **Issue-0047: WebSocket 心跳提问混淆治理、协程独立任务化隔离与输入防重抖动抑制 (Task Isolation & Anti-Duplicate) - [100% COMPLETED]**
  - [x] Checkpoint 1: 在 `chat_ws.py` 中对心跳 `ping` 消息进行即时 `pong` 分流，拦截空消息幽灵循环提问
  - [x] Checkpoint 2: 将问答生成独立为 `active_stream_task` 协程并绑定 TaskManager，使 `/abort` 精准刹车且 WebSocket 主连接不断线
  - [x] Checkpoint 3: 前端 `useChatStream.js` 实现单例连接守卫与 `isStreaming` 强防重入保护
  - [x] Checkpoint 4: `PromptBar.vue` 增加输入法 `isComposing` 与 350ms 发送锁，彻底消灭单次输入重复多次回复

- [x] **Issue-0048: RAG 意图路由重构（RAG-First 策略与知识源联动）、知识库检索 Tool 工具注册与向量入库幂等性治理 (RAG Intent Routing & Knowledge Tooling) - [100% COMPLETED]**
  - [x] Checkpoint 1: 重构 `router_node.py` 为 RAG-First 意图分类引擎，大幅扩充企业规章实体与诉求词库，并打通前端 `@知识源` 数据源强绑定
  - [x] Checkpoint 2: 在 `backend/tools/impl/knowledge_tools.py` 新增并注册全局 `search_knowledge_base` 工具，向大模型开放标准 Function Calling 知识检索
  - [x] Checkpoint 3: 加固 `backend/rag/vector_store.py` 向量入库，基于文档源路径与切片哈希采用 UUID5 确定性点 ID，杜绝向量重复爆炸
  - [x] Checkpoint 4: 改造 `backend/rag/retriever.py` 为单例池化检索器 (`get_hybrid_retriever`)，避免每轮对话重复全量重读磁盘与重新构建 BM25
  - [x] Checkpoint 5: 全量自动化测试全通 (28/28 PASS)，实测 `我出差需要临时借用备用机，期限是多久` 100% 命中制度并精准回答 14 天门禁

- [x] **Issue-0049: ThoughtLine 结构化全链路推理重塑（意图/检索/Rerank/建议）、TTFT 首字延迟极速穿透与输入栏交互去枷锁 (ThoughtLine Trace & TTFT Acceleration) - [100% COMPLETED]**
  - [x] Checkpoint 1: 移除输入栏强制 `@知识源` 的多余视觉引导，更新占位符为全自动意图识别与规章检索说明
  - [x] Checkpoint 2: 实现 `EnterpriseChatOpenAI` 拦截与提取 Ollama/DeepSeek reasoning 思考流，彻底修复 LangChain 丢弃思考 Token 导致的前端静默假死
  - [x] Checkpoint 3: 优化 WebSocket 流式管道，结构化推送【意图理解】->【制度检索】->【Rerank 语义重排】->【组织建议】四大 ThoughtLine 步骤并展示匹配文件名与置信度
  - [x] Checkpoint 4: 修复 `chat_ws.py` 嵌套模型去重过滤器，杜绝 `EnterpriseChatOpenAI` 引入的 Duplicate Token 重叠现象
  - [x] Checkpoint 5: 后端集成 FastAPI lifespan 预热机制，实测 TTFT 首字流式响应从 20s+ 骤降至 0.5s~3s，且步骤卡片与来源凭证 100% 真实联动

- [x] **Issue-0050: 根除 RAG 思考循环死锁与兜底模型假制度倒流漏洞 (RAG Grounding & Thinking Loop Fix) - [100% COMPLETED]**
  - [x] Checkpoint 1: 修复 `backend/rag/retriever.py` 中 RRF 融合因相对路径与绝对路径差异导致同一切片重复注入的缺陷
  - [x] Checkpoint 2: 在 `backend/graph/nodes/generate_node.py` 增加切片内容指纹去重，并注入对未提及条款（如押金）的明确说明准则，彻底消灭 2B 模型的死循环死锁
  - [x] Checkpoint 3: 彻底清除 `LocalEnterpriseChatModel` 中硬编码假制度文件（`01_FINANCE_TRAVEL_POLICY.md`）的陈旧 Mock 分支，改为动态真切片提炼
  - [x] Checkpoint 4: 将 `LLM_MAX_TOKENS` 扩容至 4096，保证长思考链下正文生成的充足 Token 预算
  - [x] Checkpoint 5: 端到端实测通过，多意图复合提问（借用期限、押金、超期扣款）100% 产出真实准确回复并规范引用实际制度文档

- [x] **Issue-0051: RAG 查询重写 (Query Rewriting)、多意图子查询拆分与 Rerank 强阈值截断 (RAG Precision Hardening) - [100% COMPLETED]**
  - [x] Checkpoint 1: 新建 `backend/rag/query_rewriter.py`，支持多轮对话指代消解、实体提炼与复合问题原子子查询拆分，剔除场景噪声词
  - [x] Checkpoint 2: 改造 `HybridRetriever.retrieve` 支持多查询并行双路混合召回与多候选列表 RRF 融合
  - [x] Checkpoint 3: 重构 `Reranker` 增加绝对底线门限 (`min_score=0.16`)、相对高分截断 (`0.60 * top_score`) 与跨领域排他截断，物理杜绝无关制度（如《04_FINANCE》）误召回
  - [x] Checkpoint 4: 编写 `test_query_rewriter.py` 专项单元测试，验证复合提问下 100% 排除财务文档且高分召回 IT 指南

- [x] **Issue-0052: 对齐 shadcn Vuebits 官方规范重塑 ThoughtLine、消除 Emoji 并统一样式字体 (ThoughtLine Vuebits Spec & UI Polish) - [100% COMPLETED]**
  - [x] Checkpoint 1: 全面排查并彻底清除前后端 ThoughtLine 步骤中的所有 Emoji 符号（💡/🔍/⚖️/✍️/🛠️/📋），改用典雅严谨的工业级文本标签
  - [x] Checkpoint 2: 统一 ThoughtLine 内各步骤、打勾图标与思考预览区的字体族（统一采用 `font-sans`），消除字体参差不齐
  - [x] Checkpoint 3: 严格对齐 `@vue-bits/ThoughtLine` 官方 TSX/Tailwind 排版规范，确保呼吸光标、秒表打表与折叠收拢动效 100% 稳态运行
  - [x] Checkpoint 4: 全量测试回归通过，前端生产构建通过 (7.82s)

- [x] **Issue-0053: 思考延迟根因穿透与 NativeOllama 极速推理模式 (Latency Root Cause & Fast Native Adapter) - [100% COMPLETED]**
  - [x] Checkpoint 1: 定位 26s 耗时 100% 产生于 Ollama 模型内部 1400 Token 英文思考流，实现 `NativeOllamaChatModel` 原生驱动
  - [x] Checkpoint 2: 提供 `LLM_THINKING` 可配置思考开关，极速模式下响应时延降至 2.88s (0.47s TTFT)
  - [x] Checkpoint 3: 消除历史多轮对话中的遗留错误对小模型元推理循环的干扰

- [x] **Issue-0054: 会话切换后深度思考与 ThoughtLine 完整历史持久化 (Thought & CoT Persistence) - [100% COMPLETED]**
  - [x] Checkpoint 1: 升级 `chat_messages` 数据表，新增 `thought`、`duration_seconds` 与 `thought_steps` 字段
  - [x] Checkpoint 2: 改造 WebSocket 完成帧，将思考文本、耗时与步骤列表落库，并通过 REST 消息接口导出
  - [x] Checkpoint 3: 前端 `chatStore` 与 `MessageItem` 历史消息完全恢复 ThoughtLine 状态，切换历史会话不再丢失思考过程
  - [x] Checkpoint 4: 编写 `test_thought_persistence.py` 专项测试并通过验证

- [x] **Issue-0055: 边栏展开收起会话展示不对称与时间分组截断修复 (Sidebar Session Grouping Alignment) - [100% COMPLETED]**
  - [x] Checkpoint 1: 在 `Sidebar.vue` 中补充 `olderSessions`（更早历史）渲染区域，消灭展开时 7 天前记录被丢弃的缺陷
  - [x] Checkpoint 2: 补充全部会话无缝保底渲染列表，确保无论展开还是收起，历史会话条数与展示完全对称一致
  - [x] Checkpoint 3: 将 `chatStore.js` 中的时间基准改造为动态计算，消除静态常驻时间戳造成的日期归类偏移

- [x] **Sprint R-05 / Issue-0056: 用户身份认证、角色上下文切换基座与 RBAC 视图隔离（不含安全密级） - [100% COMPLETED]**
  - [x] Checkpoint 1: 对齐后端 `rbac.py` 与 `auth.py` 身份属性及开发态快捷角色切换接口（不暴露密码）
  - [x] Checkpoint 2: 实现 `chat.py`、`chat_ws.py` 与 `approval.py` 在携带 Token 时的会话归属隔离与审批权限/署名校验（向后兼容无头单测）
  - [x] Checkpoint 3: 构建前端 `authStore.js` 与 `LoginView.vue`，重构 `chatStore.js`、`useChatStream.js`、`approvalStore.js` 消除 `u_vue3_user` 与「张经理」硬编码
  - [x] Checkpoint 4: 改造 `Sidebar.vue`、`Header.vue`、`MobileDrawer.vue` 与 `router/index.js`，实现三角色菜单隔离、全局角色切换器、`/admin/*` 预留插槽及无权限中文提示守卫
  - [x] Checkpoint 5: 编写 `test_auth_role_isolation.py`、登记全仓 Mock 至 `docs/MOCK_INVENTORY.md`，并通过 `ruff`、`pytest`、`vite build` 与 Reviewer 11 维审查归档 `.harness/runs/Issue-0056/`

- [x] **Sprint R-05 / Issue-0057: 管理员专属·大模型参数与 LangGraph 节点配置中心 (`/admin/settings`) - [100% COMPLETED]**
  - [x] Checkpoint 1: 在 `.harness/runs/Issue-0057/` 初始化 `issue.md` 与 `plan.md` 并同步登记至 `docs/plans/sprint-active.md`
  - [x] Checkpoint 2: 新建 `backend/core/runtime_config.py`（安全白名单持久化覆盖与密钥脱敏）并改造 `llm.py`、`retriever.py`、`knowledge_tools.py`、`retrieve_node.py`、`generate_node.py` 实现参数热生效
  - [x] Checkpoint 3: 新建 `backend/api/v1/admin_config.py` 并挂载至 `backend/main.py`（`/api/v1/admin/config`，强制 `RoleEnum.ADMIN` 鉴权 + 探活/重置能力）
  - [x] Checkpoint 4: 新建 `frontend/src/views/AdminSettingsView.vue`、`UserPreferencesModal.vue`、`preferencesStore.js` 并修改 `router/index.js`、`Sidebar.vue`、`MobileDrawer.vue`、`Header.vue`、`App.vue` 盘活分层 `<Settings />` 入口
  - [x] Checkpoint 5: 编写 `test_admin_config_rbac.py` (7/7 PASS)，通过 `ruff` (0 errors)、`mypy` (改动文件 0 errors)、专项 `pytest` (48/48 PASS)、`vite build` (7,916 modules / 7.46s) 与 Reviewer 11 维审查并归档 `.harness/runs/Issue-0057/` 证据包

- [x] **Sprint R-05 / Issue-0058: 管理员专属·知识文档上传与异步解析任务中心 (`/admin/tasks`) - [100% COMPLETED]**
  - [x] Checkpoint 1: 在 `.harness/runs/Issue-0058/` 初始化 `issue.md` 与 `plan.md` 并同步登记至 `docs/plans/sprint-active.md`
  - [x] Checkpoint 2: 新建 `backend/core/knowledge_ledger.py` 并改造 `backend/api/v1/knowledge.py`、`backend/api/v1/tasks.py`、`backend/tasks/ingestion_tasks.py`、`backend/rag/loader.py`（收紧管理员 RBAC、单文件校验、上传历史台账与 Celery 离线异步降级兜底）
  - [x] Checkpoint 3: 新建 `frontend/src/views/AdminTasksView.vue`（向量底座概览与已索引文档清单、多格式拖拽上传与分类/模式切换、StatusMark 5 阶段任务进度轮询追踪、FuseButton 一键同步二次确认保护）
  - [x] Checkpoint 4: 更新 `frontend/src/router/index.js`、挂载 `Sidebar.vue` 与 `MobileDrawer.vue` 管理员「知识库运维与任务中心」入口
  - [x] Checkpoint 5: 编写 `backend/tests/unit/test_admin_knowledge_tasks.py` (6/6 PASS)，同步文档与 OpenAPI Schema，通过 `ruff` (0 errors)、`mypy` (改动文件 0 errors)、`pytest`、`vite build` 与 Reviewer 11 维审查并归档 `.harness/runs/Issue-0058/` 证据包

- [x] **Sprint R-05 / Issue-0059: 管理员专属·系统遥测、工具审计与 SLA 监控看板 (`/admin/monitoring`) - [100% COMPLETED]**
  - [x] Checkpoint 1 (Step 1): 在 `.harness/runs/Issue-0059/` 创建 `issue.md` 与 `plan.md`，同步更新 `docs/plans/sprint-active.md`
  - [x] Checkpoint 2 (Step 2): 完善 `backend/core/metrics.py`（修复 mypy 语法冲突并新增 Tool 审计与统计指标）、打通核心运行链路指标上报、新建 `backend/api/v1/monitoring.py` 并挂载 `/api/v1/admin/monitoring/overview`（严格 `RoleEnum.ADMIN` RBAC）
  - [x] Checkpoint 3 (Step 3): 新建 `frontend/src/views/AdminMonitoringView.vue` 并替换 `/admin/monitoring` 路由占位组件（KPI 卡片、TTFT/Tool 双主题响应式 SVG 图表、P0~P4 SLA 履约表、手动刷新与 15s/30s 静默轮询）
  - [x] Checkpoint 4 (Step 4): 更新 `Sidebar.vue` 与 `MobileDrawer.vue` 管理员「系统监控与 SLA 看板」入口，编写 `test_admin_monitoring_api.py` (4/4 PASS)，执行 `ruff`/`mypy`/`pytest`/`npm run build`，同步文档/Schema 并归档 `.harness/runs/Issue-0059/` 证据包

- [x] **Sprint R-06 / Issue-0060: 多轮上下文感知的混合认知意图识别引擎与数据源/指令路由重构 - [100% COMPLETED]**
  - [x] Checkpoint 1: 在 `.harness/runs/Issue-0060/` 初始化 `issue.md` 与 `plan.md`，同步更新 `docs/plans/sprint-active.md`
  - [x] Checkpoint 2: 升级 `config.py`、`llm.py`、`state.py` 与 `workflow.py`（新增路由轻量非思考模型工厂 `get_router_llm`、无环复合意图边 `retrieve -> tool/approval/generate` 与离线合成兼容）
  - [x] Checkpoint 3: 重构 `router_node.py` 为三层混合认知路由引擎（Tier 1 确定性指令/`@数据源`/寒暄护栏 + Tier 2 轻量 LLM 6 轮上下文分类与严格超时兜底 + Tier 3 增强多轮上下文/动态金额/政策与执行消歧引擎），同步升级 `generate_node.py`（含 `/audit` fail-closed RBAC）、`retrieve_node.py`、`tool_node.py` 与 `chat_ws.py` 事件隔离
  - [x] Checkpoint 4: 对齐 `PromptBar.vue` 与 `ChatContainer.vue` 的 `@数据源` (`kb_all`/`db_mysql`/`erp_sap`) 与 `/` 指令 (`/audit`/`/kb`/`/help`) 元数据透传契约
  - [x] Checkpoint 5: 编写 `test_cognitive_router.py` (12/12 PASS)，通过 `ruff` (0 errors)、10 文件 `mypy` (0 errors)、12 套件联测 (68/68 PASS)、全仓 `pytest` (291 passed, 2 pre-existing failed)、`vite build` (7,920 modules) 与 Reviewer 11 维审查 (Score: 95, `APPROVED`)，更新文档并归档 `.harness/runs/Issue-0060/` 9 份完整证据包

- [x] **Sprint R-06 / Issue-0061: 多轮指代消解、上下文补全与跨领域 Query 改写引擎升级 - [100% COMPLETED]**
  - [x] Checkpoint 1: 在 `.harness/runs/Issue-0061/` 初始化 `issue.md` 与 `plan.md`，同步登记至 `docs/plans/sprint-active.md`
  - [x] Checkpoint 2: 升级 `config.py`、`llm.py` 与 `loader.py`（新增 `QUERY_REWRITER_LLM_*` 配置、共享轻量非思考模型工厂 `get_rewriter_llm` 与 `load_uploaded_data_documents` 顶层容错加载器）
  - [x] Checkpoint 3: 升级 `backend/rag/query_rewriter.py`（规则预处理 + 轻量非思考 LLM 上下文改写 + 增强确定性回退，解决无代词隐式省略补全、3 轮链式平行追问、自定义文档主题承接、多领域权重打分、全 6 域自适应子查询拆解、未消解代词/单轮伪指代护栏）
  - [x] Checkpoint 4: 升级 `retriever.py`、`retrieve_node.py`、`chat_ws.py` 与 `knowledge.py`（取消推断单域硬锁改为跨领域软加权与多样性保底并兼容旧版 `Reranker` 签名、将 `standalone_query` 传入 Graph RAG、启动自动同步 `backend/data/` 上传文档到 BM25 并阻断改写 LLM 流式外泄）
  - [x] Checkpoint 5: 编写 `test_contextual_query_rewriter.py` (10/10 PASS)，通过 `ruff` (0 errors)、9 文件 `mypy` (0 errors)、15 套件核心联测 (87/87 PASS)、全仓 `pytest` (301 passed, 2 pre-existing failed)、Live Ollama 实测 (5/5 PASS)、`vite build` 与 Reviewer 11 维审查 (Score: 95, `APPROVED`)，同步仓库文档并归档 `.harness/runs/Issue-0061/` 9 份只读证据包

- [x] **Sprint R-06 / Issue-0062: 工具与审批语义槽位提取引擎重构、前端硬编码剥离与全站中性极简界面重塑 - [100% COMPLETED]**
  - [x] Checkpoint 1: 在 `.harness/runs/Issue-0062/` 初始化 `issue.md` 与 `plan.md`，完成全站 `design-review` 视觉审查并登记至 `docs/plans/sprint-active.md`
  - [x] Checkpoint 2: 新建 `backend/tools/slot_extractor.py` 并升级 `config.py` 与 `llm.py`（共享中文/阿拉伯金额数量解析、双层混合语义槽位提取、策略 5.1A HR 邮箱反查、策略 5.2A 采购单价显式合规门禁与跨轮缺参历史承接）
  - [x] Checkpoint 3: 升级 `router_node.py`、`tool_node.py`、`approval_node.py`、`generate_node.py`、`workflow.py` 与 `chat_ws.py`（清除全部假默认值、多轮补槽闭环与总额重判、无环 `tool -> approval` 升级、零落库缺参澄清、补全 `interrupt()` 载荷及阻断抽槽流式泄露）
  - [x] Checkpoint 4: 剥离 `ChatContainer.vue` 硬编码并净化 `ApprovalCard.vue`，结合 `awesome-design-md-main`、`shadcn`（`DotGridBackdrop` / `HoldButton`）与 `emil-design-eng` 完成全站 36 文件中性单色重塑、禁用渐变发光、去除感叹号徽章与动效打磨
  - [x] Checkpoint 5: 编写 `test_slot_extractor.py` (29/29 PASS)，通过 `ruff` (0 errors)、10 文件 `mypy` (0 errors)、8 套件核心联测 (73/73 PASS)、全仓 `pytest` (330 passed, 2 pre-existing failed)、Live Ollama 实测 (5/5 PASS)、`vite build` (7923 modules) 与去术语扫描 (0 violations)
  - [x] Checkpoint 6: 同步仓库文档与 OpenAPI Schema (38 paths IN_SYNC)，完成 Reviewer 11 维审查 (Score: 100, `APPROVED`) 并归档 `.harness/runs/Issue-0062/` 9 份只读证据包

- [x] **Sprint R-06 / Issue-0063: 意图与改写黄金评测集、对抗回归测试、路由/改写可观测联动与基线清零 - [100% COMPLETED]**
  - [x] Checkpoint 1 [Track A]: 扩展 `runtime_config.py`、`admin_config.py`、`metrics.py` 与 `monitoring.py`，构建路由/改写/抽槽运行态配置与 `telemetry.cognitive` 聚合基座
  - [x] Checkpoint 2 [Track A]: 在 `router_node.py`、`query_rewriter.py` 与 `slot_extractor.py` 接入非侵入式认知可观测埋点（避免 `arewrite` 双重计数）
  - [x] Checkpoint 3 [Track B]: 改造 `AdminSettingsView.vue` 与 `AdminMonitoringView.vue`，联动认知路由与查询改写配置及诊断看板
  - [x] Checkpoint 4 [Track A]: 新建 `test_intent_routing_matrix.py` 黄金评测与对抗矩阵，并扩充 `test_contextual_query_rewriter.py`、`test_admin_config_rbac.py`、`test_admin_monitoring_api.py`
  - [x] Checkpoint 5 [Track A]: 修复 `test_mock_systems.py`、`test_thought_persistence.py` 与 `test_graph_unittest.py` 历史 2 项遗留失败，实现全仓 `pytest` 100% PASS (389 passed, 0 failed; ruff 0 errors; mypy 14 modified files 0 errors; vite build 7923 modules; ReviewScore: 95/100 `APPROVED`; Sprint R-06 closed)

---

## Historical Achievements (已交付稳态资产):
- [x] 前端现代化终端体验重塑 (Sprint F-01 ~ F-08 全部闭环，Vue3 + Tailwind + 响应式布局 + 人机协同审批卡片 100% 就绪)
- [x] LangGraph 状态机拓扑与意图路由核心框架 (StateGraph 骨架、条件边、工具注册器)
- [x] 基础设施与代码质量体系 (Ruff 0 错误 / 0 警告，自动化测试套件基线)
- [x] 多模态文档解析器骨架 (双栏重构、跨页表格合并与 Excel 表头解析基线)
