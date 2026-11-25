# Enterprise AI Digital Assistant - 项目全量开发交接摘要与下阶段演进蓝图 (Summary.md)

> **文档用途**：面向新对话窗口的一键式上下文承接与工程交接档案  
> **基准分支**：`feat/frontend-modernization-copilot`  
> **当前日期**：2026-11-24  
> **当前工程模式**：**PRAGMATIC REALIZATION & COGNITIVE ROUTING MODE**（`Sprint R-05` 全量闭环，`Sprint R-06` 已闭环 P0 `Issue-0060` 混合认知意图路由引擎与 P1 `Issue-0061` 多轮指代消解/跨领域软加权检索升级，下一步待推 `Issue-0062` ~ `Issue-0063`）  
> **关联权威文档**：[AGENTS.md](file:///g:/LLM_Learning/product/AGENTS.md) · [docs/PROJECT_PROGRESS.md](file:///g:/LLM_Learning/product/docs/PROJECT_PROGRESS.md) · [docs/FRONTEND_PROGRESS.md](file:///g:/LLM_Learning/product/docs/FRONTEND_PROGRESS.md) · [docs/MOCK_INVENTORY.md](file:///g:/LLM_Learning/product/docs/MOCK_INVENTORY.md) · [docs/plans/sprint-active.md](file:///g:/LLM_Learning/product/docs/plans/sprint-active.md)

---

## 一、全局开发进度全景 (Milestone Snapshot)

| 阶段 / 战役代号 | 核心交付范围 | 物理闭环状态 |
| :--- | :--- | :---: |
| **Bootstrap / Dev / Staging (Sprint 1~30)** | `Issue-0001` ~ `Issue-0037` 全量闭环：FastAPI + LangGraph 状态机、Qdrant/BM25/RRF 混合检索、多模态解析、Celery 异步任务、三态熔断器、Saga 回滚、安全护栏、Helm 编排、压测与投产签发 (`docs/PRODUCTION_SIGNOFF.md`) | `[DONE] 100%` |
| **前端现代化重构 (Sprint F-01~F-09)** | Vue 3 + Tailwind CSS + Pinia + Vuebits 12 大旗舰动效组件（`PromptBar`, `ThoughtLine`, `CallChip`, `FolderFloat`, `LineSidebar`, `StatusMark`, `FuseButton` 等）+ Hugeicons/Lucide 双核矢量图标 + 象牙白/曜石灰双主题无闪烁拟合 | `[DONE] 100%` |
| **务实真实化攻坚 (Sprint R-01~R-04)** | `Issue-0038` ~ `Issue-0055` 全量闭环：MySQL/SQLite 会话与 CoT 持久化、FastEmbed/OpenAI/LocalSemantic 向量底座、NativeOllama 极速推理与 `LLM_THINKING` 开关、QueryRewriter v1 与 Rerank 截断、WS 心跳隔离与发送解锁 | `[DONE] 100%` |
| **RBAC 基座与管理员控制面 (Sprint R-05)** | `Issue-0056` ~ `Issue-0059` 全量闭环：JWT 三角色隔离 (`employee`/`manager`/`admin`)、`/admin/settings` 模型与 RAG 热配置台、`/admin/tasks` 知识库上传与异步解析中心、`/admin/monitoring` 遥测/工具审计/SLA 看板（`AdminSlotPlaceholderView` 已退役） | `[DONE] 100%` |
| **Day-2 SRE 运维任务** | `Ops-0001`、`Ops-0002` 已归档；`Ops-0003` ~ `Ops-0005`（指标告警调优、影子流量切流、脱敏红蓝审计）保留待排期 | `[PENDING]` |
| **明确剔除与暂缓搁置范围** | `[EXCLUDED]` 4 级安全密级前端切换与密级权限过滤开发；`[DEFERRED]` `/workflows`（Dify/N8N 编排页）与 `/eval`（DPO 标注导出台），对应后端路由继续保留可用 | `[SCOPE LOCKED]` |

---

## 二、当前实测技术基线与工作区状态 (Verified Baseline)

### 2.1 运行环境与核心验收数据（2026-11-19 ~ 2026-11-24 实测）
- **Python 虚拟环境**：`backend/.venv/Scripts/python.exe`（严禁使用全局 Python）。
- **静态检查与类型**：
  - `backend/.venv/Scripts/python.exe -m ruff check backend/ benchmark/`：`All checks passed!`（`0` 错误）。
  - `mypy`：`Issue-0060` (10 文件) 与 `Issue-0061` (9 文件) 涉及的后端与单测文件在 `--follow-imports=skip` 下 `0` 错误；全仓保留 12 个未改动历史文件共 29 项既有静态类型待治理。
- **前端生产构建**：`frontend/` 下 `npm run build`（`vite build`）转换 `7,920` 个模块，`0` 错误。
- **自动化测试基线**：
  - `test_cognitive_router.py`：`12/12 PASS`；`test_contextual_query_rewriter.py`：`10/10 PASS`；15 套件核心联测：`87/87 PASS`。
  - 全仓 `backend/.venv/Scripts/python.exe -m pytest backend/tests/ -q --tb=short`：`301 passed, 2 failed`（仅存 2 项既有历史用例：`test_graph_unittest.py` 仍断言旧版 `"processed your message"` 文案；`test_thought_persistence.py` 在全仓串行时受前置 `test_mock_systems.py` 未清理 `dependency_overrides` 影响，单独复跑 `1 passed`）。
- **API 契约与向量库状态**：
  - `docs/generated/openapi-spec.json`：`38` 条路径，`82,902` 字节，与 `backend.main:app` 100% 同步。
  - Qdrant（`local_storage` @ `backend/data/qdrant_storage`）：`enterprise_knowledge` 集合共 `7,387` 个向量点位，维度 `1024`，当前引擎 `local-semantic-ngram-v1`。
- **RBAC 演示账号（`backend/core/rbac.py`）**：
  - `employee` / `emp123`（普通员工 · 人力资源部）-> `/`、`/knowledge`、外观偏好弹窗。
  - `manager` / `manager123`（部门主管 · 采购管理部）-> 增加 `/approvals` 审批工作台。
  - `admin` / `admin123`（系统管理员 · IT 系统管理部）-> 增加 `/admin/settings`、`/admin/tasks`、`/admin/monitoring`。

### 2.2 Git 工作区现状提醒（重要）
当前分支 `feat/frontend-modernization-copilot` 上，**Sprint R-05 后半程（含 `Issue-0058`、`Issue-0059`）的改动与证据包尚处于未提交状态（working tree dirty）**：
- 主要修改：`backend/api/v1/{chat_ws,knowledge,tasks}.py`、`backend/core/{llm_gateway,llm_infra,metrics}.py`、`backend/graph/nodes/generate_node.py`、`backend/main.py`、`backend/rag/loader.py`、`backend/tasks/ingestion_tasks.py`、`backend/tools/registry.py`、`frontend/src/router/index.js`、`frontend/src/components/layout/{Sidebar,MobileDrawer}.vue`、`docs/{API,FRONTEND_PROGRESS,MOCK_INVENTORY,PROJECT_PROGRESS}.md`、`docs/generated/openapi-spec.json`、`docs/plans/sprint-active.md`、`.gitignore`、`benchmark/evaluation_report.md`。
- 主要新增：`backend/api/v1/monitoring.py`、`backend/core/knowledge_ledger.py`、`backend/tests/unit/{test_admin_knowledge_tasks,test_admin_monitoring_api}.py`、`frontend/src/views/{AdminMonitoringView,AdminTasksView}.vue`、`.harness/runs/Issue-0058/`、`.harness/runs/Issue-0059/`，以及未跟踪草稿 `"Thinking process.txt"`。
- **承接建议**：新窗口开始 `Sprint R-06` 编码前，先运行 `git status -s` 确认是否需要先行提交 `Issue-0058~0059` 稳态基线，或清理无关草稿文件，再建立 `.harness/runs/Issue-0060/` 沙盒。

---

## 三、现存痛点代码级诊断：意图识别、Query 改写与槽位提取短板

基于对当前后端状态机与前端对话组件的源码实查，用户体感“意图识别和改写不够完善”的根因集中在以下 4 个层面：

### 3.1 意图路由 (`backend/graph/nodes/router_node.py`)
1. **单轮字面关键词路由，无多轮上下文感知**：`router_node()` 仅读取 `messages[-1]`（L78-L95），完全忽略历史对话 `messages[:-1]`。追问句（如 `"那帮我提交一个吧"`、`"再查一下他的邮箱"`、`"如果超过这个天数呢"`）无法承接上一轮意图。
2. **规则过窄导致高频误路由**：
   - `tool` 分支（L105-L116）查员工强制要求包含字面 `"员工"`/`"employee"`，查库存强制要求包含 `"库存"`，导致 `"张伟的电话是多少"`、`"还有几台 MacBook 可以领"` 误路由至 `retrieve`；自然语言报障/转发请求未命中 `"创建工单"`/`"发邮件"` 时同样误路由。
   - `approval` 分支（L129-L131）仅硬编码匹配 `["6000", "10000", "22999", "大额", "超额"]`，其余任意真实超阈值采购金额（如 `8000` 元、`2 台 3500 元`）均无法触发审批流。
3. **非问答对话被强制拖入 RAG 检索引擎**：L168-L169 对任何长度 `>= 4` 且未精确命中 `GREETING_WORDS`/`ACK_WORDS` 的输入一律兜底路由为 `retrieve`，导致常规交流、文本翻译或总结指令被强行检索制度库并触发低置信拒答。
4. **`@数据源` 与 `/` 快捷指令前后脱节**：`frontend/src/components/ui/PromptBar.vue`（L228-L238）提供的 `@MySQL 业务台账`、`@ERP 采购与供应链`、`/audit`、`/kb`、`/help` 在传给后端后，`router_node.py`（L71-L75）对所有 `data_source` 无差别强制返回 `retrieve`，且 `/audit`、`/help` 无对应路由解析逻辑。
5. **单分支图拓扑限制**：`backend/graph/workflow.py` 当前为 `router -> (retrieve | tool | approval | generate)` 单跳路由，跨“先查制度再创建工单/审批”的复合意图无法协同流转；`backend/graph/subgraphs/` 与 `swarm_router.py` 尚未接入主流程。

### 3.2 Query 改写与检索联动 (`backend/rag/query_rewriter.py`, `retrieve_node.py`, `retriever.py`)
1. **指代消解高度局限**：`QueryRewriter._resolve_coreference()`（L66-L93）仅匹配 10 个固定代词且仅回溯 13 个硬编码名词正则，面对无代词的隐式省略追问（如 `"那产假呢？"`、`"住宿标准是多少？"`、`"超了会怎样？"`）完全无法补全主语与约束条件。
2. **子查询拆解模板化**：`_split_sub_queries()`（L115-L171）仅对 `备用机`、`办公电脑`、`差旅报销`、`年假休假` 4 个实体和 4 个切面做了关键词扩展；其余制度领域（HR 社保/试用期、Procurement 招标/验收、Security 保密/开源协议、CS SLA 以及管理员通过 `/admin/tasks` 新上传文档）仅能退化为标点切句，缺乏同义词归一化与意图扩写。
3. **单域硬锁引发跨领域信息丢失**：`_detect_primary_domain()`（L101-L102）遇到 `"借用"`/`"电脑"` 直接硬锁返回 `"IT"`，配合 `retriever.py`（L304-L311）的 `cat_matched` 过滤，导致跨领域复合问题（如 `"出差借备用机并按一线城市标准报销"`）或采购类电脑询问丢失 `FINANCE`/`PROCUREMENT` 条款。
4. **Graph RAG 与上传文档持久化盲区**：`retrieve_node.py:L74` 将原始 `query` 而非 `rewritten.standalone_query` 传入 `default_enterprise_kg.query_graph_rag()`，使带指代的提问丢失图谱召回；`HybridRetriever.__init__` 仅加载 `docs/sample_kb`，重启服务后 `backend/data/` 中由管理员上传的新文档虽保留于 Qdrant 向量中，但不会自动重新灌入内存 BM25 索引。

### 3.3 槽位提取与前端硬编码污染 (`ChatContainer.vue`, `tool_node.py`, `approval_node.py`)
1. **前端业务参数硬编码覆盖用户输入**：`frontend/src/components/ChatContainer.vue:L215-L224` 只要检测到消息包含 `"MacBook"` 或 `"采购"`，便强制注入固定 `purchase_args`（`MacBook Pro 16`、`quantity: 1`、`unit_price: 22999.0`），彻底掩盖用户实际输入的产品名、数量和单价。
2. **后端无语义抽槽与缺参澄清**：`backend/graph/nodes/tool_node.py:L45-L74` 与 `approval_node.py:L21-L29` 在缺失 LLM `tool_calls` 时直接使用写死的默认人名、固定邮箱、固定 `MacBook` 库存查询、固定 `P2` 优先级与 `6000.0` 默认采购价，缺少结构化实体/金额提取与缺失槽位追问能力。

### 3.4 可观测性与热调配缺失 (`runtime_config.py`, `chat_ws.py`)
- `runtime_config.py` 与 `/admin/settings` 尚不支持路由策略 / Query 改写模式及超时配置；`chat_ws.py` 亦未在实时思考步骤或监控看板中暴露路由命中分布与改写前后对照诊断（对普通员工视图仍需严守零技术黑话约束）。

---

## 四、下一阶段推理规划：`Sprint R-06`（认知意图路由、多轮语境改写与语义槽位提取专项升级）

建议下一阶段以 **4 个原子化 Issue (`Issue-0060` ~ `Issue-0063`)** 推进，严格遵守 `P0 -> P3` 依赖顺序：

| 优先级 | Issue 编号 | 任务名称 | 核心落地范围与验收标准 |
| :---: | :--- | :--- | :--- |
| **P0** | **Issue-0060** `[DONE]` | **混合认知意图识别引擎与数据源/指令路由重构** | **[已闭环 · Score: 95/100 APPROVED]** 重构 `router_node.py` 为三层混合认知路由引擎（Tier 1 确定性指令/`@数据源`/寒暄护栏 + Tier 2 轻量非思考 6 轮 LLM 分类器与严格超时/事件隔离 + Tier 3 增强多轮上下文/动态金额/政策与执行消歧兜底）；打通 `workflow.py` 无环复合链路 `retrieve -> tool/approval/generate`；对齐 `PromptBar.vue`/`ChatContainer.vue` 元数据与 `/audit` fail-closed RBAC；新增 `test_cognitive_router.py` (12/12 PASS) 并归档 `.harness/runs/Issue-0060/`。 |
| **P1** | **Issue-0061** `[DONE]` | **多轮指代消解、上下文补全与跨领域 Query 改写引擎升级** | **[已闭环 · Score: 95/100 APPROVED]** 升级 `query_rewriter.py`、`retrieve_node.py`、`retriever.py`、`loader.py`、`chat_ws.py` 与 `knowledge.py`：落地三段式混合改写（规则预处理 + 轻量非思考 LLM `arewrite` 严格超时/流式隔离 + 增强确定性回退），支持显式代词/无代词隐式省略/3 轮链式平行追问、自定义上传文档动态实体承接与全 6 域自适应子查询拆解；取消推断单域硬锁改为跨领域软加权 + 多样性保底；将 `standalone_query` 传入 Graph RAG；启动自动同步 `backend/data/` 上传文档到内存 BM25；新增 `test_contextual_query_rewriter.py` (10/10 PASS) 并归档 `.harness/runs/Issue-0061/`。 |
| **P2** | **Issue-0062** | **工具/审批语义槽位提取器重构与前端硬编码剥离** | 彻底移除 `frontend/src/components/ChatContainer.vue:L215-L224` 硬编码 `purchase_args`；在后端构建结构化槽位提取器（提取人名、物品、数量、单价/总价、邮箱、工单优先级 P0~P4、部门与事由），支持大模型抽槽 + 中文数字/金额正则兜底；关键槽位缺失时返回自然语言追问澄清而非静默写入假默认值。 |
| **P3** | **Issue-0063** | **意图与改写黄金评测集、对抗回归测试与基线清零** | 新建 `test_intent_routing_matrix.py` 与 `test_contextual_query_rewriter.py`（覆盖多轮指代、关键词碰撞消歧、跨领域改写、真实金额与槽位抽取）；在 `runtime_config.py` / `monitoring.py` 增加路由与改写策略可观测指标；顺带修复全仓遗留的 2 项历史失败用例（`test_graph_unittest.py` 与 `test_thought_persistence.py` 测试隔离），实现全仓 `pytest` 100% 全通。 |

---

## 五、新对话窗口一键承接启动提示词

开启新窗口时，可直接发送以下指令使 Agent 立即完成对齐并启动开发：

```markdown
请先行阅读仓库根路径的 `Summary.md`、`AGENTS.md`、`docs/FRONTEND_PROGRESS.md`（第 9 节 Harness 规范与 Onboarding RULES）、`docs/PROJECT_PROGRESS.md` 与 `docs/plans/sprint-active.md`，完成 Repository Onboarding 状态核查（含 `git status -s` 检查）。
确认理解后，请严格遵循 Harness 10 阶段生命周期与 `.harness/runs/Issue-XXXX/` 沙盒证据规范，输出简要诊断结论，并准备接收 Sprint R-06（从 P0 `Issue-0060` 起）的研发指派。
```
