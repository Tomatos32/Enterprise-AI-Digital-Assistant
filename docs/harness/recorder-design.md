# Enterprise AI Harness - Harness Recorder Architecture Specification
> 企业级 AI 数字员工平台——Harness Recorder (运行记录器) 设计说明书 (V1.0)

---

## 1. 定位与哲学 (Positioning & Philosophy)

Harness Recorder **不是一个 Agent**，它不消耗大模型 Token，不参与业务逻辑决策或代码修改。

它属于 **Harness Runtime 内核的核心底层监控设施 (Infrastructure Component)**。它以无侵入（Non-invasive）的方式挂载在 Agent 通信总线（Message Bus）与工具调用拦截器（Tool Interceptor）上，对所有 Agent 的行为、消息传递、物理交付物、思考链及控制台输出进行**毫秒级无盲区留痕**。

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Harness Runtime Kernel                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Harness Recorder Engine                       │  │
│  │  (Event Bus Listener | Tool Interceptor | Artifact Synchronizer) │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
└────────────────────────────────────┼───────────────────────────────────┘
                                     │ Non-invasive Observation
    ┌────────────────────────────────┼────────────────────────────────┐
    ▼                                ▼                                ▼
[Message Traffic]           [Tool Execution & Log]           [Physical Artifacts]
- TASK, ARTIFACT, DECISION  - view_file, run_command         - plan.md, review.md
- REVIEW, DEPLOY, ERROR     - pytest stdout/stderr           - openapi.json, diff
```

---

## 2. 启动与结束生命周期 (Lifecycle Triggers)

### 2.1 启动时机 (Start Trigger)
当 `HarnessOrchestrator` 或 `BootstrapOrchestrator` 收到新 Issue，在 `.harness/runs/` 下建立隔离沙盒目录 `Issue-XXXX/` 的瞬间，Recorder 引擎自动启动，初始化事件缓冲区并绑定该 `Run ID`。

### 2.2 结束时机 (End Trigger)
当 Issue 经历所有 SDLC 阶段并达到 `Closed`（成功结案）、`REJECTED` 或 `FATAL_ERROR`（致命拦截）状态时，Recorder 触发刷盘机制（Flush & Sync），生成 `summary.json`、`timeline.md` 与 `runtime.log` 物理文件，随后优雅关闭事件监听。

---

## 3. 记录内容全景图 (What to Record)

Harness Recorder 涵盖 4 大维度的无盲区记录：

| 记录维度 (Dimension) | 捕获的具体数据内容 (Captured Content) | 数据来源 (Data Source) |
| :--- | :--- | :--- |
| **1. Agent Thought & Action**| System Prompt 结构、Thought 思考链、工具调用的方法名、入参 JSON、返回值及 stdout/stderr。 | Tool Interceptor & Agent Adapter |
| **2. Communication Messages**| 遵守 `Communication.md` 协议的全部 9 种 Message JSON 体（`TASK`, `ARTIFACT`, `DECISION`, `REVIEW`, `BENCHMARK`, `DEPLOY`, `APPROVAL`, `ERROR`, `RETRY`）。 | Event Bus / Message Broker |
| **3. Physical Artifacts** | Git Commit Patch (`git_diff.patch`)、Alembic SQL、OpenAPI `openapi-spec.json` 及 7 大 Agent 报告。 | Artifact Synchronizer |
| **4. Telemetry & Cost** | 节点耗时 (Duration)、Input/Output Tokens、模型 ID (Model ID) 及 USD 开销折算。 | LLM Gateway / Token Counter |

---

## 4. 自动生成的 3 大最终交付物 (Deliverables)

单次 Issue 运行结束后，Recorder 自动在 `.harness/runs/Issue-XXXX/` 刷盘生成以下 3 个标准证据文件：

### 4.1 `summary.json` (机器可读控制总表)

汇聚全生命周期的结构化数据，供 CI/CD 流水线与可视化看板解析：

```json
{
  "run_id": "run_20260722_09812",
  "issue_id": "ISSUE-0001",
  "mode": "BOOTSTRAP",
  "status": "CLOSED",
  "start_time": "2026-07-22T02:00:00.120Z",
  "end_time": "2026-07-22T02:15:30.450Z",
  "total_duration_seconds": 930.33,
  "telemetry": {
    "total_tokens_consumed": 38450,
    "input_tokens": 31200,
    "output_tokens": 7250,
    "estimated_cost_usd": 0.0115
  },
  "agent_timeline": [
    {
      "agent": "PlannerAgent",
      "status": "SUCCESS",
      "duration_seconds": 120.5,
      "artifact_generated": "docs/plans/plan.md"
    },
    {
      "agent": "DeveloperAgent",
      "status": "SUCCESS",
      "duration_seconds": 450.2,
      "artifact_generated": "docs/harness/reports/developer.md"
    },
    {
      "agent": "ReviewerAgent",
      "status": "APPROVED",
      "review_score": 95,
      "duration_seconds": 180.0,
      "artifact_generated": "docs/harness/reports/review.md"
    },
    {
      "agent": "DocumentationAgent",
      "status": "SUCCESS",
      "duration_seconds": 179.6,
      "artifact_generated": "docs/harness/reports/documentation.md"
    }
  ]
}
```

---

### 4.2 `timeline.md` (人类可读时间轴报告)

以直观的 Markdown 格式生成按时间排布的事件与状态转移图：

```markdown
# ⏱️ Harness Runtime Timeline Report

