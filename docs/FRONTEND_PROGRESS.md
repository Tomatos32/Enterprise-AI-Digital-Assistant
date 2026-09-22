# Enterprise AI Digital Assistant - 前端现代化与 ChatGPT/Gemini 范式重构全景背书白皮书

> **项目名称**：企业级 AI 数字员工平台 - 现代化终端体验重塑与 Copilot 架构升级  
> **当前运行模式**：**FRONTEND MODERNIZATION MODE (前端工程演进与体验重构模式 · 规划就绪)**  
> **设计范式标准**：**ChatGPT / Gemini 极简沉浸式 Web 范式 + UI/UX Pro Max 企业级生产力标准**  
> **基准规范**：[docs/PROJECT_PROGRESS.md](file:///g:/LLM_Learning/product/docs/PROJECT_PROGRESS.md) · [docs/SPEC.MD](file:///g:/LLM_Learning/product/docs/SPEC.MD) · [AGENTS.md](file:///g:/LLM_Learning/product/AGENTS.md) · `ui-ux-pro-max`  
> **系统最后更新**：2026-09-23  

---

## 1. 全局进度与阶段规划全景看板 (Master Frontend Progress Dashboard)

```text
====================================================================================================
[PHASE 1: 基础骨架与设计系统]   ████████████████████████████████ 100% (Sprint F-01 & F-02 全部闭环)
[PHASE 2: 流式对话与自然思考]   ████████████████████████████████ 100% (Sprint F-03 & F-04 全部闭环)
[PHASE 3: 业务协同与待办中心]   ████████████████████████████████ 100% (Sprint F-05 & F-06 全部闭环)
[PHASE 4: 多端响应与硬化验收]   ████████████████████████████████ 100% (Sprint F-07 & F-08 全部闭环)
====================================================================================================
```

| 治理维度 | 当前基线状态 | 目标形态与合规标准 (ChatGPT/Gemini 范式) |
| :--- | :--- | :--- |
| **视觉与交互范式** | 单页调试态 (乱套、混杂开发黑话) | **极简沉浸式 Copilot 工作台 (类 ChatGPT / Gemini Web 架构)** |
| **开发术语脱敏** | 存在 `[WS状态]`、`TTFT`、`熔断器`、`节点代号` | **100% 抹除技术术语**，转化为自然人机语言与折叠知识胶囊 |
| **设计系统 (Design System)**| 硬编码深色样式，缺乏原子规范 | **基于 `ui-ux-pro-max` Slate-950 + 科技微光 + WCAG AA 调色板** |
| **图标与视觉元素** | 混用 Emoji (`💡`, `⚠️`, `⚙️`) | **100% 采用 Lucide 矢量 SVG 规范图标 (24x24 viewBox)** |
| **会话与状态管理** | 单一硬编码会话，不可切换 | **Pinia 集中化会话仓储，支持历史会话分组 (今天/昨天/前7天)** |
| **人机审批交互** | 原始 JSON 状态机拦截卡片 | **现代化企业审批协同凭据卡 (一键同意/驳回，直观审批流)** |
| **知识检索呈现** | 仅内部 Log 打印 | **Gemini 风格折叠小胶囊 (例: "⚡ 已核对 3 篇企业制度 · 展开来源")** |
| **端到端体验质量** | 输入卡顿、缺乏打字光标柔化 | **悬浮胶囊输入框、自适应高度、平滑打字光标、零布局抖动** |

---

## 2. 范式转换核准矩阵与“去开发化”规范 (Paradigm Shift & De-Jargon Rules)

依据用户明确要求，本重构计划严格确立 **“面向最终业务用户 (End-User Centric)”** 的铁律，所有界面元素执行如下映射转换：

```mermaid
graph TD
    subgraph Raw_Dev_Elements [原始开发与调试黑话 (彻底移除)]
        D1["[WS已连接] / [断开] 状态徽章"]
        D2["TTFT: 182ms / Tokens: 1,420"]
        D3["● ROUTER ● TOOL ● APPROVAL"]
        D4["LangGraph interrupt() 状态机挂起"]
        D5["熔断器: CLOSED / HALF_OPEN"]
        D6["ID: thread_ws_982312 会话流水号"]
    end

    subgraph User_Centric_Transform [ChatGPT / Gemini 范式转换引擎]
        T1["网络异常静默重试 / 仅断网时顶部极细通知条"]
        T2["后台静默追踪 / 用户界面零干扰"]
        T3["自然语言折叠胶囊: '已检索知识库与ERP库存'"]
        T4["企业审批协同卡: '需要主管审批确认'"]
        T5["自然降级话术: '系统繁忙，已为您转入离线工单'"]
        T6["智能自然标题: '2026 Q3 研发设备采购咨询'"]
    end

    subgraph Clean_UI_Experience [终端用户高品质体验]
        U1["干净无干扰的画布"]
        U2["高可读性 Markdown 流"]
        U3["直观高效的单据审批"]
    end

    D1 -.-> T1 --> U1
    D2 -.-> T2 --> U1
    D3 -.-> T3 --> U2
    D4 -.-> T4 --> U3
    D5 -.-> T5 --> U2
    D6 -.-> T6 --> U1
```

---

## 3. 架构蓝图与视口布局规范 (Layout Architecture & Wireframe)

界面严格遵循类似 **ChatGPT / Google Gemini** 的现代三段式弹性结构：

```text
┌─────────────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
│  企业数字员工   │  [智能助手模式 ▼]  企业通用助手 (已接入企业内网知识库)                         [新建对话] [头像] │
├─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
│                 │                                                                                         │
│ [+ 新建对话]   │                                                                                         │
│                 │   👤 研发部 - 李工:                                                                     │
│ 【近期会话】    │   请帮我申请采购 1 台高配开发机 MacBook Pro 16，单价 22,999 元。                         │
│ 💬 设备采购申请  │                                                                                         │
│ 💬 IT网络故障排查│   -----------------------------------------------------------------------------------   │
│ 💬 员工入职指引  │                                                                                         │
│                 │   ✨ 数字员工助手:                                                                      │
│ 【我的协同】    │                                                                                         │
│ 📋 待我审批 (1) │   ┌ ⚡ 已参考《企业固定资产管理规章》并核对研发部硬件预算标准   [展开查看制度来源 ▼] ┐    │
│ 📚 规章制度检索 │   └───────────────────────────────────────────────────────────────────────────────┘     │
│                 │                                                                                         │
│                 │   已为您核对制度并生成设备采购申请单。依据公司财务制度，金额大于 ￥5,000 元需提交审批：   │
│                 │                                                                                         │
│                 │   ┌─────────────────────────────────────────────────────────────────────────┐           │
│                 │   │ 📋 大额采购审批确认单                                      单号: PR-20260922-01 │           │
│                 │   ├─────────────────────────────────────────────────────────────────────────┤           │
│                 │   │ • 申请物品: MacBook Pro 16 英寸 (M-Series)                              │           │
│                 │   │ • 采购总额: ￥22,999.00           • 申请部门: 研发部                      │           │
│                 │   │ • 申请事由: AI 数字人高算力本地调试与模型训练需求                       │           │
│                 │   ├─────────────────────────────────────────────────────────────────────────┤           │
│                 │   │ [输入审批批注意见 (可选)...                                           ] │           │
│                 │   │                                       [ 驳回申请 ]   [ 同意并提交采购 ] │           │
│                 │   └─────────────────────────────────────────────────────────────────────────┘           │
│                 │                                                                                         │
├─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
│ ⚙️ 系统偏好     │                 ┌───────────────────────────────────────────────────┐                   │
│ 👤 张经理 (研发)│                 │ 💭 发送消息给企业数字员工... (支持 Shift+Enter 换行)│ [⬆ 发送]          │
│ [◀ 收起侧边栏]  │                 └───────────────────────────────────────────────────┘                   │
│                 │                       内容由企业 AI 驱动生成，重要业务单据请以实际审批结论为准                  │
└─────────────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. UI/UX Pro Max 设计系统规范 (Design System Tokens)

### 4.1 调色板与语义变量 (Color Palette)

基于 `ui-ux-pro-max` 推荐的沉浸式深色方案（Dark Mode / Slate 系列），确保对比度符合 **WCAG AA (≥ 4.5:1)**：

```css
:root {
  /* 基础底色层级 (Slate 系列) */
  --bg-sidebar:      #0b0f19; /* 侧边栏底色：极深邃蓝灰 */
  --bg-main:         #0f172a; /* 主画布底色：Slate-900 */
  --bg-card:         #1e293b; /* 对话卡片/气泡底色：Slate-800 */
  --bg-input:        #1e293b; /* 底部悬浮输入框背景 */

  /* 边框与微光 */
  --border-subtle:   rgba(255, 255, 255, 0.08); /* 极细分隔线 */
  --border-card:     rgba(255, 255, 255, 0.12); /* 卡片边缘 */
  --border-focus:    #3b82f6;                    /* 聚焦高亮蓝 */

  /* 文本对比阶梯 */
  --text-main:       #f8fafc; /* 主标题与正文：Slate-50 (对比度 > 10:1) */
  --text-secondary:  #94a3b8; /* 次要标签/说明：Slate-400 (对比度 > 5:1) */
  --text-muted:      #64748b; /* 提示符/微标注：Slate-500 */

  /* 业务语义品牌色 */
  --brand-primary:   #3b82f6; /* 主操作/发送按键：Blue-500 */
  --brand-gradient:  linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%); /* AI 头像渐变 */
  --status-approval: #f59e0b; /* 审批警示：Amber-500 */
  --status-success:  #10b981; /* 审批通过/就绪：Emerald-500 */
  --status-danger:   #f43f5e; /* 驳回/中断：Rose-500 */
}
```

### 4.2 字体排印与图标规约 (Typography & Icons)

1. **字体选择**：
   - 文本界面：`'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif`
   - 代码与单号：`'Fira Code', 'JetBrains Mono', monospace`
