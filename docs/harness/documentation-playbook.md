# Enterprise AI Harness - Documentation Agent Execution Playbook
> 企业级 AI 数字员工平台——Documentation Agent 实战操作手册与范例 (V1.0)

---

## 1. 实战演练范例 (Concrete Example)

### 1.1 接收到的 DECISION 审查通过入站消息体 (Inbound Message)

```json
{
  "message_id": "msg_dec_0885",
  "message_type": "DECISION",
  "sender": "ReviewerAgent",
  "receiver": "DocumentationAgent",
  "status": "Merged",
  "timestamp": "2026-07-22T02:10:00Z",
  "artifact": {
    "file_paths": ["backend/tools/erp_tools.py"],
    "git_commit": "a1b2c3d4",
    "diff_hash": "sha256:e3b0c44298..."
  },
  "payload": {
    "issue_id": "ISSUE-204",
    "decision": "APPROVED",
    "completed_checkpoints": ["Checkpoint 1: 实现 check_department_limit()"]
  }
}
```

---

### 1.2 Documentation Agent 执行的实战步骤日志

1. **导出 OpenAPI规格**：运行 `python workflow/scripts/dump_openapi.py`，更新 `docs/generated/openapi-spec.json`。
2. **Patch 计划文档**：使用 `md_patch_tool` 修改 [docs/plans/sprint-active.md](file:///g:/LLM_Learning/product/docs/plans/sprint-active.md)：
   - `[ ] Task 3: 实现 check_department_limit()` ──> `[x] Task 3: 实现 check_department_limit()`
3. **追加 CHANGELOG**：在 `CHANGELOG.md` 追加格式化日志：
   ```markdown
   ## [Unreleased] - 2026-07-22
   - Added: 支持 ERP 采购工具部门动态限额校验功能 (ISSUE-204)。
   ```
4. **向量存储增量重构 (Qdrant Re-Embedding)**：
   运行 `embedder_tool` 读取 `docs/plans/sprint-active.md` 与 `CHANGELOG.md`，重新分块生成 1024 维 BGE-M3 Embedding 并更新至 Qdrant `enterprise_knowledge` 集合。

---

### 1.3 投递给 Evaluator Agent 的出站消息体 (Outbound BENCHMARK Message)

```json
{
  "message_id": "msg_bm_0886",
  "message_type": "BENCHMARK",
  "sender": "DocumentationAgent",
  "receiver": "EvaluatorAgent",
  "status": "Running",
  "timestamp": "2026-07-22T02:12:00Z",
  "artifact": {
    "file_paths": ["docs/generated/openapi-spec.json", "CHANGELOG.md"],
    "git_commit": "a1b2c3d4",
    "diff_hash": null
  },
  "payload": {
    "issue_id": "ISSUE-204",
    "schema_updated": true,
    "vector_points_upserted": 6,
    "qdrant_collection": "enterprise_knowledge"
  }
}
```
