# Enterprise AI Harness Engineering Directory Design
> 企业级 AI 数字员工平台——Agent 自主开发脚手架目录体系规范 (V1.0)

---

## 1. 全局分类维度矩阵 (Classification Matrix)

在 Harness Engineering 体系中，目录不仅是代码的存放位置，更是 **AI Agent 识别权限、记忆属性与数据生命周期的物理边界**。我们将所有目录划分为四大物理维度：

- **维度一：数据维护者 (Maintainer)**：`AI 自动维护` vs `人类硬性维护` vs `人机协作`
- **维度二：记忆属性 (Memory Type)**：`长期知识 (Long-Term)` vs `动态计划 (Dynamic Plan)`
- **维度三：运行时属性 (Runtime Tier)**：`项目代码/配置` vs `运行时数据 (Runtime Only)`
- **维度四：治理层级 (Governance Tier)**：`控制面 (Control Plane)` vs `数据面 (Data Plane)`

### 目录属性总览表

| 目录名称 | 核心职责概述 | 维护者 (Maintainer) | 记忆/数据属性 | Git 版本控制 |
| :--- | :--- | :--- | :--- | :--- |
| `AGENTS.md` | **[根节点]** Agent 导航入口、安全红线与测试指令 | **人类硬性维护** | 长期规则 (Root Rule) | 必须版本控制 |
| `backend/` | 后端业务代码（FastAPI, LangGraph 状态机, RAG, Tools） | **人机协作** (Pair-Coding) | 项目应用源码 | 必须版本控制 |
| `frontend/` | 前端 UI 界面代码（Vue3, NuxtJS, Tailwind） | **人机协作** (Pair-Coding) | 项目应用源码 | 必须版本控制 |
| `docs/` | 系统级设计文档（架构、数据库 ER 图、API 规范等） | **人机协作** (Doc Agent) | 长期知识 (Long-Term) | 必须版本控制 |
| `memory/` | 业务概念、领域字典、历史 Bug 排错库（Lessons） | **AI 提取 / 人类审计** | 长期记忆 (Long-Term) | 必须版本控制 |
| `plans/` | 12-Sprint 路线图、当前 Sprint 任务与 Checkpoint 状态 | **AI 自动更新进度** | 动态计划 (Dynamic) | 必须版本控制 |
| `decision/` | 架构决策记录 (ADR) | **人类最终审批** / AI 起草 | 长期记忆 (Long-Term) | 必须版本控制 |
| `generated/` | 自动抽取的 OpenAPI JSON、数据库 DDL 与 AST 图谱 | **AI 100% 自动维护** | 机器生成元数据 | 必须版本控制 |
| `prompt/` | Agent 系统提示词模版、Few-shot 数据集与安全规则 | **人类硬性维护** | 长期规则 (Prompt Control)| 必须版本控制 |
| `agents/` | Harness 专属 Subagent 权限配置文件与控制面 | **人类硬性维护** | 控制面配置 (Control) | 必须版本控制 |
| `workflow/` | AST 提取脚本、Git Hook 触发器与自动化逻辑 | **人类硬性维护** | 控制面工具 (Infra) | 必须版本控制 |
| `benchmark/` | RAGAS 评估数据集、模拟测试 Query 及压测脚本 | **人机协作** | 质量保障数据 | 必须版本控制 |
| `logs/` | Agent 执行轨迹、Tool Call 日志、审计与测试日志 | **系统运行时产生** | 运行时数据 (Runtime) | **Git 忽略 (.gitignore)**|
| `.github/` | GitHub Actions CI/CD 流水线与 Issue/PR 模版 | **人类硬性维护** | 基础设施/治理 | 必须版本控制 |

---

## 2. 目录职责深度解析

### 2.1 应用源码目录 (Application Code Base)
- **`backend/`**
  - **职责**：存放后端 Python 业务源码。包括 FastAPI 路由层 (`api/`)、LangGraph 图状态机节点与边 (`graph/`)、RAG 解析与 Qdrant 检索器 (`rag/`)、Function Calling 工具注册表 (`tools/`)、SQLAlchemy/Pydantic 模型 (`models/`) 及 Celery 异步任务 (`tasks/`)。
  - **属性**：人机协作开发；应用代码。
- **`frontend/`**
  - **职责**：存放 Vue3 / NuxtJS 前端应用。包括对话组件、审批卡片、WebSocket 长连接状态管理及样式配置。
  - **属性**：人机协作开发；应用代码。