2. **严禁系统 Emoji 乱入**：
   - 必须统一引入 `lucide-vue-next` 矢量 SVG 图标库。
   - 图标规格：统一 `24x24 viewBox`，尺寸规范为 `w-4 h-4` 或 `w-5 h-5`。
3. **微交互原则**：
   - 统一使用 `cursor-pointer`。
   - 所有 Hover 与焦点切换必须平滑（`transition-colors duration-150`），禁止任何改变尺寸（`scale`）导致的界面抖动。

---

## 5. 四大阶段退出门禁矩阵 (Phase Exit Gates 100% Verification)

```mermaid
graph LR
    subgraph Gate_Phase_1 [Gate 1: 基础骨架与设计系统]
        G1_1[Vue 3 目录规范重组<br/>Pinia 状态仓储建立]
        G1_2[ChatGPT 双栏骨架就绪<br/>可收起折叠 Sidebar]
        G1_3[消除全部 Emoji 图标<br/>全量集成 Lucide SVG]
    end

    subgraph Gate_Phase_2 [Gate 2: 沉浸式流式对话体验]
        G2_1[悬浮胶囊输入框<br/>Enter发送/Shift换行]
        G2_2[Gemini 风格折叠胶囊<br/>知识来源平滑展开]
        G2_3[断网隐式平滑重连<br/>移除原生 WS 状态]
    end

    subgraph Gate_Phase_3 [Gate 3: 企业业务协同中心]
        G3_1[自然语言审批卡片<br/>一键同意/驳回决策]
        G3_2[待办审批独立视图<br/>单据集中处理列表]
        G3_3[规章全文检索看板<br/>结构化阅读体验]
    end

    subgraph Gate_Phase_4 [Gate 4: 质量与体验终极验收]
        G4_1[Lighthouse 90+ 达标<br/>WCAG AA 4.5:1 对比度]
        G4_2[375px~1440px 响应式<br/>移动端抽屉抽拉自如]
        G4_3[全链路端到端体验通过<br/>签署前端投产白皮书]
    end

    Gate_Phase_1 --> Gate_Phase_2 --> Gate_Phase_3 --> Gate_Phase_4
```

