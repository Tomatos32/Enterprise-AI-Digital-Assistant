# Enterprise AI Harness - Reviewer Agent Execution Playbook
> 企业级 AI 数字员工平台——Reviewer Agent 实战操作手册与范例 (V1.0)

---

## 1. 评审决策演练 (Decision Scenarios)

### 场景 A：审查通过 (`APPROVED`)
- **判定条件**：9 大领域无任何 Critical 报错，测试全过，`ReviewScore` = 95。
- **动作**：投递 `DECISION` 消息发往 `DocumentationAgent` 触发自动合并与知识抽取。

### 场景 B：审查驳回 (`REJECTED_WITH_CHANGES`)
- **判定条件**：发现 1 处 async 事件循环中使用了同步 `time.sleep(2)`，`ReviewScore` = 70。
- **动作**：投递 `REVIEW` 消息带精确行号意见退回 `DeveloperAgent` 修正。

---

## 2. 真实演练范例 (Concrete Examples)

### 2.1 接收到的 ARTIFACT 消息体 (Input Message)

```json
{
  "message_id": "msg_art_0883",
  "message_type": "ARTIFACT",
  "sender": "DeveloperAgent",
  "receiver": "ReviewerAgent",
  "status": "Running",
  "timestamp": "2026-07-22T02:05:00Z",
  "artifact": {
    "file_paths": ["backend/api/v1/chat.py", "backend/tools/erp_tools.py"],
    "git_commit": "b2c3d4e5",
    "diff_hash": "sha256:7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a"
  },
  "payload": {
    "issue_id": "ISSUE-204",
    "local_test_summary": "3 passed in 0.12s"
  }
}
```

---

### 2.2 Reviewer Agent 审查报告 (Generated Review Comment)

```markdown
# 🔍 Code Review Report

**Review Status**: ❌ REJECTED_WITH_CHANGES
**Review Score**: 75 / 100
**Evaluated Commit**: `b2c3d4e5`

---

## 📊 Score Matrix
- Architecture: 10/10
- Coding Style: 8/10 (-2 missing typing)
- Security: 10/10
- Performance: 0/10 (-25 Critical: Blocking IO)
- Migration: 10/10 (No ORM change)
- Test Coverage: 10/10

---

## ⚠️ Detailed Feedback & Required Fixes

### 1. [PERFORMANCE] [CRITICAL] 发现同步阻塞事件循环
- **File**: `backend/api/v1/chat.py:L84`
- **Problem**: 调用了同步逻辑 `time.sleep(2)`，导致 FastAPI 单线程事件循环挂起。
- **Fix Suggestion**:
  ```python
  # BAD:
  time.sleep(2)

  # GOOD:
  await asyncio.sleep(2)
  ```

### 2. [CODING_STYLE] [WARNING] 类型标注缺失
- **File**: `backend/tools/erp_tools.py:L32`
- **Problem**: `check_department_limit` 参数缺少显式返回值标注。
- **Fix Suggestion**:
  ```python
  def check_department_limit(department: str, amount: float) -> bool:
  ```
```

---

### 2.3 投递给 Developer Agent 的驳回出站消息体 (Outbound REVIEW Message)

```json
{
  "message_id": "msg_rev_0884",
  "message_type": "REVIEW",
  "sender": "ReviewerAgent",
  "receiver": "DeveloperAgent",
  "status": "Rejected",
  "timestamp": "2026-07-22T02:08:30Z",
  "artifact": {
    "file_paths": ["backend/api/v1/chat.py", "backend/tools/erp_tools.py"],
    "git_commit": "b2c3d4e5",
    "diff_hash": "sha256:7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a"
  },
  "payload": {
    "decision": "REJECTED_WITH_CHANGES",
    "review_score": 75,
    "feedbacks": [
      {
        "file": "backend/api/v1/chat.py",
        "line": 84,
        "domain": "Performance",
        "severity": "CRITICAL",
        "issue": "使用了同步 time.sleep(2) 阻塞了 async 事件循环",
        "suggestion": "请修改为 await asyncio.sleep(2)"
      },
      {
        "file": "backend/tools/erp_tools.py",
        "line": 32,
        "domain": "Coding Style",
        "severity": "WARNING",
        "issue": "缺少返回值 -> bool 类型标注",
        "suggestion": "添加 -> bool 类型标注"
      }
    ]
  }
}
```
