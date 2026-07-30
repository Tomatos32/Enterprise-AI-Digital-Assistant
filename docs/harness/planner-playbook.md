# Enterprise AI Harness - Planner Agent Execution Playbook
> 企业级 AI 数字员工平台——Planner Agent 实战操作手册与范例 (V1.0)

---

## 1. 场景标准操作规程 (SOPs)

### 场景 1：新增业务功能需求 (New Feature Request)
- **步骤 1**：解析 Issue 描述，读取 [AGENTS.md](file:///g:/LLM_Learning/product/AGENTS.md) 了解整体红线。
- **步骤 2**：使用 `grep_search` 定位现有的相关路由与模型（如搜索 `create_purchase`）。
- **步骤 3**：评估改动点。若涉及数据表新增字段，强制在计划中添加：“生成 Alembic 迁移脚本” Checkpoint。
- **步骤 4**：调用 `md_patch_tool` 更新 [docs/plans/sprint-active.md](file:///g:/LLM_Learning/product/docs/plans/sprint-active.md)。
- **步骤 5**：向消息总线投递发往 `DeveloperAgent` 的 `TASK` 消息。

---

## 2. 真实输入输出演练范例 (Concrete Example)

### 2.1 接收到的原始 Task 消息体 (Input JSON Message)

```json
{
  "message_id": "msg_task_0881",
  "message_type": "TASK",
  "sender": "HarnessOrchestrator",
  "receiver": "PlannerAgent",
  "status": "Pending",
  "timestamp": "2026-07-22T01:57:00Z",
  "artifact": {
    "file_paths": [],
    "git_commit": null,
    "diff_hash": null
  },
  "payload": {
    "issue_id": "ISSUE-204",
    "raw_issue_text": "需要为 ERP 采购工具添加部门采购限额动态校验功能。如果研发部采购总额超过 10,000 元，自动标记需要主管审批；如果是 HR 部超 5,000 元自动触发审批。"
  }
}
```

---

### 2.2 Planner Agent 内部推理与计划生成 (Generated Plan Output)

在检查完 `backend/tools/erp_tools.py` 与 `backend/models/domain.py` 之后，Planner 生成并写入 `docs/plans/sprint-active.md` 的内容如下：

```markdown
# Implementation Plan: [ISSUE-204] ERP 采购工具部门限额动态校验

## 1. Requirement & Context Summary
根据用户所属部门动态加载采购额度（研发部 >10000 元，HR 部 >5000 元），超额自动标记 `approval_needed=True` 并触发 HITL 审批。

## 2. Target File Impact Analysis
- [MODIFY] `backend/tools/erp_tools.py` (L40-L90): 增加 `check_department_limit()` 逻辑
- [NEW] `backend/tests/unit/test_department_limit.py`: 新增单元测试用例

## 3. Atomic Task Checkpoints
- [ ] Checkpoint 1: 在 `backend/tools/erp_tools.py` 中实现 `check_department_limit(department, amount)` 函数
- [ ] Checkpoint 2: 在 `create_purchase` 工具执行前嵌入限额校验逻辑
- [ ] Checkpoint 3: 在 `backend/tests/unit/test_department_limit.py` 中编写研发部超额与正常采购的 pytest 测试用例

## 4. Verification Criteria
- 运行 `pytest backend/tests/unit/test_department_limit.py` 全通过
- 运行 `ruff check backend/tools/erp_tools.py` 零 Warning
```

---

### 2.3 派发给 Developer Agent 的消息体 (Outbound Output Message)

```json
{
  "message_id": "msg_task_0882",
  "message_type": "TASK",
  "sender": "PlannerAgent",
  "receiver": "DeveloperAgent",
  "status": "Pending",
  "timestamp": "2026-07-22T01:57:15Z",
  "artifact": {
    "file_paths": ["backend/tools/erp_tools.py", "backend/tests/unit/test_department_limit.py"],
    "git_commit": null,
    "diff_hash": null
  },
  "payload": {
    "issue_id": "ISSUE-204",
    "plan_file": "docs/plans/sprint-active.md",
    "checkpoints": [
      "Checkpoint 1: 实现 check_department_limit()",
      "Checkpoint 2: 嵌入 create_purchase 工具校验",
      "Checkpoint 3: 编写 pytest 单元测试"
    ],
    "verification_cmd": "pytest backend/tests/unit/test_department_limit.py"
  }
}
```