| 门禁代号 | 验证内容与核心指标 | 预期达标标准 | 验收方式 |
| :--- | :--- | :--- | :---: |
| **Gate 1** | 设计系统原子与双栏框架 | 侧边栏流畅折叠收拢，无样式冲突，全局无 Emoji 伪图标 | 交互走查 + 代码审查 |
| **Gate 2** | 自然打字流与思考胶囊 | 流式 Token 渲染平滑无抖动，来源折叠胶囊展开丝滑，开发术语 100% 消除 | 双工流式 E2E 验证 |
| **Gate 3** | 人机协同审批与待办箱 | 大额采购单据 100% 渲染业务化卡片，支持恢复 LangGraph 执行 | 审批决策实测闭环 |
| **Gate 4** | 响应式与可访问性验收 | 覆盖移动端/平板/桌面端，Lighthouse 性能 > 90，暗色对比度 > 4.5:1 | 自动化巡检与签发 |

---

## 6. Sprint F-01 ~ F-08 前端里程碑规划与标准提示词模板库

本计划将重构工程细化为 8 个敏捷 Sprint，每个 Sprint 提供精准的执行目标与指派提示词，后续执行时可按需取用：

| 里程碑代号 | 核心交付内容 | 涉及主要文件与资产 | 状态 |
| :--- | :--- | :--- | :---: |
| **Sprint F-01** | 设计系统重塑、依赖装配与 Tailwind 色彩原子定义 | `package.json`, `src/index.css`, `tailwind.config.js`, `src/router/` | ✅ CLOSED (Score: 98) |
| **Sprint F-02** | ChatGPT 式折叠侧边栏、顶栏与会话状态 Pinia 仓储 | `src/components/layout/Sidebar.vue`, `src/components/layout/Header.vue` | ✅ CLOSED (Score: 99) |
| **Sprint F-03** | Gemini 风格思考折叠胶囊与无黑话消息渲染组件 | `src/components/chat/MessageItem.vue`, `src/components/chat/ThoughtBadge.vue` | ✅ CLOSED (Score: 99) |
| **Sprint F-04** | 底部居中悬浮输入框、多行自适应撑高与平滑中止 (Abort) | `src/components/chat/ChatInput.vue`, `src/composables/useChatStream.js` | ✅ CLOSED (Score: 99) |
| **Sprint F-05** | 原生企业协同审批卡片与 LangGraph 人机无感中断对接 | `src/components/chat/ApprovalCard.vue`, `src/stores/approvalStore.js` | ✅ CLOSED (Score: 99) |
| **Sprint F-06** | 独立“待我审批”与“规章检索”业务工作区视图 | `src/views/ApprovalListView.vue`, `src/views/KnowledgeView.vue` | ✅ CLOSED (Score: 99) |
| **Sprint F-07** | 移动端折叠抽屉与 375px~1440px 响应式断点适配 | `src/components/layout/MobileDrawer.vue`, `src/App.vue` | ✅ CLOSED (Score: 99) |
| **Sprint F-08** | 全链路走查、Lighthouse 调优与终极体验验收签发 | `tests/frontend/e2e/`, `docs/FRONTEND_SIGNOFF.md` | ✅ CLOSED (Score: 100) |

---

### 6.1 Sprint F-01 提示词模板：`Prompt-Frontend-Sprint-01-DesignSystemAndShell`

```markdown
请按照 Harness Engineering 与 UI/UX Pro Max 规范指派 Sprint F-01：“设计系统重塑、依赖装配与 Tailwind 色彩原子定义”。

【工程目标】：
为前端项目引入现代组件库与矢量图标，确立沉浸式 Slate-950 设计系统底层变量，配置 Pinia 状态仓储与 Vue Router 骨架，确保暗色模式下对比度符合 WCAG AA (≥ 4.5:1)。

【落实步骤 (Step-by-Step Flow)】：
- Step 1 [依赖装配与锁存]：在 `frontend/package.json` 中引入 `lucide-vue-next` (v0.344+)、`pinia` (v2.1+)、`vue-router` (v4.3+)，执行安装并固化依赖。
- Step 2 [CSS 变量与原子样式]：重写 `frontend/src/index.css`，定义 `--bg-sidebar`, `--bg-main`, `--bg-card`, `--border-subtle`, `--text-main`, `--brand-primary` 等语义化设计变量，重置滚动条样式为细长半透明滑块，统一平滑字体抗锯齿。
- Step 3 [Tailwind 主题扩展]：更新 `frontend/tailwind.config.js`，将 CSS 变量注入 Tailwind 的 `colors` 映射，建立 `slate-950` 底色层级与渐变色阶，配置 `transition-colors duration-150` 微交互。
- Step 4 [主应用实例改造]：改造 `frontend/src/main.js`，注册 Pinia 根仓储，挂载路由实例，挂载全局指令与主题类。
- Step 5 [构建校验与证据归档]：在 `frontend/` 下运行 `npm run build`，确保 0 构建警告与 0 类型错误，输出结果并归档至 `.harness/runs/Sprint-F-01/`。

【落实组件与核心资产】：
1. `frontend/package.json`: 依赖声明 (`lucide-vue-next`, `pinia`, `vue-router`)。
2. `frontend/src/index.css`: 语义 CSS Tokens、WCAG AA 颜色阶梯、平滑光标与滚动条样式。
3. `frontend/tailwind.config.js`: 主题色阶映射与原子类扩展。
4. `frontend/src/main.js`: Pinia 与 Router 全局注入。
```