### 2.2 知识、记忆与决策目录 (Knowledge, Memory & ADR)
- **`docs/`**
  - **职责**：存放系统的规范说明书（架构设计、数据库 ER 图、API 设计规格、部署指南等），是 Agent 了解整体系统全貌的文档依据。
  - **属性**：长期知识；Doc Agent 可进行精准段落 Patch 修改。
- **`memory/`**
  - **职责**：存放 Agent 长期记忆资产。`system-context.md` 存储核心概念与术语表；`bug-history.md` 存储历史踩坑经验与回归排错模式。
  - **属性**：长期记忆；AI 自动提取归纳，人类定期审计。
- **`decision/`**
  - **职责**：存放项目的 ADR（Architecture Decision Records）。记录如选择 LangGraph、开启 vLLM Prefix Cache 等重大技术决策及上下文。
  - **属性**：长期记忆；AI 可生成 Draft 草案，必须经由人类 Approve。

### 2.3 计划与机器生成目录 (Execution Plans & Auto-Generated)
- **`plans/`**
  - **职责**：包含全局 `roadmap.md` 及动态的 `sprint-active.md`。用于指示 Agent 当前 Sprint 的任务拆解、Checkpoint 勾选状态与阻塞点。
  - **属性**：动态计划；AI 根据任务执行结果实时更新 `[x]` 状态。
- **`generated/`**
  - **职责**：专门存放由 CI 脚本或 Documentation Agent 自动提取生成的绝对契约文件（`openapi-spec.json`、数据库 `db-schema.md`、代码 `codebase-index.json`）。
  - **属性**：AI 100% 自动维护；严禁人类手动编辑。

### 2.4 控制面与运行保障目录 (Control Plane & Infrastructure)
- **`prompt/`**
  - **职责**：集中管理业务 Agent 使用的系统提示词模板（`.prompt`）及敏感词防御规则文件。
  - **属性**：人类硬性维护；防止 Agent 篡改自身 Prompt 控制链。
- **`agents/`**
  - **职责**：存放 Harness 内部各个 Subagent（如 CodingAgent, DocAgent, ReviewAgent）的权限范围配置与上下文访问矩阵。
  - **属性**：人类硬性维护；控制 Agent 行为边界。
- **`workflow/`**
  - **职责**：存放 Harness 自动化脚本（AST 解析、OpenAPI 导出脚本）及 Git Pre-commit 触发器。
  - **属性**：人类硬性维护；脚手架基础设施。
- **`benchmark/`**
  - **职责**：存放 RAGAS 测试数据集、Ground Truth 对照表及性能压测脚本。
  - **属性**：质量评估；人机共同补充测试集。
- **`logs/`**
  - **职责**：记录 Agent 运行时的 Trajectories（思考链与 Tool 调用日志）、测试结果日志与文档同步审计日志。
  - **属性**：运行时数据；**必须加入 `.gitignore`**，防止膨胀。
- **`.github/`**
  - **职责**：存放 CI/CD 工作流（GitHub Actions）及 Git 治理模版。
  - **属性**：人类硬性维护；基础设施。

---

## 3. 完整 Harness 树状目录结构 (Complete Directory Tree)

