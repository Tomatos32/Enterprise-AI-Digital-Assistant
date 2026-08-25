# Active Sprint Execution Plan (Sprint 19 ~ 21 - Development Mode Campaign 1)
> Enterprise AI Digital Assistant - Active Task Checkpoint Board

---

## Active Issues: Issue-0026 ~ Issue-0028 (全量闭环交付)

### Task Checkpoints:
- [x] Checkpoint 1 (Issue-0026): 实现 `RoutingSession` 读写分离引擎与主从连接池优化 (`pool_size=100`, `max_overflow=50`, `pool_pre_ping=True`)
- [x] Checkpoint 2 (Issue-0026): 实现 Redis Sentinel 哨兵模式主从自动容灾切换与 Standalone 优雅回退
- [x] Checkpoint 3 (Issue-0026): 编写 100 并发读写混合压力测试脚本 `benchmark/stress_test.py` 与单元测试 `test_db_routing.py`
- [x] Checkpoint 4 (Issue-0027): 建立 `FeedbackRecord` 数据表模型与 `POST /api/v1/chat/feedback` 反馈收集接口
- [x] Checkpoint 5 (Issue-0027): 编写 `backend/scripts/extract_dpo_dataset.py` 实现 PII 隐私脱敏与标准 DPO 数据对抽取提炼
- [x] Checkpoint 6 (Issue-0027): 编写 `backend/tests/unit/test_feedback_dpo.py` 验证端到端反馈收集与 DPO 转换
- [x] Checkpoint 7 (Issue-0028): 增强 `benchmark/eval_ragas.py` 实现 `--strict-gate` 双阈值阻断与坏例分析 Markdown 报告
- [x] Checkpoint 8 (Issue-0028): 编写 GitHub Actions 工作流 `.github/workflows/eval_pipeline.yml`
- [x] Checkpoint 9 (Issue-0028): 编写 `backend/tests/unit/test_eval_gate.py` 验证门禁放行与阻断
- [x] Checkpoint 10: 刷盘 `.harness/runs/Issue-0026/`, `.harness/runs/Issue-0027/`, `.harness/runs/Issue-0028/` 全套 8 大证据包

---

## Sprint Overall Status
- Mode: `DEVELOPMENT MODE`
- Campaign: `战役一：生产级多模态、系统基线与深度知识增强`
- Active Issues: `Issue-0026`, `Issue-0027`, `Issue-0028` (ALL COMPLETED & CLOSED)
- Status: `CLOSED`
- Evidence Directories: `.harness/runs/Issue-0026/`, `.harness/runs/Issue-0027/`, `.harness/runs/Issue-0028/`