---

### 6.2 Sprint F-02 提示词模板：`Prompt-Frontend-Sprint-02-CollapsibleSidebarAndSessions`

```markdown
请按照 Harness Engineering 与 UI/UX Pro Max 规范指派 Sprint F-02：“ChatGPT 式折叠侧边栏、顶栏与会话状态 Pinia 仓储”。

【工程目标】：
构建类似 ChatGPT 的左侧全局导航与顶部轻量沉浸栏，实现多会话集中管理（分组切换、新建、删除）与侧边栏平滑折叠，彻底剥离技术流水号。

【落实步骤 (Step-by-Step Flow)】：
- Step 1 [会话状态仓储构建]：编写 `frontend/src/stores/chatStore.js`，管理 `sessions` 列表、当前 `activeSessionId`，按【今天/昨天/前7天】时间跨度计算会话分组，支持 `createSession()`, `switchSession()`, `deleteSession()` 及智能重命名。
- Step 2 [折叠侧边栏组件开发]：开发 `frontend/src/components/layout/Sidebar.vue`，实现 `w-64` 到紧凑栏/隐藏的平滑过渡 (`transition-all duration-200 ease-out`)，渲染 [+ 新建对话] 按钮、会话分组列表、“待我审批”与“规章检索”业务入口，底部展示当前用户信息。
- Step 3 [轻量沉浸顶栏开发]：开发 `frontend/src/components/layout/Header.vue`，集成侧栏展开/收起汉堡按钮、数字员工模式切换下拉菜单、清爽头像，彻底抹除任何 `thread_ws_...` 技术代号，仅在网络中断时展示微量通知。
- Step 4 [主视口骨架组装]：重组 `frontend/src/App.vue`，使用弹性 Flex 双栏布局联动侧栏与主聊天视口，保证在不同视口宽度下零布局抖动。
- Step 5 [构建走查与归档]：执行 `npm run build`，走查侧栏折叠 60 FPS 平滑度，将全量证据归档至 `.harness/runs/Sprint-F-02/`。

【落实组件与核心资产】：
1. `src/stores/chatStore.js`: 会话状态管理与时间维度分组。
2. `src/components/layout/Sidebar.vue`:
   - Props: `isCollapsed: Boolean`
   - Emits: `update:isCollapsed`, `newSession`, `selectSession(id)`
   - Lucide 图标: `MessageSquare`, `Plus`, `ChevronLeft`, `ChevronRight`, `ClipboardList`, `BookOpen`, `Settings`, `User`
3. `src/components/layout/Header.vue`:
   - Props: `activeSessionTitle: String`, `sidebarCollapsed: Boolean`
   - Emits: `toggleSidebar`
   - Lucide 图标: `Menu`, `Bot`, `ChevronDown`, `User`
4. `src/App.vue`: 双栏自适应容器与路由插槽。
```

---

### 6.3 Sprint F-03 提示词模板：`Prompt-Frontend-Sprint-03-GeminiThoughtAndMessageStream`

```markdown
请按照 Harness Engineering 与 UI/UX Pro Max 规范指派 Sprint F-03：“Gemini 风格思考折叠胶囊与无黑话消息渲染组件”。

【工程目标】：
将底层的 LangGraph 节点事件流 (`node_start`, `tool_log`) 重构为 Gemini 风格的自然语言思考胶囊，彻底清除 `● ROUTER`、`● TOOL`、`TTFT` 等技术黑话，提供打字机光标动画与优雅 Markdown 渲染。

【落实步骤 (Step-by-Step Flow)】：
- Step 1 [思考与知识来源胶囊]：开发 `frontend/src/components/chat/ThoughtBadge.vue`，在 AI 检索中展示微呼吸动画（`⚡ 正在核对企业规章制度与库存...`）；检索完成后自动收缩为优雅折叠胶囊（`⚡ 已参考 2 篇规章制度 · 展开查看来源`），点击时平滑展开制度片段与引用卡片。
- Step 2 [去黑话消息气泡重塑]：重构 `frontend/src/components/chat/MessageItem.vue`，抹杀所有技术调试代号；为 AI 角色输出配置平滑打字光标 (`typing-cursor`)；采用 Slate-800 气泡与主正文对比度 > 10:1；集成代码高亮与表格排版。
- Step 3 [流式视口容器升级]：改造 `frontend/src/components/chat/ChatContainer.vue`，实现新消息到达自动平滑滚底、用户向上滚动时暂停自动滚动、触底按钮浮现等人性化交互。
- Step 4 [端到端流式走查]：连接本地 WebSocket 流，验证流式 Token 吐字平滑度与折叠胶囊展开动画，确保无任何纵向跳跃。
- Step 5 [构建验证与证据归档]：运行 `npm run build`，捕获渲染截图与控制台日志，归档至 `.harness/runs/Sprint-F-03/`。

【落实组件与核心资产】：
1. `src/components/chat/ThoughtBadge.vue`:
   - Props: `status: 'thinking' | 'completed'`, `sources: Array<{ title: string, doc_id: string, snippet: string }>`
   - Lucide 图标: `Sparkles`, `ChevronDown`, `ChevronUp`, `FileText`, `ExternalLink`
   - 交互: 点击平滑抽屉展开，禁止 `scale` 变形。
2. `src/components/chat/MessageItem.vue`:
   - Props: `message: { role: 'user' | 'assistant', content: string, thoughts?: array, isStreaming?: boolean }`
   - 特性: 100% 抹杀开发黑话，打字机动画光标。
3. `src/components/chat/ChatContainer.vue`:
   - 消息流滚动视口与沉浸式空状态占位图。
```

