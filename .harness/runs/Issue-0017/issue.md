# Issue-0017 Target Context Lock

> **Issue ID**: Issue-0017  
> **Title**: 实现 Sprint 10 “AI Infra 基础设施：Prompt Cache、Token Monitor 与 Fallback”  
> **Operating Mode**: BOOTSTRAP MODE  
> **Python Environment**: `backend/.venv/Scripts/python.exe` (Python 3.11.0)  
> **Workspace Root**: `g:\LLM_Learning\product`  
> **Timestamp**: 2026-08-20T18:16:52+08:00  

---

## 1. Issue Background & Requirements (需求背景与要求)

1. **LLMGateway 类实现 (`backend/core/llm_infra.py`)**：
   - 实现 `LLMGateway` 类，作为统一的大语言模型基础设施调用网关。
2. **Prompt Hash Cache 逻辑 (Redis-based)**：
   - 基于 SHA-256 哈希计算 Prompt 的唯一 Key，并在 Redis 中进行缓存。
   - 重复 Prompt 请求直接命中缓存返回，避免重复模型调用与 Token 开销。
3. **Token Monitor 与成本计算中间件**：
   - 准确统计 Prompt Tokens 和 Completion Tokens 的数量及估算成本 (USD)。
   - 将开销与调用指标结构化记录至 Redis 哈希表 (`token_stats:summary`) 及统计日志清单中。
4. **模型降级与超时回退策略 (Model Fallback Strategy)**：
   - 支持主模型 (`primary_model`) 超时或抛出异常时自动 Try-Catch 平滑切换至备选/本地 vLLM 模型 (`fallback_model`)。
   - 响应元数据中明确记录 `fallback_triggered=True` 与 `primary_error` 信息。
5. **单元测试与质量门禁 (`backend/tests/unit/test_llm_infra.py`)**：
   - 编写 Prompt Cache 命中/未命中、Token 监控计算与主备降级回退单元测试。
   - 确保 `pytest` 100% 通过且 `ruff check` 零告警。
6. **沙盒证据包刷盘 (`.harness/runs/Issue-0017/`)**：
   - 刷盘 `issue.md`, `plan.md`, `developer.md`, `review.md`, `documentation.md`, `verification.md`, `summary.json`, `timeline.md`, `runtime.log` 9 大物理证据包，分 Issue 中文 commit 闭环。
