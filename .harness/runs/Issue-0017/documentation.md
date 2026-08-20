# Documentation Agent Sync Report (Issue-0017)

> **Issue ID**: Issue-0017  
> **Title**: 实现 Sprint 10 “AI Infra 基础设施：Prompt Cache、Token Monitor 与 Fallback”  
> **Sync Status**: `COMPLETED`  

---

## 1. Documentation & Architecture Updates

### New Core Module: `LLMGateway` (`backend/core/llm_infra.py`)
- **API Spec**:
  - `LLMGateway(redis_client, primary_model_name, fallback_model_name, default_timeout, cache_ttl)`
  - `async generate_response(prompt, primary_func, fallback_func, timeout, use_cache) -> dict`
  - `async get_token_stats() -> dict`
  - `async get_cached_response(prompt, model_name) -> dict | None`
  - `async set_cached_response(prompt, model_name, response_data, ttl) -> bool`

---

## 2. Redis Key Topology

| Key Pattern | Type | Purpose | TTL |
| :--- | :--- | :--- | :--- |
| `prompt_cache:{sha256_hash}` | `String (JSON)` | 存储 LLM 生成响应以加速二次请求 | Default: 3600s |
| `token_stats:summary` | `Hash` | 记录 `total_prompt_tokens`, `total_completion_tokens`, `total_cost`, `total_calls` | Permanent |
| `token_stats:logs` | `List (JSON)` | 细粒度单次调用开销日志列表 | Permanent |

---

## 3. Schema & OpenAPI Sync Status
- 本 Issue 为基础设施 Core 网关层改造，未变更 HTTP REST OpenAPI Schema，公共 API 端点无破坏性调整。