```text
enterprise-ai-agent/
├── AGENTS.md                          # [ROOT] [人类维护] Agent 导航入口与全局安全红线
├── README.md                          # [ROOT] [人类维护] 项目全貌指南与 QuickStart
├── docker-compose.yml                 # [ROOT] [人机协作] 单机容器服务编排
├── Makefile                           # [ROOT] [人类维护] 自动化命令快捷入口
│
├── backend/                           # [人机协作] [应用代码] 后端 Python 服务
│   ├── api/                           # FastAPI 路由与 WebSocket Endpoint
│   │   ├── v1/                        # API 路由版本化实现
│   │   └── deps.py                    # 依赖注入与 JWT 鉴权
│   ├── graph/                         # LangGraph 状态机核心实现
│   │   ├── nodes/                     # IntentRouter, Retrieve, ToolExecutor 节点
│   │   ├── edges/                     # 条件路由器与转移 Edge
│   │   └── state.py                   # 强类型 AgentState 字典声明
│   ├── rag/                           # RAG 知识检索管道
│   │   ├── parser.py                  # Docling / OCR 文档解析器
│   │   ├── chunker.py                 # 递归字符切片器
│   │   └── retriever.py               # Qdrant Dense+Sparse 混合检索器
│   ├── tools/                         # Function Calling 工具集与 JSON Schema
│   │   ├── erp_tools.py               # 库存/采购查询与创建工具
│   │   └── registry.py                # 工具注册器与权限预检
│   ├── models/                        # 物理数据库结构与 Pydantic Body
│   │   ├── domain.py                  # SQLAlchemy ORM 映射表
│   │   └── schemas.py                 # Pydantic 强类型请求/响应体
│   ├── tasks/                         # Celery 异步后台任务
│   │   ├── celery_app.py              # Celery 初始化配置
│   │   └── worker_tasks.py            # OCR 解析与向量切片任务
│   └── tests/                         # pytest 测试集
│       ├── unit/                      # 单元测试
│       └── integration/               # 联调集成测试
│
├── frontend/                          # [人机协作] [应用代码] 前端 UI (Vue3 + NuxtJS)
│   ├── components/                    # 聊天窗口、审批卡片等 UI 组件
│   ├── pages/                         # NuxtJS 页面路由
│   └── composables/                   # WebSocket 与会话 VueUse Hooks
│
├── docs/                              # [人机协作] [长期知识] 系统设计规范说明书
│   ├── Architecture.md                # 系统架构设计说明书
│   ├── Database.md                    # 数据库 ER 图与物理表结构说明
│   ├── API.md                         # OpenAPI 接口文档规范
│   ├── Workflow.md                    # LangGraph 状态机与 SOP 流程图说明
│   └── Deployment.md                  # Docker / K8s / vLLM 部署指南
│
├── memory/                            # [AI提取/人类审计] [长期记忆] 知识与经验库
│   ├── system-context.md              # 业务概念、领域字典与系统边界说明
│   └── bug-history.md                 # 历史 Bug 排错库与回归测试模式 (Post-Mortem)
│
├── decision/                          # [人类审批/AI起草] [长期记忆] 架构决策记录 (ADR)
│   ├── 0001-langgraph-state-machine.md
│   ├── 0002-vllm-prompt-cache-strategy.md
│   └── 0003-hybrid-retrieval-rrf.md
│
├── plans/                             # [AI自动更新] [动态计划] 任务与路线图
│   ├── roadmap.md                     # 12-Sprint 全局里程碑规划
│   ├── sprint-active.md               # 当前 Sprint 任务拆解与 Checkpoint 状态
│   └── task-template.md               # AI 任务分解 Markdown 标准模版
│
├── generated/                         # [AI 100% 自动维护] [机器生成元数据] Schema 导出一览
│   ├── openapi-spec.json              # FastAPI 导出的 OpenAPI 3.0 JSON
│   ├── db-schema.md                   # 数据库 DDL 结构自动导出
│   └── codebase-index.json            # 源码符号图谱与 AST 依赖拓扑
│
├── prompt/                            # [人类硬性维护] [规则配置] Prompt 模版与防线
│   ├── intent-router.prompt           # 意图路由 System Prompt 模板
│   ├── planner.prompt                 # 任务规划器 Prompt 模板
│   └── guardrails.json                # Prompt 注入防御与敏感词正则库
│
├── agents/                            # [人类硬性维护] [控制面配置] Harness 代理控制面
│   ├── doc-agent.config.json          # Documentation Agent 权限与配置
│   ├── coding-agent.config.json       # Coding Agent 执行与验证配置
│   └── review-agent.config.json       # Code Review Agent 审查规则
│
├── workflow/                          # [人类硬性维护] [控制面工具] 脚手架脚本与 Hook
│   ├── scripts/                       # AST 提取、OpenAPI 自动生成 Python 脚本
│   │   ├── extract_ast.py
│   │   └── dump_openapi.py
│   └── hooks/                         # Git 钩子
│       └── pre-commit                 # 代码格式化与类型检查预检
│
├── benchmark/                         # [人机协作] [质量评估] 评估与测试集
│   ├── test-dataset.json              # RAGAS 评估数据集 (Query, Context, GroundTruth)
│   └── ragas-eval.py                  # RAG 自动化评估脚本
│
├── logs/                              # [系统运行时产生] [运行时数据] (Git 忽略)
│   ├── .gitignore                     # 忽略日志文件提交
│   ├── trajectories/                  # Agent 执行轨迹 JSON 栈
│   ├── audit.log                      # Documentation Agent 同步日志
│   └── pytest.log                     # 测试运行结果记录
│
└── .github/                           # [人类硬性维护] [治理基础设施] Git 与 CI/CD 规范
    ├── workflows/                     # GitHub Actions (CI 静态检查与构建)
    │   └── ci-pipeline.yml
    ├── PULL_REQUEST_TEMPLATE.md       # PR 提交模板
    └── ISSUE_TEMPLATE.md              # Bug / Task 模版
```
