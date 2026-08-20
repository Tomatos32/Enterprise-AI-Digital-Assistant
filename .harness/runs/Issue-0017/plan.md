# Issue-0017 Execution Plan

> **Issue ID**: Issue-0017  
> **Title**: 实现 Sprint 10 “AI Infra 基础设施：Prompt Cache、Token Monitor 与 Fallback”  
> **Target DoD**: Ruff 0 Error, Pytest 100% Pass, Review Score ≥ 90  

---

## SDLC 9 Checkpoint Breakdown

- [ ] Checkpoint 1: 锁存需求至 `.harness/runs/Issue-0017/issue.md`
- [ ] Checkpoint 2: 生成 `.harness/runs/Issue-0017/plan.md` 并同步更新 `docs/plans/sprint-active.md`
- [ ] Checkpoint 3: 实现 `backend/core/llm_infra.py` 中的 `LLMGateway` (Prompt Hash Cache, Token Monitor & Cost Calculation, Fallback Strategy)
- [ ] Checkpoint 4: 编写 `backend/tests/unit/test_llm_infra.py` 并通过 Cache 命中、Token 监控与降级回退单元测试
- [ ] Checkpoint 5: 执行 `ruff check` 与 `pytest` 全量自动化单元测试 (100% Pass)
- [ ] Checkpoint 6: 完成 ReviewerAgent 11 维质量审查，生成 `review.md` (Score ≥ 90 / APPROVED)
- [ ] Checkpoint 7: 生成 `documentation.md` 与 `verification.md`
- [ ] Checkpoint 8: 刷盘 `.harness/runs/Issue-0017/` 8 大证据包，完成中文 feat Commit 并闭环关单
