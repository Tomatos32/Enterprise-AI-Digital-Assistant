# Issue-0046: Ollama 思考链真实透传、ThoughtLine 动效规范化重塑与发送状态解闭锁 (issue.md)

> **Sprint**：Sprint R-04 / Sprint F-09 Sub-branch  
> **负责人**：Bootstrap Orchestrator / DeveloperAgent  
> **时间**：2026-10-26T09:00:00Z  
> **关联原始任务**：`Sprint-F-09` Checkpoint 5（ThoughtLine 呼吸秒表与收拢折叠）& `Issue-0041`（输入框流式死锁）  
> **关联痛点**：
> 1. 思考链模块在任何会话下总是显示固定的采购意图分析 4 步与固定的 ERP 库存工具调用卡片；
> 2. 思考结束给出答复后，思考时间显示硬编码的“1.8秒”；
> 3. 思考链下方无论提问什么都会硬编码回显两篇采购制度引用卡片；
> 4. 对话结束后，发送按钮未能及时复位回箭头，仍保持为暂停方块，导致用户被迫点击从而触发了此前的 abort 异常；
> 5. 期望将本地 Ollama 的原生思考链条（Reasoning Content）真实透传回显，并将 `<ThoughtLine />` 组件严格对齐 Vue Bits 官方规范（TypeScript + Tailwind + `@hugeicons/core-free-icons`）。

---

## 1. 核心根因分析 (Root Causes)

1. **硬编码伪数据未割接** (`ThoughtBadge.vue`)：
   - 之前在开发 UI 演示阶段，`ThoughtBadge.vue` 内部硬编码了 `calculatedDuration = computed(() => 1.8)`、`defaultSampleSources`（固定采购制度）以及 4 条写死的采购意图步骤；当没有传入真实数据时，页面直接 fallback 到这组死数据。
2. **WebSocket 终态判定漏洞导致发送按钮死锁** (`useChatStream.js`)：
   - `handleWsEvent` 开头使用了守卫 `if (!currentMsg || currentMsg.completed) return;`；当消息状态已被提前置为 completed 时，收到的 `complete` 事件被跳过，导致 `isStreaming.value = false` 未被执行。
   - 输入框因此一直保持在 `isStreaming === true` 状态，按钮维持为黑色停止方块，用户被迫点击停止按钮，从而向后端触发了 `POST /api/v1/chat/abort`。
3. **Ollama 思考流与前端解耦** (`chat_ws.py` & `llm.py`)：
   - Ollama (Qwen) 产生的思考内容位于 SSE 的 `reasoning` 字段中，此前仅转发了 `content`，未将思考过程作为独立的 `thought` 帧透传给前端。

---

## 2. 交付与验收目标 (Definition of Done)

1. **官方 Vue Bits `<ThoughtLine />` 规范重塑** (`ThoughtLine.vue`)：
   - 基于官方规范（`TypeScript + Tailwind + @hugeicons/core-free-icons + motion-v`）完成组件实现；
   - 包含流式呼吸微动（breathing shimmer）、实时打表时钟（tabular-nums live timer）、平滑模糊折叠（blur settle）与展开推理全文支持。
2. **彻底消灭所有硬编码内容** (`ThoughtBadge.vue` & `MessageItem.vue`)：
   - 彻底删除 1.8 秒硬编码，改为根据从提问到首字吐出动态计算真实思考秒数；
   - 彻底删除写死的采购制度与 4 条模拟步骤，真实有检索依据才展示卡片，普通对话保持清爽；
   - 彻底删除写死的工具调用卡片，仅在真实触发 Tool 时动态渲染。
3. **发送按钮状态即时复位** (`useChatStream.js`)：
   - 终态事件（`complete`, `cancelled`, `error`, `interrupt`）无条件强制执行 `isStreaming.value = false; activeNodes.value = [];`；
   - 确保生成一结束，发送按钮瞬间无缝切回向上箭头，绝不再卡在停止方块。
4. **Ollama 真实思考链流式透传** (`chat_ws.py` & `useChatStream.js`)：
   - 后端识别并透传 `thought` 事件，前端实时累加至 `currentMsg.thought`，并可在 `ThoughtLine` 展开后查看完整大模型推理思路。