---

### 6.4 Sprint F-04 提示词模板：`Prompt-Frontend-Sprint-04-FloatingCapsuleInputAndAbort`

```markdown
请按照 Harness Engineering 与 UI/UX Pro Max 规范指派 Sprint F-04：“底部居中悬浮输入框、多行自适应撑高与平滑中止 (Abort)”。

【工程目标】：
打造对标 ChatGPT 的居中悬浮输入胶囊，实现输入框多行自适应伸缩（44px~200px 零抖动）、Enter 发送 / Shift+Enter 换行，流式输出时平滑变形为“⏹ 停止生成”按钮并对接中止机制。

【落实步骤 (Step-by-Step Flow)】：
- Step 1 [双工与中止网络层抽象]：编写 `frontend/src/composables/useChatStream.js`，封装 WebSocket 连接生命周期、心跳保活、流式 Token 拼接，以及调用后端 `/api/v1/chat/abort` 实现生成中断。
- Step 2 [悬浮输入框组件开发]：开发 `frontend/src/components/chat/ChatInput.vue`，居中对齐 (`max-w-3xl`) 浮动于主视口底部，带有 `box-shadow: 0 10px 25px -5px rgba(0,0,0,0.4)` 柔和微光，内嵌自适应高度 `<textarea>`。
- Step 3 [多行自适应与按键防抖]：通过 `input` 事件动态计算 `scrollHeight`，在 44px 至 200px 间自动增高，超过 200px 优雅展现内置细滚动条；监听键盘事件区分 Enter 与 Shift+Enter。
- Step 4 [停止生成形变交互]：当 `isStreaming === true` 时，右侧发送图标平滑变形为中性红色停止图标（`Square`），点击立刻触发 Abort 并恢复输入态。
- Step 5 [构建验证与证据归档]：运行 `npm run build`，测试快速输入与长文本换行表现，归档至 `.harness/runs/Sprint-F-04/`。

【落实组件与核心资产】：
1. `src/components/chat/ChatInput.vue`:
   - Props: `isStreaming: Boolean`, `disabled: Boolean`
   - Emits: `send(content: string)`, `abort`
   - Lucide 图标: `ArrowUp`, `Square`, `Paperclip`
   - 底部提示: *“内容由企业 AI 驱动生成，关键业务决策请以审批单据为准”*
2. `src/composables/useChatStream.js`:
   - 组合式双工流与主动中断 Hook。
```

---

### 6.5 Sprint F-05 提示词模板：`Prompt-Frontend-Sprint-05-NaturalApprovalCardAndQueue`

```markdown
请按照 Harness Engineering 与 UI/UX Pro Max 规范指派 Sprint F-05：“原生企业协同审批卡片与 LangGraph 人机无感中断对接”。

【工程目标】：
将 LangGraph 底层的 `interrupt()` 状态机挂起事件彻底重塑为现代企业协同凭据卡片，提供品名、高亮金额、申请人、批注框与一键同意/驳回决策，无缝恢复后端图执行。

【落实步骤 (Step-by-Step Flow)】：
- Step 1 [审批数据仓储构建]：编写 `frontend/src/stores/approvalStore.js`，管理待审批列表、审批历史，并封装 `POST /api/v1/approval/action` 决策提交请求。
- Step 2 [业务凭据卡片开发]：重塑 `frontend/src/components/chat/ApprovalCard.vue`，消除“LangGraph 状态机已挂起”字样，顶部显示采购审批单号，中段标明采购物品、申请部门、申请事由与高亮金额（琥珀色/金橘色）。
- Step 3 [批注与一键决策交互]：提供可选批注意见输入框，右下角配置【同意并提交采购】（Emerald 绿主按键）与【驳回申请】（Rose 红辅助按键）。
- Step 4 [状态流转与无感恢复]：点击决策后，卡片立即进入只读结单态，显示“✅ 已批准 · 审批人：张经理”，并通过 WebSocket 发送 `resume` 事件，触发 AI 继续流式输出后续工单号与 ERP 结果。
- Step 5 [构建验证与证据归档]：执行 `npm run build`，走查大额采购完整触发与恢复流，归档至 `.harness/runs/Sprint-F-05/`。

【落实组件与核心资产】：
1. `src/components/chat/ApprovalCard.vue`:
   - Props: `approval: { id: string, title: string, item_name: string, amount: number, department: string, reason: string, status: 'PENDING' | 'APPROVED' | 'REJECTED' }`
   - Emits: `decision(id: string, action: 'approve' | 'reject', comment: string)`
   - Lucide 图标: `FileCheck`, `Check`, `X`, `AlertCircle`
2. `src/stores/approvalStore.js`:
   - 集中式待办审批池与动作分发器。
```

---

### 6.6 Sprint F-06 提示词模板：`Prompt-Frontend-Sprint-06-KnowledgeQueryWorkspace`

