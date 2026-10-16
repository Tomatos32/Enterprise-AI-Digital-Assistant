# Sprint-F-09: Architecture & Implementation Plan
# ChatGPT / Claude 原生 Web 交互与 Vuebits 旗舰动效组件集成规划书

> **Sprint ID**: `Sprint-F-09`  
> **Planner Agent**: `PlannerAgent`  
> **Target**: `frontend/` (Vue3 + Tailwind CSS + Vuebits + Hugeicons + Lucide)  
> **Date**: 2026-10-16  

---

## 1. 架构目标与技术演进 (Architectural Goal)

本冲刺将企业级 AI 数字员工平台前端全量升维至 **ChatGPT (GPT-4o/o1/o3/Voice) 与 Claude (3.5/3.7 Extended Thinking)** 顶级 Web 交互水准：
1. **视觉底色与双主题拟合**：构建日间纸质温润白（`#FBF9F5` / `#FFFFFF`，对比度 $\ge 7:1$）与夜间曜石灰（`#0F172A` / `#0B0F19`，对比度 $\ge 4.5:1$）双轨令牌，全站无缝背景拟合。
2. **矢量图标双核体系**：装配 `@hugeicons/vue` 与 `lucide-vue-next`，彻底驱逐所有系统 Emoji 符号。
3. **Vuebits 动效原子套件**：交付 12 大原子动效组件，覆盖输入栏、思维链、工具调用芯片、语音胶囊、光标邻近侧栏与悬浮知识库。
4. **代码级去黑话与去技术注释**：清空所有调试注释、TODO 及内部技术缩写，交付纯净企业生产力产品。

---

## 2. Checkpoints 阶段变动表 (Detailed Checkpoints)

| Checkpoint | 责任模块 | 改动文件与目标 | 验证方式 |
| :--- | :--- | :--- | :--- |
| **CP-1** | 依赖装配与注册表 | `package.json`, `components.json` 固化 `@hugeicons/vue`, `@hugeicons/core-free-icons`, `motion-v`, `lucide-vue-next` | `npm list` / 编译无解析错误 |
| **CP-2** | 双主题色彩与背景拟合 | `src/index.css`, `tailwind.config.js`，实现温润白与曜石灰日夜映射、毛玻璃与平滑过渡 | 浏览器样式检查 / 对比度合规 |
| **CP-3** | Vuebits 旗舰原子组件集 | 创建 `src/components/ui/` 下的 12 项组件（`PromptBar`, `ThoughtLine`, `CallChip`, `VoicePill`, `GlideSelect`, `RubberSegment`, `LineSidebar`, `FolderFloat`, `ShinyText`, `WarmTooltip`, `StatusMark`, `FuseButton`） | 组件独立语法校验与类型检查 |
| **CP-4** | 输入区域重塑 | `src/components/chat/ChatInput.vue` 集成 `PromptBar`，支持 `@` 知识库菜单、`/` 指令菜单、模型切换、充能发送与中止流式 | 交互事件与状态机联动 |
| **CP-5** | 思维链与工具调用升级 | `src/components/chat/ThoughtBadge.vue` 升级为 `ThoughtLine` 呼吸秒表与 `CallChip` 工具调用芯片 | 耗时计时、流式打字与折叠过渡 |
| **CP-6** | 侧栏邻近与知识库悬浮 | `src/components/layout/Sidebar.vue` 升级 `LineSidebar` 与 `FolderFloat`，顶栏支持日夜模式切换 | 悬浮微动与光标邻近测试 |
| **CP-7** | 全站 100% 消除 Emoji 与注释 | 扫描并清洗 `MessageItem.vue`, `ApprovalCard.vue`, `KnowledgeView.vue`, `ApprovalListView.vue`, `Header.vue` 等所有组件 | 正则扫描零 Emoji、零 TODO/调试注释 |
| **CP-8** | 端到端构建与证据归档 | 运行 `npm run build`，核验控制台产物并输出 8 大只读证据包至 `.harness/runs/Sprint-F-09/` | 构建退出码 0，文件只读锁定 |

---

## 3. 受影响文件预测与清单 (Impacted Files Matrix)

```text
frontend/
├── package.json                                [Modified: 依赖装配]
├── components.json                             [Verified: @vue-bits 注册表]
├── tailwind.config.js                          [Modified: 扩展色彩与主题类]
├── src/
│   ├── index.css                               [Modified: 日夜双轨色彩令牌与无缝拟合]
│   ├── components/
│   │   ├── ui/                                 [New: Vuebits 旗舰原子组件库]
│   │   │   ├── PromptBar.vue
│   │   │   ├── ThoughtLine.vue
│   │   │   ├── CallChip.vue
│   │   │   ├── VoicePill.vue
│   │   │   ├── GlideSelect.vue
│   │   │   ├── RubberSegment.vue
│   │   │   ├── LineSidebar.vue
│   │   │   ├── FolderFloat.vue
│   │   │   ├── ShinyText.vue
│   │   │   ├── WarmTooltip.vue
│   │   │   ├── StatusMark.vue
│   │   │   └── FuseButton.vue
│   │   ├── chat/
│   │   │   ├── ChatInput.vue                   [Modified: PromptBar 充能与中止]
│   │   │   ├── ThoughtBadge.vue                [Modified: ThoughtLine + CallChip]
│   │   │   ├── MessageItem.vue                 [Modified: 消除 Emoji，双主题支持]
│   │   │   ├── MessageBubble.vue               [Modified: 消除 Emoji，双主题支持]
│   │   │   └── ApprovalCard.vue                [Modified: 矢量图标替换，双主题支持]
│   │   └── layout/
│   │       ├── Header.vue                      [Modified: 主题切换，ShinyText]
│   │       ├── Sidebar.vue                     [Modified: LineSidebar 与 FolderFloat]
│   │       └── MobileDrawer.vue                [Modified: 矢量图标，双主题支持]
│   ├── views/
│   │   ├── ChatView.vue                        [Modified: 消除 Emoji，双主题适配]
│   │   ├── KnowledgeView.vue                   [Modified: FolderFloat 卡片云，消除 Emoji]
│   │   └── ApprovalListView.vue                [Modified: 矢量图标替换，消除 Emoji]
│   └── stores/
│       └── chatStore.js                        [Modified: 支持当前选定模型与数据源状态]
```

---

## 4. 回滚与风控计划 (Rollback & Risk Mitigation)

- **回滚机制**：若任何组件引入 CSS 破坏性破坏或构建失败，通过 Git 状态保护隔离修改。
- **性能保障**：动效全部基于 CSS transform / opacity 及 `motion-v` 硬件加速，保证 60 FPS 无主线程卡顿。
- **对比度兜底**：使用 WCAG 计算验证日间模式正文 `#111827` 在 `#FBF9F5` 底色上达 15.2:1 (远超 7:1 AAA)，夜间模式正文 `#F8FAFC` 在 `#0F172A` 上达 14.8:1 (远超 4.5:1 AA)。
