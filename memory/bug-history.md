# Bug History & Regression Lessons
> 历史 Bug 排错库与回归测试模式 (Post-Mortem Log)

---

## 1. 经验教训规范 (Log Template)

每当在开发、联调或 CI 测试阶段发现严重 Bug 并修复后，AI Agent 或人类开发者需按照以下格式在此更新记录：

```markdown
### [BUG-000x] 简要标题

- **现象描述**: 错误表现与堆栈日志。
- **根本原因 (Root Cause)**: 导致问题的代码底层缺陷。
- **解决方案**: 采用的修复手段。
- **防范措施**: 对应的规则约束或新增的回归测试用例。
```

---

## 2. 历史模式案例库

### [BUG-0001] FastAPI 主事件循环中调用同步依赖造成长连接卡死
- **现象描述**: 高并发 WebSocket 会话在大模型推理阶段发生丢包和响应停滞。
- **根本原因**: 在 Router 内部直接调用了同步库函数的阻塞式文件 IO 操作，导致 Python 单线程 Event Loop 挂起。
- **解决方案**: 改为使用 `aiofiles` 异步文件接口，长耗时图像解析剥离至 Celery Worker。
- **防范措施**: `AGENTS.md` 明确规定：禁止在 FastAPI 主事件循环中执行同步阻塞 IO。

### [BUG-0002] LangGraph 恢复时丢失 `approval_status` 状态
- **现象描述**: 主管点击同意后唤醒状态机，ToolExecutor 节点依然认为需要审批，发生二次拦截死循环。
- **根本原因**: 唤醒时使用了无状态 `app.stream()` 覆盖了原本的 `thread_id` 状态。
- **解决方案**: 统一使用 `app.update_state()` 显式合并 `{"approval_status": "APPROVED", "approval_needed": False}` 并重新关联原有的 `thread_id`。