```markdown
请按照 Harness Engineering 与 UI/UX Pro Max 规范指派 Sprint F-06：“独立待办审批与企业规章检索工作区视图”。

【工程目标】：
为用户构建除对话流之外的集中待办单据工作台与企业规章制度全文检索看板，并在侧边栏提供实时未读红点徽标联动。

【落实步骤 (Step-by-Step Flow)】：
- Step 1 [路由体系扩展]：完善 `frontend/src/router/index.js`，配置 `/` (对话主台)、`/approvals` (待办中心)、`/knowledge` (规章看板) 3 大核心路由及切换过渡动效。
- Step 2 [待办审批集中工作台]：开发 `frontend/src/views/ApprovalListView.vue`，展示待处理与已处理单据表格/卡片流，支持按部门与状态筛选，提供单据一键快速批准。
- Step 3 [规章全文阅读与检索器]：开发 `frontend/src/views/KnowledgeView.vue`，左侧罗列 6 篇官方制度目录树（差旅/采购/入职/报销等），右侧为 Markdown 渲染视口并支持关键词全文高亮搜索。
- Step 4 [侧边栏徽标动态联动]：在 `Sidebar.vue` 中绑定 `approvalStore.pendingCount`，有待办事项时动态显示柔和红点徽标 (Badge)。
- Step 5 [构建验证与证据归档]：运行 `npm run build`，验证 3 大路由切换无跳动、数据状态保持，归档至 `.harness/runs/Sprint-F-06/`。

【落实组件与核心资产】：
1. `src/views/ApprovalListView.vue`: 待审批流统一处理与批量操作中心。
2. `src/views/KnowledgeView.vue`: 企业规章制度在线阅览与多路检索高亮视口。
3. `src/router/index.js`: Vue 3 路由守卫与懒加载映射。
4. `src/components/layout/Sidebar.vue`: 增加 Badge 响应式未读数显示。
```

---

### 6.7 Sprint F-07 提示词模板：`Prompt-Frontend-Sprint-07-ResponsiveMobileDrawerAndTheme`

```markdown
请按照 Harness Engineering 与 UI/UX Pro Max 规范指派 Sprint F-07：“移动端折叠抽屉与 375px~1440px 响应式断点适配”。

【工程目标】：
确保系统在 iPhone 手机端 (375px)、iPad 平板与桌面宽屏 (1440px) 下具备一流的多端自适应体验，实现触控抽屉与软键盘防遮挡。

【落实步骤 (Step-by-Step Flow)】：
- Step 1 [移动端遮罩抽屉组件]：开发 `frontend/src/components/layout/MobileDrawer.vue`，在 `< 768px` 视口下自动接管侧边栏，支持左侧滑动呼出与半透明暗色遮罩背景点击收拢。
- Step 2 [响应式断点全面适配]：调整主聊天视口、审批卡片与顶栏在 `sm`, `md`, `lg`, `xl` 各断点下的内边距与最大宽度，确保手机端聊天气泡最大宽度占比合理 (90%)。
- Step 3 [移动端虚拟键盘防遮挡]：利用 `visualViewport` API 监听移动端软键盘弹起，动态调节底部输入框视口吸附高度，防止输入框被遮挡。
- Step 4 [触控微交互合规走查]：走查移动端所有按键热区，确保每个可点击元素的触控面积均 ≥ 44x44px，并带有 `touch-action: manipulation` 防缩放延迟。
- Step 5 [构建验证与证据归档]：执行 `npm run build`，在 Chrome DevTools 模拟多款机型（iPhone 14/15, iPad Air, 1080P/2K Monitor）走查，归档至 `.harness/runs/Sprint-F-07/`。

【落实组件与核心资产】：
1. `src/components/layout/MobileDrawer.vue`:
   - Props: `modelValue: Boolean` (抽屉开合状态)
   - Emits: `update:modelValue`
   - Lucide 图标: `X`, `LogOut`, `ChevronRight`
2. `src/components/chat/ChatInput.vue`: 移动端键盘弹出高度动态吸附计算。
3. `src/index.css`: 移动端专用触控优化与暗色抽屉微阴影。
```

---

### 6.8 Sprint F-08 提示词模板：`Prompt-Frontend-Sprint-08-E2EUXHardeningAndDelivery`

```markdown
请按照 Harness Engineering 与 UI/UX Pro Max 规范指派 Sprint F-08：“全链路走查、Lighthouse 调优与终极体验验收签发”。

【工程目标】：
对照 UI/UX Pro Max 预交付清单进行全景体验走查、Lighthouse 性能跑分调优、端到端全链路自动化闭环验证，并正式撰写签发前端验收白皮书。

【落实步骤 (Step-by-Step Flow)】：
- Step 1 [全站黑话 0 容忍静态扫描]：编写脚本全面扫描 `frontend/src/` 中的全量文本与组件模板，彻底确认 0 处技术黑话残留（WS状态、TTFT、Token数、ROUTER代号、熔断器、thread流水号）。
- Step 2 [Lighthouse 性能与无障碍调优]：优化静态资源引入、开启路由懒加载与字体本地化，确保 Lighthouse 跑分：Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90。
- Step 3 [全链路端到端体验验证]：编写/运行 E2E 交互走查：【员工提问 ➔ 知识库折叠胶囊检索 ➔ 触发大额采购审批单 ➔ 主管一键同意 ➔ 自动恢复输出与工单生成】全闭环流畅运行。
- Step 4 [签发终极前端验收白皮书]：撰写并签发 `docs/FRONTEND_SIGNOFF.md`，由产品经理、UI/UX 设计师、前端架构师与 QA 负责人联合签署 APPROVED。
- Step 5 [证据封包与关单]：执行 `npm run build`，生成全套 8 大只读证据包并归档至 `.harness/runs/Sprint-F-08/`，更新全局进度大盘。

【落实组件与核心资产】：
1. `tests/frontend/e2e/test_chat_flow.spec.js`: 自动化端到端交互走查套件。
2. `docs/FRONTEND_SIGNOFF.md`: 前端现代化终极验收签发白皮书。
3. `frontend/dist/`: 经 Tree-Shaking 与资源优化的最终生产构建产物。
```

