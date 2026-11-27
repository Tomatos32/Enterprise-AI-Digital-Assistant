# Subagent.MD - Claude Code Harness 子 Agent 简介与新窗口使用指南

> **适用范围**: 本仓库（企业级 AI 数字员工平台）

> **核心价值**: 新开 Claude Code 窗口时，**无需再手动复制粘贴长篇 Harness 规范**；只需一条 `/harness` 指令，主会话就会自动按模块并行调度 9 个专业子 Agent 跑完整个开发、审查、验证、文档与证据封存闭环。

---

## 1. 先搞懂原理：为什么新窗口不用再贴长提示词了？

只要你在 **本仓库根目录** 下打开新的 Claude Code 窗口，Claude Code 启动时会自动识别并加载以下 3 层配置：

| 层级 | 文件位置 | 标签 | 作用（替代你以前做的事） |
| :--- | :--- | :--- | :--- |
| **第 1 层：自动规范** | `CLAUDE.md` | `[自动加载]` | 新窗口打开即生效，自动注入全部 10 条红线、虚拟环境路径、受保护文件名单与并行规则（替代手动粘贴长规范）。 |
| **第 2 层：一键入口** | `.claude/skills/harness/SKILL.md` | `[主入口 /harness]` | 注册斜杠命令 `/harness`，把 6-Wave 编排流程、并行策略、重试上限固化为可执行 SOP。 |
| **第 3 层：专业团队** | `.claude/agents/harness-*.md` | `[9 个子 Agent]` | 把 Harness 每个环节拆成独立上下文、独立权限隔离的子 Agent，主会话可以**在同一轮同时派发多个子 Agent 并行干活**。 |

> **关键认知**：你面向的永远只有**当前主窗口**（即总控 `HarnessOrchestrator`）。你给主窗口下指令，主窗口负责拆任务、并行拉起子 Agent、汇总结果并把关门禁；你不需要自己切换窗口去和子 Agent 对话。

---

## 2. 新窗口怎么用？（直接复制即用的 6 种场景）

打开一个全新的 Claude Code 窗口（确认工作目录在本仓库根目录），按你的目的直接输入下面对应的一句话即可：

### 场景 A：刚开新窗口，只想先看项目当前进度（不改任何代码）

```text
/harness onboard
```

- **会发生什么**：主窗口后台拉起纯只读子 Agent `harness-onboarding`，帮你快速读取 `AGENTS.md`、`Summary.md`、`sprint-active.md` 等 9 份文档并检查 `git status`，然后只返回一份精炼摘要（不会把大文档塞爆你的主窗口上下文）。
- **适合时机**：每天开工第一句、切换新窗口准备接力开发前。

### 场景 B：按标准 Harness 全流程开发一个指定 Issue（最常用）

```text
/harness Issue-0062
```

或者附带你的补充要求（推荐，更精准）：

```text
/harness Issue-0062 重点剥离前端硬编码的采购参数，后端补全槽位提取和缺参澄清追问
```

- **会发生什么**（全自动流转，每步自动落盘到 `.harness/runs/Issue-0062/`）：
  1. **Wave 1 [锁单]**：体检工作区 + 主窗口创建 `issue.md`。
  2. **Wave 2 [规划]**：派发 `harness-planner` 产出 `plan.md` 并登记 `docs/plans/sprint-active.md`。
  3. **Wave 3 [开发]**：派发 `harness-developer` 写代码、补单测、自跑检查并写 `developer.md`（若前后端文件完全不重叠，会自动**同时并行启动 2 个 `harness-developer`** 分别写后端和前端）。
  4. **Wave 4 [并行门禁]**：**同一轮并行启动** `harness-reviewer`（11 维审计打分 -> `review.md`）+ `harness-verifier`（实跑 `ruff`/`mypy`/`pytest`/`vite build`/SHA-256 -> `verification.md`）。若审查 < 90 分或验证不通过，自动打回 Wave 3 修复重测（最多 2 轮）。
  5. **Wave 5 [并行同步]**：门禁通过后，启动 `harness-documentation` 同步 OpenAPI、Qdrant 校验与项目进度文档（`documentation.md`）；若改动涉及 RAG/路由/改写/Prompt/安全，会**同时并行启动** `harness-evaluator`（`benchmark.md`）。
  6. **Wave 6 [终审封存]**：启动 `harness-recorder` 做 6 项合规终审，刷盘 `summary.json`、`timeline.md`、`runtime.log`，并把证据文件夹全部锁为只读。

### 场景 C：强制开启 RAG / 路由 / 安全定量评测（加 `--eval`）

```text
/harness Issue-0063 --eval
```

- **会发生什么**：除全套流程外，强制在 Wave 5 让 `harness-evaluator` 与 `harness-documentation` **并行执行**，输出定量打分报告 `.harness/runs/Issue-0063/benchmark.md`。

### 场景 D：运维任务或带迁移/灰度探活的发布任务（加 `--deploy`）

```text
/harness Ops-0003 --eval --deploy
```