**Issue ID**: `ISSUE-0001`  
**Run ID**: `run_20260722_09812`  
**Execution Mode**: `BOOTSTRAP`  
**Final Status**: ✅ `CLOSED`  

---

## 📅 Timeline Events

```text
[02:00:00] 🚀 Issue Received -> Harness Orchestrator initialized sandbox `.harness/runs/Issue-0001/`.
[02:00:05] 📥 Inbound Message: TASK -> PlannerAgent invoked.
[02:02:05] 📄 Artifact Created: `plan.md` -> 4 Checkpoints generated.
[02:02:10] 📤 Outbound Message: TASK -> DeveloperAgent invoked.
[02:09:40] ⚙️ Tool Execution: `pytest backend/tests/` -> 100% PASSED (3/3).
[02:09:45] 📄 Artifact Created: `developer.md` -> Git Commit `a1b2c3d4`.
[02:09:50] 📤 Outbound Message: ARTIFACT -> ReviewerAgent invoked.
[02:12:50] 🔍 Code Review: ReviewScore 95/100 -> Status APPROVED.
[02:12:55] 📄 Artifact Created: `review.md`.
[02:13:00] 📤 Outbound Message: DECISION(APPROVED) -> DocumentationAgent invoked.
[02:15:25] 📚 Schema Export: `openapi-spec.json` updated, 6 Qdrant points upserted.
[02:15:30] ✅ Issue Closed -> Final summary.json & timeline.md flushed cleanly.
```
```

---

### 4.3 `runtime.log` (全量控制台与思考链日志)

保持未截断的原始日志流，记载 Thought 链条、Tool 命令明细及命令输出：

```text
2026-07-22T02:00:05.123Z [INFO] [PlannerAgent] Processing Inbound TASK: ISSUE-0001 (FastAPI Scaffold)
2026-07-22T02:00:10.456Z [THOUGHT] [PlannerAgent] Reading BOOTSTRAP.md and Architecture.md to construct minimal scope...
2026-07-22T02:02:05.789Z [ARTIFACT] [PlannerAgent] Written plan.md (Length: 1420 bytes).
2026-07-22T02:02:10.012Z [MSG_BUS] Emitted TASK message to DeveloperAgent.
2026-07-22T02:09:40.111Z [TOOL_RUN] Executing command: `pytest backend/tests/`
2026-07-22T02:09:44.888Z [TOOL_STDOUT] ===== 3 passed in 0.45s =====
2026-07-22T02:12:50.333Z [DECISION] ReviewerAgent decision: APPROVED (Score: 95).
2026-07-22T02:15:30.450Z [SYSTEM] Recorder flushed logs successfully. Thread closed.
```