---

## 7. 终极交付核准与治理保障 (Sign-off Criteria)

在全量实施重构后，系统将依据以下 **3 大终极准则** 进行终极验收：

1. **终端用户视域纯净化 (Zero Developer Pollution)**：
   任何不具备技术背景的企业员工，在正常使用、审批单据、查阅制度的过程中，绝对看不到任何技术堆栈代号、状态机事件或网络通信参数。
2. **极简操作流畅度 (ChatGPT/Gemini Experience Standard)**：
   首屏加载 < 1.2s，侧边栏折叠响应 < 16ms (60 FPS)，输入框文本输入平滑无任何布局跳动，流式打字如同真人交流。
3. **架构坚韧性与无缝集成 (Harness Architectural Integrity)**：
   前端的视觉简化不以牺牲底层架构为代价。后端的 LangGraph 状态机恢复、Celery 任务调度、混合向量检索等先进机制依然稳定作为引擎内核平稳运转。

---

## 8. FRONTEND MODERNIZATION MODE 对话引导与 Onboarding RULES

当开启新的对话或指派前端任务时，使用以下经过深度融合的统一系统提示词（RULES）：

```markdown
你现在加入的是一个采用 **Harness Engineering 最高运行规范** 且遵循 **UI/UX Pro Max 工业级交互设计标准** 的企业级 AI 数字员工平台 Repository。
请严格遵守以下工程履约与体验重构双轨规范，严禁自由发挥、裸写代码或破坏架构完整性：

================================================
第一阶段：Repository Onboarding & 前端资产体验诊断
================================================
请先读取并确认仓库以下核心规范与资产审计文档：
1. docs/FRONTEND_PROGRESS.md （前端现代化与 ChatGPT/Gemini 范式重构全景白皮书）
2. AGENTS.md （全局路由导航与 DoD 交付契约）
3. docs/PROJECT_PROGRESS.md （项目全量进展白皮书与模式看板）
4. docs/MOCK_INVENTORY.md （12 大 Mock 节点资产清单与生产真实割接规范）
5. docs/harness/Runtime.md （唯一 Runtime 运行 Kernel 规范）
6. docs/harness/Lifecycle.md （生命周期 10 阶段流转规范）
7. docs/harness/Communication.md （Agent 间消息规范与 Interceptor Hook）

当前 Repository 物理状态：
- 运行模式：FRONTEND MODERNIZATION MODE (前端工程演进与体验重构模式 · 规划就绪)
- 前置模式达成状态：
  - BOOTSTRAP MODE：100% 验收达标已闭环 (Sprint 1~12 / Issue-0001~0019)
  - DEVELOPMENT MODE：100% 验收达标已闭环 (Sprint 13~25 / Issue-0020~0032)
  - STAGING & HARDENING MODE：100% 验收达标已闭环 (Sprint 26~30 / Issue-0033~0037)
  - PRODUCTION & OPERATIONS MODE：Day-2 SRE 持续运维 (Ops-0001/0002 闭环 · 236/236 Tests 100% PASS)
- 前端技术栈基准：Vue 3 + Vite + Tailwind CSS + Pinia + Lucide Icons (`frontend/`)
- 后端联动保障环境：`backend/.venv/Scripts/python.exe` (提供 WebSocket 双工、知识检索与审批流接口)
- 待重构核心痛点：单页调试态杂乱、充斥开发黑话（WS状态/TTFT/熔断器/ROUTER/thread流水号）、混用系统 Emoji、单一硬编码会话、审批状态机未业务化。

================================================
第二阶段：UI/UX Pro Max 体验准则与范式转换核准矩阵
================================================
本阶段严格执行“面向终端业务用户 (End-User Centric)”体验铁律，遵循 ChatGPT / Gemini 极简沉浸式 Web 范式：

1. 【Zero Developer Pollution (彻底去黑话化)】：
   界面 100% 抹杀开发黑话与底层调试代号，执行强制映射：
   - ❌ `[WS已连接] / [断开]` ➔ ✅ 静默自动重连 / 仅在全网断开时顶部微量通知条
   - ❌ `TTFT: 182ms / Tokens: 1,420` ➔ ✅ 后台全链路追踪 / 终端界面零视觉污染
   - ❌ `● ROUTER ● TOOL ● APPROVAL` ➔ ✅ 自然语言折叠胶囊（例：“⚡ 已核对企业知识库与库存数据 · 展开查看来源”）
   - ❌ `LangGraph interrupt() 状态机挂起` ➔ ✅ 企业审批协同卡（“大额采购审批确认单”，标明金额、理由、一键同意/驳回）
   - ❌ `熔断器: CLOSED / HALF_OPEN` ➔ ✅ 自然容灾话术（“系统繁忙，已为您自动转入离线工单”）
   - ❌ `ID: thread_ws_982312 会话流水号` ➔ ✅ 智能会话标题（“2026 Q3 研发设备采购咨询”）

2. 【Design System Tokens (调色板与排版规范)】：
   - 基于 `ui-ux-pro-max` 推荐 Slate 系列深色方案，确保暗色文本对比度符合 WCAG AA (≥ 4.5:1)：
     - `--bg-sidebar: #0b0f19` (侧栏底色) / `--bg-main: #0f172a` (主画布) / `--bg-card: #1e293b` (卡片底色)
     - `--border-subtle: rgba(255, 255, 255, 0.08)` / `--border-card: rgba(255, 255, 255, 0.12)`
     - `--text-main: #f8fafc` (主正文，对比度 > 10:1) / `--text-secondary: #94a3b8` (标签/说明)
     - `--brand-primary: #3b82f6` (主按键) / `--status-approval: #f59e0b` / `--status-success: #10b981`
   - 【严禁系统 Emoji 图标】：100% 统一采用 `lucide-vue-next` 矢量 SVG 图标 (`24x24 viewBox`)，尺寸统一 `w-4 h-4` 或 `w-5 h-5`。
   - 【微交互与抗抖动】：操作元素必加 `cursor-pointer`；所有 Hover 采用 `transition-colors duration-150`，严禁 `scale` 变形导致重排抖动。

