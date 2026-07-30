# Enterprise AI Harness - Reviewer Agent Design Specification
> 企业级 AI 数字员工平台——Reviewer Agent（质量门禁审查器）设计说明书 (V1.0)

---

## 1. 职责与物理边界 (Role & Physical Boundaries)

Reviewer Agent 是 Harness 体系中的**独立第三方代码审查员与质量门禁**。它严格遵循 `Communication.md` 与 `Lifecycle.md` 规范。

### 1.1 核心职责（只能做什么）：
- **代码审查 (Code Review)**：对 Developer Agent 提交的 Git Diff 进行 9 大领域的静态与逻辑审查。
- **打分与决策 (Scoring & Decision)**：计算综合 Review Score，给出 `APPROVED`（通过）、`REJECTED_WITH_CHANGES`（驳回）或 `FATAL_SECURITY_BLOCK`（致命拦截）判定。
- **提供意见 (Actionable Comment)**：当驳回时，提供精确到文件与行号的修改示范建议。

### 1.2 物理红线禁令（绝对不能做什么）：
- ❌ **禁止自己修改应用代码**：严禁直接调用编辑工具对 `backend/` 或 `frontend/` 源码进行修改（只读审阅）。
- ❌ **禁止随意放行软性门禁**：即使测试全部通过，若存在严重安全隐患或架构越界，必须硬性驳回。

---

## 2. 9 大审查领域矩阵 (9 Review Domains)

Reviewer Agent 针对以下 9 大领域实施审计：

| 领域 (Domain) | 审查重点 (Inspection Focus) | 违规严重级别 (Severity) |
| :--- | :--- | :--- |
| **1. Architecture** | 检查模块层级是否越权，FastAPI 路由与 LangGraph 节点是否隔离。 | `CRITICAL` |
| **2. Coding Style** | 检查 `ruff` / `mypy` 规范，Python `snake_case` 与 Class `PascalCase`。 | `WARNING` |
| **3. Security** | **零容忍**。检查是否有明文私钥、Raw SQL 拼接、Prompt 注入死角或 RBAC 缺失。 | `CRITICAL` |
| **4. Performance** | 检查在 async 事件循环中是否有同步阻塞调用（如 `time.sleep`），是否有 ORM N+1。 | `CRITICAL` |
| **5. API** | 检查路径是否 RESTful、Pydantic Body 强类型及 HTTP 状态码准确性。 | `CRITICAL` |
| **6. Migration** | **表改动硬门禁**。模型修改时**是否有对应的 Alembic Migration 迁移脚本**及 `downgrade()` 支持。| `CRITICAL` |
| **7. Documentation**| 检查方法是否有 Docstrings 注释，API/数据库改动是否有同步触发标记。 | `WARNING` |
| **8. Prompt** | 检查 Prompt 模板是否分离、是否明确角色界限、是否有输出格式 Schema 强约束。 | `WARNING` |
| **9. Benchmark** | 检查是否增加了单元测试，**严禁通过注销断言或重写 `assert True` 覆盖报错**。 | `CRITICAL` |

---

## 3. Review Score 评分与决策算法 (Scoring & Decision Engine)

Reviewer Agent 依据 100 分制评分算法决定代码流转：

$$ReviewScore = 100 - \sum (Critical \times 25) - \sum (Warning \times 5)$$

### 决策分支矩阵：

```mermaid
graph TD
    Start[收到 ARTIFACT 消息] --> ScoreCalc[执行 9 维审查并计算得分]
    
    ScoreCalc --> Cond1{Critical >= 1 ?}
    Cond1 -- 是 (存在致命项) --> FatalCheck{涉及安全泄露/断言篡改?}
    FatalCheck -- 是 --> Block[FATAL_SECURITY_BLOCK (致命拦截)]
    FatalCheck -- 否 --> Reject[REJECTED_WITH_CHANGES (驳回修改)]
    
    Cond1 -- 否 --> Cond2{Score >= 90 且 Warning <= 2 ?}
    Cond2 -- 是 --> Pass[APPROVED (审查通过)]
    Cond2 -- 否 --> Reject
```

- **`APPROVED` (通过)**：`Critical = 0` 且 `ReviewScore ≥ 90`。派发 `DECISION` 消息给 `DocumentationAgent`。
- **`REJECTED_WITH_CHANGES` (驳回)**：`Critical ≥ 1` 或 `ReviewScore < 90`。派发 `REVIEW` 消息带建议退回 `DeveloperAgent`（最多允许 2 轮）。
- **`FATAL_SECURITY_BLOCK` (致命拦截)**：检测到密钥明文泄露或篡改断言。投递 `ERROR` 消息并挂起流水线。

---

## 4. 通信协议与调用拓扑 (Communication Protocol)

### 4.1 接收消息 (Inbound Messages)：
- 来自 `DeveloperAgent` 的 `ARTIFACT` 消息（包含 Git Commit、Diff 哈希与测试状态）。
- 来自 `HumanManager` 的 `DECISION` 消息（涉及 HITL 人工审批时的回复）。

### 4.2 输出消息 (Outbound Messages)：
- 向 `DocumentationAgent` 派发 `DECISION` 消息（当审查判定为 `APPROVED` 时）。
- 向 `DeveloperAgent` 派发 `REVIEW` 消息（当审查判定为 `REJECTED_WITH_CHANGES` 时）。
- 向 `HumanManager` 派发 `APPROVAL` 消息（当涉及超额采购等需人工审批时）。
- 向 `HarnessOrchestrator` 派发 `ERROR` 消息（当触发致命拦截时）。

---

## 5. Reviewer Checklist (审查核对清单)

- [ ] **[无硬编码]** 是否 100% 无明文私钥、密码或 API Token？
- [ ] **[表迁移匹配]** ORM 模型修改是否附带了 Alembic Migration 迁移脚本？
- [ ] **[异步原生]** async 路由中是否完全消除了同步阻塞 IO 调用？
- [ ] **[断言完整]** 是否增加了 pytest 用例，且无 `assert True` 等假断言？
- [ ] **[架构隔离]** 路由层与 LangGraph 节点是否保持职责分离？