- **会发生什么**：只有在 `harness-reviewer` (`APPROVED >= 90`) 且 `harness-evaluator` (`RECOMMEND_DEPLOY >= 90`) 双通过后，Wave 6 才会派发 `harness-deployment` 执行 Alembic 迁移、镜像/编排检查、3 次 `/api/v1/health` 探活及失败自动回滚，产出 `deployment.md`。

### 场景 E：临时提一个还没编号的新需求 / Bug 修复

```text
/harness 给管理员后台增加导出工具审计日志为 CSV 的接口和按钮
```

- **会发生什么**：主窗口先核对 `.harness/runs/` 当前最大编号，自动分配下一个 `Issue-XXXX`，然后照常走完 6-Wave 全流程与 9 份证据归档。

### 场景 F：不跑全流程，只想单独点名某个（或某几个）子 Agent 干活

如果你已经自己改了代码，或者只想重跑其中某一步，直接用自然语言点名子 Agent 名称即可：

```text
# 1. 只做仓库现状体检（只读）
请调用 harness-onboarding 检查当前分支、未提交改动和最新测试基线

# 2. 代码改完了，同时并行跑审查 + 全量物理验证（最常用的局部组合）
请并行调用 harness-reviewer 和 harness-verifier，审计并验证 Issue-0062 的当前改动

# 3. 审查通过后，只同步 OpenAPI 和所有文档
请调用 harness-documentation 完成 Issue-0062 的文档与 OpenAPI 同步

# 4. 只跑一次定量评测
请调用 harness-evaluator 对当前意图路由和 Query 改写做回归评测

# 5. 所有证据齐了，只做最后审计封存与只读加锁
请调用 harness-recorder 审计并封存 .harness/runs/Issue-0062/
```

---

## 3. 9 个 Subagent 简介与功能标记总览

以下标记说明每个子 Agent 的职责边界、能否并发、以及它唯一允许产出的文件：

- `[只读]`：绝不修改任何业务代码文件，安全零副作用
- `[可并行]`：可与其他子 Agent 在同一轮同时执行，互不写冲突
- `[写代码]`：允许编辑 `backend/`、`frontend/` 源码与测试
- `[强制门禁]`：不通过则阻断流程，禁止向下游推进
- `[可选]`：仅涉及评测或发布时激活
- `[终审封存]`：全流程最后一棒，负责合规核验与只读加锁

| Subagent 名称 | 标记 | 一句话简介 | 触发时机 | 产出证据文件 |
| :--- | :--- | :--- | :--- | :--- |
| **`harness-onboarding`** | `[只读]` `[可并行]` | 仓库体检与基线诊断官。独立上下文通读 9 份核心文档、检查 git/OpenAPI/Qdrant 基线，防止主窗口上下文爆炸。 | Wave 1（新窗口启动或任务前） | 无落盘（向主窗口返回结构化简报） |
| **`harness-planner`** | `[只写计划]` | 首席架构规划师。读代码后拆出 <=5 个原子 Checkpoint，给出精确文件清单，并判断是否可拆成互不重叠的前后端并行轨道。 | Wave 2（`issue.md` 创建后） | `.harness/runs/<ID>/plan.md` + `docs/plans/sprint-active.md` |
| **`harness-developer`** | `[写代码]` `[可并行]` | 全栈开发与本地自测工程师。按 `plan.md` 写代码/Alembic 迁移/单测，并用虚拟环境跑本地 `ruff`/`mypy`/`pytest`/`vite build`（最多自修 3 次）。 | Wave 3（单轨道 1 个，前后端解耦时可并行 2+ 个） | 代码、测试、迁移 + `.harness/runs/<ID>/developer.md` |
| **`harness-reviewer`** | `[只读]` `[可并行]` `[强制门禁]` | 独立 11 维度代码审查官。直接审 `git diff`，按架构/安全/RBAC/性能/测试真实性等 11 维扣分，必须 `>= 90` 且 `Critical = 0` 才放行。 | Wave 4（与 `harness-verifier` 并行） | `.harness/runs/<ID>/review.md` |
| **`harness-verifier`** | `[只读]` `[可并行]` `[强制门禁]` | 独立物理门禁验证官。实跑全量 `ruff`、`mypy`、定向+全仓 `pytest`、`vite build`、去黑话、防 Emoji、受保护文件校验、3x `/api/v1/health`、Qdrant 状态与 SHA-256。 | Wave 4（与 `harness-reviewer` 并行） | `.harness/runs/<ID>/verification.md` |
| **`harness-documentation`** | `[只写文档]` `[可并行]` | 知识与契约同步官。导出最新 `openapi-spec.json`、验 Qdrant 向量点位，并把实测数据精准同步到 `API.md`/`PROJECT_PROGRESS.md`/`FRONTEND_PROGRESS.md`/`sprint-active.md`/`Summary.md`。 | Wave 5（门禁通过后，与 `harness-evaluator` 并行） | `docs/generated/openapi-spec.json`、仓库文档 + `documentation.md` |
| **`harness-evaluator`** | `[只读]` `[可并行]` `[可选]` | 定量评测官。运行 RAGAS / 意图路由矩阵 / 延迟 TTFT / 离线兜底 / Prompt 注入安全评测，算加权 `TotalScore`（>= 90 推荐发布）。 | Wave 5（带 `--eval` 或涉及 RAG/路由/改写/Prompt/安全时） | `.harness/runs/<ID>/benchmark.md` |
| **`harness-deployment`** | `[运维]` `[可选]` | 发布与回滚工程师。执行 `alembic upgrade head`、构建与灰度、3 次健康探活及冒烟测试；任一步失败立即自动回滚（`alembic downgrade -1` + 回退标签）。 | Wave 6（仅带 `--deploy` 或明确运维发布且前置门禁通过） | `.harness/runs/<ID>/deployment.md` |
| **`harness-recorder`** | `[终审封存]` | 运行时审计与记录官。核验 6 项合规门禁（证据齐全、Review APPROVED、OpenAPI 同步、受保护文件未动、Alembic 对齐），刷盘遥测并把证据目录全部加只读锁。 | Wave 6 最后一步（强制闭环） | `summary.json`、`timeline.md`、`runtime.log` + 全目录只读锁 |

