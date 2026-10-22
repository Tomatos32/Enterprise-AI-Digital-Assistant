# Issue-0044: 前端输入框交互净化与无套话纯净流式生成 (issue.md)

> **Sprint**：Sprint R-04 (UI Simplification & Clean Streaming Generation)  
> **负责人**：Bootstrap Orchestrator / DeveloperAgent  
> **时间**：2026-10-22T01:30:00Z  
> **关联痛点**：用户反馈“输入框中并不需要选择模型的组件”以及“AI的流式回复中会参杂类似 `[Chat Answer]: Hello! I have processed your message: 'hi'. ` 这样的无效机械信息”。

---

## 1. 核心需求与背景

1. **输入框交互臃肿问题**：
   - 当前企业数字员工底座已统一定位，用户在日常业务提问时不需要在输入框中切换底层技术模型（如 Claude/GPT/o3-mini）。保留模型切换下拉框增加认知负担，需净化移除。
2. **回复文本存在生硬调试套话**：
   - 之前在 `LocalEnterpriseChatModel` 中硬编码了中英混杂语句 `Hello! I have processed your message: '{query}'.`，当用户提问时直接作为回答吐出，极其生硬且毫无业务意义。
   - `generate_node.py` 的 System Prompt 强加了格式要求（如要求首行标注 `[Chat Answer]:` 或 `[RAG Answer]:`），并在生成后拼接技术标签，导致流式推送直接向前端用户暴露出内部调试代号。

---

## 2. 交付与验收目标 (Definition of Done)

1. **前端输入框极简化 (`PromptBar.vue`)**：
   - 彻底移除 `GlideSelect` 模型选择组件及其选项配置；
   - 保留知识库关联 `@知识源` 与快捷指令 `/指令`，聚焦业务协同与问答，UI 极简纯粹。
2. **消除英文与技术标签套话 (`backend/core/llm.py` & `generate_node.py`)**：
   - 从 `LocalEnterpriseChatModel` 中永久移除 `Hello! I have processed your message: ...` 套话，替换为自然严谨的中文企业员工问候与引导。
   - 优化 `generate_node.py` 的 System Prompt，不再强求大模型输出技术前缀标签。
3. **流式传输与展示层脱敏 (`output_sanitizer.py` & `chat_ws.py`)**：
   - 在 `StreamingSanitizer` 与 WebSocket `complete` 帧发送层自动剥离 `[Chat Answer]: `、`[RAG Answer]: ` 等技术代号，确保推送到前端的文本 100% 干净自然，无任何调试痕迹。
   - 保证后端内部架构测试依然兼容通过。
