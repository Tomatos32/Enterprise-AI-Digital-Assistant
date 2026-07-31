# Active Sprint Execution Plan (Sprint 1 & Sprint 2 Milestone)
> Enterprise AI Digital Assistant - Active Task Checkpoint Board

---

## Active Issue: Issue-0007 (Sprint 2 Vector & RAG File Upload API)

### Task Checkpoints:
- [x] Checkpoint 1: 锁存需求至 `.harness/runs/Issue-0007/issue.md`
- [x] Checkpoint 2: 重构 `backend/rag/vector_store.py`，增加 1024 维 BGE-M3 向量表示生成、`init_qdrant_collection`、`upsert_documents` 及 `search_similar_documents`
- [x] Checkpoint 3: 新增 FastAPI 接口 `backend/api/v1/knowledge.py` (`POST /api/v1/knowledge/upload`)，自动落地 `backend/data/` 目录并批量入库，并在 `backend/main.py` 注册 Router
- [x] Checkpoint 4: 编写 `backend/tests/unit/test_vector_store.py` 覆盖初始化、写入、检索与上传 API 测试
- [x] Checkpoint 5: 运行 `ruff check backend/ --fix` 与 `pytest backend/tests/` 确保 100% 零报错通过
- [x] Checkpoint 6: 生成 `.harness/runs/Issue-0007/` 下全套 9 大只读证据包

---

## Sprint Overall Status
- Mode: `BOOTSTRAP MODE`
- Active Issue: `Issue-0007`
- Status: `CLOSED`
- Evidence Directory: `.harness/runs/Issue-0007/`