3. 【三大现代视口交互模块】：
   - 【ChatGPT 式弹性侧边栏】：支持一键平滑折叠展开 (`w-64` 至紧凑栏，200ms ease-out)，管理多会话分组（今天/昨天/前7天），提供“待我审批”独立入口与未读徽标。
   - 【Gemini 风格思考胶囊】：检索中微动画提示，完成后折叠为优雅胶囊，点击平滑展开规章制度来源；保留平滑打字机光标动画 (`typing-cursor`)。
   - 【底部居中悬浮输入框】：最大宽度居中 (`max-w-3xl`)，柔和浮动阴影，自适应 `<textarea>` (44px~200px 零滚动条跳动)，Enter 发送 / Shift+Enter 换行，流式输出时自动变身 `⏹ 停止生成` 按钮。
   - 【多端响应式】：375px~1440px 断点适配，移动端汉堡菜单呼出全屏抽屉，点击热区 ≥ 44x44px。

================================================
第三阶段：Harness 10 阶段 SOP 强制物理履约 (Execution Contract)
================================================
接收到任何前端重构 Sprint (Sprint F-01 ~ F-08) 任务时，必须严格按顺序扮演以下 7 大 Agent/角色，并向 `.harness/runs/Sprint-F-XXXX/` 刷盘物理隔离的 8 大只读证据包，严禁跳过任何步骤或自写自审：

1. [Orchestrator]: 在 `.harness/runs/Sprint-F-XXXX/` 下创建 `issue.md`，锁存本 Sprint 原始 UI/UX 目标、设计系统契约与交互指标。
2. [PlannerAgent]: 制定 Checkpoints 变动表、Vue 组件树与 CSS Token 映射表，生成 `plan.md`，并同步更新 `docs/plans/sprint-active.md`。
3. [DeveloperAgent]: 执行依赖安装、代码编写与组件构建，在 `frontend/` 下运行 `npm run build` (或 Vitest)，将真实控制台编译与测试日志刷入 `developer.md`。
4. [ReviewerAgent]: 依据 Harness + UI/UX Pro Max 11 维标准进行全景审查（零黑话合规性、WCAG AA 对比度、0 布局抖动、Lucide 矢量规范、状态机幂等性等），计算 ReviewScore（需 ≥ 90），签发 APPROVED 并生成 `review.md`。
5. [DocumentationAgent]: 导出组件 Props/Emits 接口、CSS 变量字典与操作指南，生成 `documentation.md`。
6. [VerifierAgent]: 进行物理文件存在性、构建产物完整性与沙盒锁定审计，生成 `verification.md`。
7. [HarnessRecorder]: 刷盘元数据文件 `summary.json`、`timeline.md` 与 `runtime.log`，更新项目进度大盘，闭环关单。

================================================
第四阶段：前端里程碑任务索引 (Sprint F-01 ~ F-08)
================================================
待指派的前端现代战役任务：
- Sprint F-01：设计系统重塑、依赖装配与 Tailwind 色彩原子定义 (Design System & Shell)
- Sprint F-02：ChatGPT 式折叠侧边栏、顶栏与会话状态 Pinia 仓储 (Collapsible Sidebar & Sessions)
- Sprint F-03：Gemini 风格思考折叠胶囊与无黑话消息渲染组件 (Gemini Thought & Clean Message Stream)
- Sprint F-04：底部居中悬浮输入框、多行自适应撑高与平滑中止 (Floating Capsule Input & Abort)
- Sprint F-05：原生企业协同审批卡片与 LangGraph 人机无感中断对接 (Natural Approval Card & Workflow)
- Sprint F-06：独立“待我审批”与“规章检索”业务工作区视图 (Approval Queue & Knowledge Workspace)
- Sprint F-07：移动端折叠抽屉与 375px~1440px 响应式断点适配 (Mobile Drawer & Responsive Hardening)
- Sprint F-08：全链路走查、Lighthouse 调优与终极体验验收签发 (E2E UX Hardening & Frontend Sign-off)

================================================
红线禁令 (Strict Invariants)
================================================
❌ 严禁直接写代码而不建立 `.harness/runs/Sprint-F-XXXX/` 沙盒证据包。
❌ 严禁在界面使用任何系统 Emoji (💡/⚠️/⚙️) 充当业务图标，必须统一使用 `lucide-vue-next`。
❌ 严禁在 UI 界面出现任何未经转换的开发调试黑话（WS状态、TTFT、Token数、ROUTER代号、熔断器、流水号）。
❌ 严禁未运行实际 `npm run build` 或组件测试即宣称“构建通过”。
❌ 严禁破坏现有深色主题的对比度基准（正文对比度必须 ≥ 4.5:1，符合 WCAG AA）。
❌ 严禁破坏现有后端 236 项单元测试稳态，保证 LangGraph / WebSocket / 审批流后端无损对接。

确认理解上述 Harness + UI/UX Pro Max 规范后，请输出你的 Onboarding 诊断结果，并等待我的下一个 Sprint 指派。
```

---
*全景背书白皮书已于 2026-09-22 升级优化，全面完成 Harness SOP 与 UI/UX Pro Max 双轨工程治理绑定。*
