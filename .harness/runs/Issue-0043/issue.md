# Issue-0043: 本地大模型代理穿透直连修复与端到端真实推理闭环 (issue.md)

> **Sprint**：Sprint R-04 (Real Model Connectivity & Zero-Proxy Loopback)  
> **负责人**：Bootstrap Orchestrator / DeveloperAgent  
> **时间**：2026-10-22T01:00:00Z  
> **关联痛点**：用户实测反馈“Ollama 已经启动，但在提问时后台抛出 `[LLM] Primary ChatModel _astream failed: Error code: 502. Falling back to LocalEnterpriseChatModel`，大模型连接失败”。

---

## 1. 核心根因分析 (Root Cause)

经过系统级网络与环境审计，定位到根本原因如下：
1. **Windows 本地代理软件（Clash / V2Ray）拦截了回环请求**：
   - 机器开启了 Windows 系统代理（`127.0.0.1:7897`）。
   - Python `httpx`（底层 `openai` SDK 与 `langchain_openai` 客户端依赖的 HTTP 驱动）默认配置 `trust_env=True`，会自动读取 Windows 系统代理。
   - 当后端向 `http://localhost:11434/v1` 或 `http://127.0.0.1:11434/v1` 发起大模型推理请求时，请求被系统代理客户端拦截，而代理客户端对本地端口转发失败，直接返回了 **502 Bad Gateway**！
2. **LangChain BaseChatModel 内部流式聚合缺陷**：
   - 在 `ResilientChatModel` 的 `_agenerate` 内部直接调用了底层私有方法 `_agenerate`，当 `streaming=True` 时底层返回未消耗的 `AsyncStream`，抛出 `'AsyncStream' object has no attribute 'model_dump'`，进一步加剧了降级异常。

---

## 2. 交付与验收目标 (Definition of Done)

1. **禁用本地系统代理继承 (`trust_env=False`)** (`backend/core/llm.py`)：
   - 检测本地回环地址（`127.0.0.1`, `localhost`），显式构造 `httpx.AsyncClient(trust_env=False)` 与 `httpx.Client(trust_env=False)` 并注入 `ChatOpenAI`。
   - 将 `effective_base` 中的 `localhost` 统一规范化为 `127.0.0.1`，杜绝 Windows IPv6 (`::1`) 解析异常与代理拦截。
2. **重构 `ResilientChatModel` 容灾方法** (`backend/core/llm.py`)：
   - `_generate` 与 `_agenerate` 改用标准的 `invoke` / `ainvoke` 接口，安全包装单轮响应。
   - `_astream` 支持逐 token 安全 yield，当真实模型输出时直连推送，异常时自动平滑回退。
3. **真实推理闭环验证**：
   - 真实连通本地运行的 Ollama `qwen3.5:2b` 模型，端到端返回自然高质量回答，彻底消除 502 错误。
