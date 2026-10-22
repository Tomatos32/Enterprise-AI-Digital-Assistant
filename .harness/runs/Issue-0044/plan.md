# Issue-0044: 实施方案与重构设计 (plan.md)

> **Sprint**：Sprint R-04  
> **设计人**：PlannerAgent / Architect  
> **时间**：2026-10-22T01:35:00Z  

---

## 1. 架构净化拓扑

```text
[用户输入 PromptBar]  -->  (已移除模型选择器，仅保留 @知识库 /指令 快捷键)
        │
        ▼ WebSocket
[generate_node / Ollama / Fallback]
        │
        ▼ 内部产生标准回答 (带/不带内部元数据标识)
[StreamingSanitizer & strip_internal_answer_tags]
        │ (彻底自动过滤 [Chat Answer]: / [RAG Answer]: 与 Hello! I have processed...)
        ▼
[前端 Vue3 MessageItem] --> 呈现 100% 自然优雅的中文流式回复与知识来源卡片
```

---

## 2. 实施矩阵

1. **前端组件修剪**：
   - 在 `PromptBar.vue` 中删除 `<GlideSelect>` 模板与所有 `modelOptions`，并在 `handleSend` 中解绑 `model` 字段。
2. **生成节点与兜底文本净化**：
   - 修正 `LocalEnterpriseChatModel`，改为纯正中文。
   - 增强 `generate_node.py` 防御，当 LLM 返回空时自动调用高质量业务领域合成。
3. **流式与完成帧前缀清洗**：
   - 在 `StreamingSanitizer.process_chunk` 和 `flush` 中增加前缀过滤；
   - 在 `chat_ws.py` 写入数据库与发送 complete 帧时调用 `strip_internal_answer_tags`。