---

## 4. 并行调度全景图（什么时候并行、什么时候串行）

```text
你在新窗口输入: /harness Issue-0062
        │
        ▼
[Wave 1] harness-onboarding (只读体检)  ||  git status 检查
        └─► 主窗口落盘: .harness/runs/Issue-0062/issue.md
        │
        ▼
[Wave 2] harness-planner (架构拆解 & 划分互不重叠文件轨道)
        └─► 落盘: plan.md + sprint-active.md ([ ])
        │
        ▼
[Wave 3] harness-developer
        ├─ 单模块任务: 1 个实例串行写完并本地自测
        └─ 前后端解耦任务: Track A (backend/*)  ||  Track B (frontend/*) 同时写
        └─► 落盘: 代码 + 单测 + developer.md
        │
        ▼
[Wave 4] ────────── 强制并行门禁（互不写同一文件，零冲突）──────────
        ├─ harness-reviewer  ──► review.md   (要求 APPROVED 且 Score >= 90)
        └─ harness-verifier  ──► verification.md (要求静态/测试/构建全部 PASS)
        └─► 任一失败 -> 带着精准行号意见打回 Wave 3（最多 2 轮）
        │   双双通过
        ▼
[Wave 5] ────────── 审批后并行收尾（零冲突）──────────
        ├─ harness-documentation ──► OpenAPI + 文档同步 + sprint-active [x] + documentation.md
        └─ harness-evaluator     ──► benchmark.md (仅 RAG/路由/改写/Prompt/安全或 --eval 时触发)
        │
        ▼
[Wave 6] (可选) harness-deployment ──► deployment.md (仅 --deploy 时触发)
        └─► harness-recorder ──► 6 项终审 + summary.json / timeline.md / runtime.log + 只读加锁
```

---

## 5. 新窗口自检清单 & 常见问题 (FAQ)

### Q1：怎么确认新窗口已经成功加载了这些 Subagent 和 `/harness`？
1. 确认你的终端/IDE 工作目录是**本仓库根目录**（不是上级目录，也不是 `backend/` 子目录）。
2. 在 Claude Code 输入框里打 `/harness`，能看到补全提示 `Orchestrate the Enterprise AI Digital Assistant Harness Engineering lifecycle...` 即代表技能已生效。
3. 输入 `/agents` 查看项目级子 Agent 列表，能看到 9 个 `harness-*` 即代表全部子 Agent 加载成功。

### Q2：跑完 `/harness Issue-XXXX` 后，会自动 `git commit` 或 `git push` 吗？
**不会。** 所有子 Agent 都严格禁止未经你明确授权就执行 `git commit` 或 `git push`。流水线结束后，主窗口会汇报完整实测数据和证据路径，由你审核后再决定是否提交。

### Q3：如果并行跑 2 个 `harness-developer`（比如后端 + 前端），会不会把同一个文件改乱？
**不会。** `harness-planner` 在 `plan.md` 中必须把并行轨道拆为**严格不相交的文件白名单**（例如 Track A 只能改 `backend/*`，Track B 只能改 `frontend/*`），且接口 JSON/WebSocket 协议在 `plan.md` 中提前锁死。只有文件解耦时才会并行；若文件强耦合，会自动退化为单轨道顺序开发。

### Q4：为什么不能把整套流程写成一个“总管 Subagent”再去调其他 Subagent？
这是 Claude Code 的底层安全机制：**子 Agent 不能再嵌套派生子 Agent**。因此最稳健的设计就是：
- **主窗口本身 = `HarnessOrchestrator`**（通过 `CLAUDE.md` + `/harness` 技能获得编排能力）；
- **9 个 `.claude/agents/harness-*.md` = 执行层专业子 Agent**，由主窗口在同一轮并发拉起。

### Q5：这些文件需要提交到 Git 吗？
- **建议提交到 Git**：`CLAUDE.md`、`Subagent.MD`、`.claude/skills/harness/SKILL.md`、`.claude/agents/harness-*.md`（提交后任何分支、任何机器、任何新窗口拉下来就能直接用）。
- **不要提交到 Git**：`.claude/settings.local.json`（本地个人权限配置）。
