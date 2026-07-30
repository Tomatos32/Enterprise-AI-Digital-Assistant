# Recorder Gap Analysis Report (Harness Recorder 缺口审计报告)

> **审计对象**: Enterprise AI Harness Engineering 架构与规范体系  
> **审计结论**: ⚠️ **Recorder 未完成物理集成 (INCOMPLETE INTEGRATION)**  
> **状态声明**: 尽管建立了 `recorder-design.md` 设计说明，但核心运行规范（`Runtime.md`、`Lifecycle.md`、`Communication.md`、`AGENTS.md`）尚未物理接入 Recorder 引擎。

---

## 1. 7 大维度项深度审计结果 (7-Point Audit Checklist)

| 审计项目 (Audit Item) | 检查结果 (Status) | 缺失情况说明 (Gap Description) |
| :--- | :---: | :--- |
| **1. Runtime.md 是否调用 Recorder** | ❌ **MISSING** | `Runtime.md` 仅在第 6 节提到了 `.harness/` 目录，但在第 2 节（工作流）、第 4 节（调用次序）及第 8 节（状态机）中**未将 Harness Recorder 作为常驻 Kernel 监听引擎进行显式调用**。 |
| **2. Lifecycle.md 是否包含 Recorder** | ❌ **MISSING** | `Lifecycle.md` 描述的 10 大 SDLC 阶段及 Sequence 序列图中，**完全未提及 Harness Recorder** 的事件拦截与日志落盘动作。 |
| **3. Communication.md 是否定义 Recorder Message** | ❌ **MISSING** | `Communication.md` 定义了 9 种 Agent 间的 Message 类型，但**未定义 Recorder 的事件总线 Hook (Event Bus Listener) 机制**与消息拦截监听规范。 |
| **4. AGENTS.md 是否要求 Recorder 必须执行** | ❌ **MISSING** | `AGENTS.md` 虽然在参考文档列表中包含了 `recorder-design.md`，但在 Section 6 **`Definition of Done (DoD)` 中未强行要求“Harness Recorder 必须在后台运行且日志刷盘成功”**。 |
| **5. 是否存在 `.harness/runs/` 目录规范** | ⚠️ **PARTIAL** | 在 `evidence-design.md` 中设计了 `.harness/runs/` 目录规范，但**代码库根目录下尚未初始化 `.harness/runs/` 物理目录与 `.gitignore` 保护**。 |
| **6. Recorder 是否定义 `summary.json`, `timeline.md`, `runtime.log` 生成规则** | ⚠️ **ISOLATED** | 生成规则仅在 `recorder-design.md` 中孤立定义，**未注入到主流程的核心契约文件（`Runtime.md` / `Lifecycle.md`）中**。 |
| **7. Issue Close 是否依赖 Recorder** | ❌ **MISSING** | `Lifecycle.md` Stage 10 (Closed) 与 `AGENTS.md` 关单条件**未把 Recorder 的 `timeline.md` 与 `runtime.log` 刷盘完成作为结案的前置依赖**。 |

---

## 2. Recorder Gap Analysis 缺口清单 (Detailed Gaps)

为了使 Harness Recorder 从“单文档设计”真正升级为“物理可运行 Kernel”，当前仍存在以下 4 大核心缺失：

### 缺口 1: 缺少 Message Bus 监听 Hook 定义 (Communication.md 缺失)
- **现状**：`Communication.md` 仅定义了 Agent 之间的点对点与单向 Message 投递。
- **缺口**：缺少一个被动监听事件总线（Pub/Sub Event Bus Listener）。Recorder 无法在不侵入 Agent 代码的前提下静默捕获 `TASK`、`ARTIFACT`、`REVIEW` 等消息。

### 缺口 2: 缺少 SDLC 生命周期节点注入 (Lifecycle.md 缺失)
- **现状**：`Lifecycle.md` 将每个阶段的输入输出仅限定在专职 Agent 手中。
- **缺口**：未规定在 Stage 0 (Issue Ingress) 时自动 Spawn Recorder 进程，也未规定在 Stage 10 (Closed) 时由 Orchestrator 触发 Recorder 刷盘退出。

### 缺口 3: 缺少物理执行控制契约 (Runtime.md 缺失)
- **现状**：`Runtime.md` 规定了 Agent 的调用逻辑，但未把 Recorder 设定为物理运行的前提条件。
- **缺口**：若 Recorder 因挂载失败或磁盘空间不足崩溃，`Runtime.md` 未定义系统是降级运行还是立即终止线程（Fail-Fast）。

### 缺口 4: 关单门禁 (DoD) 未绑定 Recorder 产出
- **现状**：`AGENTS.md` DoD 仅校验 `pytest`、`ruff` 与 `Reviewer APPROVED`。
- **缺口**：没有检查 `.harness/runs/Issue-XXXX/` 下的 `summary.json`、`timeline.md` 与 `runtime.log` 是否全部生成且大小 > 0。

---

## 3. 改进建议行动指南 (Remediation Plan)

1. **更新 Communication.md**：补充 Section 1.3 `Event Bus & Recorder Interceptors` 说明。
2. **更新 Lifecycle.md**：在序列图中为每个 Stage 增加 Recorder 的静默监听虚线指示。
3. **更新 Runtime.md**：在 Section 1 (Philosophy) 与 Section 4 (Agent Invocation) 中将 Recorder 显式定义为底层 Kernel 进程。
4. **更新 AGENTS.md**：在 DoD 门禁中增加 `8. Harness Recorder summary.json and timeline.md flushed successfully`。
5. **初始化物理目录**：创建物理目录 `g:\LLM_Learning\product\.harness\runs\` 并配置 `.gitignore`。
