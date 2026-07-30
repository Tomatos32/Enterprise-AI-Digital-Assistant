# Enterprise AI Harness - Developer Agent Execution Playbook
> 企业级 AI 数字员工平台——Developer Agent 实战操作手册与范例 (V1.0)

---

## 1. 标准操作规程 (SOPs)

### 1.1 增量功能开发与数据库迁移流 (Feature & Migration Flow)
1. **解析 Task 消息**：提取入参 `TASK` 消息体中的 Checkpoints 清单与目标文件。
2. **检索符号约束**：使用 `grep_search` 查看待修改类的导入与定义。
3. **编辑应用源码**：使用 `replace_file_content` 进行局部行修改。
4. **生成数据库迁移**：若修改了 `backend/models/domain.py`，执行命令：
   `alembic revision --autogenerate -m "add_department_limit_field"`
5. **编写 pytest 测试**：在 `backend/tests/unit/` 下创建或补充 `test_*.py`，添加正常与边界情况断言。
6. **运行本地三连自测**：
   - `ruff check backend/`
   - `mypy backend/`
   - `pytest backend/tests/unit/`
7. **投递 ARTIFACT 消息**：打包 Git Commit 与哈希，向 `ReviewerAgent` 发送消息。

---

## 2. 真实演练范例 (Concrete Example)

### 2.1 接收到的 TASK 入站消息体 (Inbound TASK Message)

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

---

### 2.2 Developer Agent 代码编写与修改

#### 代码修改 (`backend/tools/erp_tools.py`):
```python
# 修改 backend/tools/erp_tools.py 增加限额函数
DEPARTMENT_PURCHASE_LIMITS = {
    "R&D": 10000.0,
    "HR": 5000.0,
    "DEFAULT": 2000.0
}

def check_department_limit(department: str, amount: float) -> bool:
    """校验采购金额是否超过该部门免审额度"""
    limit = DEPARTMENT_PURCHASE_LIMITS.get(department, DEPARTMENT_PURCHASE_LIMITS["DEFAULT"])
    return amount > limit
```

#### 单元测试补充 (`backend/tests/unit/test_department_limit.py`):
```python
import pytest
from backend.tools.erp_tools import check_department_limit

def test_rd_department_limit_exceeded():
    assert check_department_limit("R&D", 12000.0) is True

def test_rd_department_limit_within():
    assert check_department_limit("R&D", 8000.0) is False

def test_hr_department_limit_exceeded():
    assert check_department_limit("HR", 6000.0) is True
```

---

### 2.3 本地自测与命令行执行 (Verification)

```bash
# 1. 语法与代码风格校验
ruff check backend/tools/erp_tools.py

# 2. 静态类型校验
mypy backend/tools/erp_tools.py

# 3. 运行单元测试
pytest backend/tests/unit/test_department_limit.py
```
*自测结果：100% 通过（`3 passed in 0.12s`）。*

---

### 2.4 投递给 Reviewer Agent 的 ARTIFACT 出站消息体 (Outbound Message)

```json
{
  "message_id": "msg_art_0883",
  "message_type": "ARTIFACT",
  "sender": "DeveloperAgent",
  "receiver": "ReviewerAgent",
  "status": "Running",
  "timestamp": "2026-07-22T02:05:00Z",
  "artifact": {
    "file_paths": ["backend/tools/erp_tools.py", "backend/tests/unit/test_department_limit.py"],
    "git_commit": "b2c3d4e5",
    "diff_hash": "sha256:7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a"
  },
  "payload": {
    "issue_id": "ISSUE-204",
    "completed_checkpoints": [
      "Checkpoint 1: 实现 check_department_limit()",
      "Checkpoint 2: 嵌入 create_purchase 工具校验",
      "Checkpoint 3: 编写 pytest 单元测试"
    ],
    "local_test_summary": "3 passed in 0.12s",
    "ruff_status": "PASSED",
    "mypy_status": "PASSED",
    "alembic_migration_created": false
  }
}
```
