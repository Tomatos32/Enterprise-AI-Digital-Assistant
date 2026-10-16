# Sprint-F-09: Frontend Design System & Component Documentation
# ChatGPT / Claude 原生 Web 交互与 Vuebits 旗舰组件设计手册

> **Sprint ID**: `Sprint-F-09`  
> **Agent**: `DocumentationAgent`  
> **Target Framework**: Vue 3 + Tailwind CSS + Vuebits + Hugeicons + Lucide  
> **Date**: 2026-10-16  

---

## 1. Vuebits 旗舰原子组件目录与 API 规范

所有原子动效组件均落盘于 `frontend/src/components/ui/`，具备独立的类型自洽与双主题拟合能力：

### 1.1 `PromptBar.vue` (多模态指令输入栏)
- **定位**：ChatGPT / Claude 风格终极多模态输入栏，集成 `@` 菜单、`/` 指令、模型切换与语音交互。
- **Props**:
  - `modelValue` (String): 输入文本双向绑定。
  - `isStreaming` (Boolean): 流式响应状态（切换发送按键为停止方块）。
- **Emits**:
  - `update:modelValue`: 双向同步文本。
  - `send`: 发送消息 payload `{ text, source, model }`。
  - `abort`: 触发流式中断请求 (`/api/v1/chat/abort`)。

### 1.2 `ThoughtLine.vue` (CoT 原生思维链折叠头)
- **定位**：Claude 3.7 / Gemini 极简思索折叠胶囊。
- **Props**:
  - `isThinking` (Boolean): 当前是否处于大模型思维推理中。
  - `durationSeconds` (Number): 实际思考耗时（秒）。
  - `steps` (Array): 推理步骤对象数组 `[{ title, desc, status }]`。
  - `preview` (String): 思考阶段占位摘要。

### 1.3 `CallChip.vue` (行内工具调用芯片)
- **定位**：RAG 向量检索、SQL 查询、Saga 事务调用的行内可视化芯片。
- **Props**:
  - `toolName` (String): 工具名称（自动映射为业务友好的中文名称）。
  - `status` ('running' | 'success' | 'error'): 执行状态。
  - `durationMs` (Number): 工具调用耗时毫秒计数。
  - `inputSummary` (String): 输入参数摘要。

### 1.4 `VoicePill.vue` (语音录音波形胶囊)
- **定位**：Advanced Voice 录音胶囊，动态模拟电平振幅。
- **Props**: `active` (Boolean)。
- **Emits**: `finish`, `cancel`。

### 1.5 `FolderFloat.vue` (3D 悬浮翻盖文件夹)
- **定位**：企业知识库与制度中心 3D 浮动卡片云，跟随光标微动倾斜。
- **Props**: `title`, `count`, `category`, `description`, `lastUpdated`。
- **Emits**: `click`。

### 1.6 `LineSidebar.vue` (光标邻近微动侧栏条目)
- **定位**：历史会话条目，支持光标邻近流动投影（Cursor Proximity Effect）。
- **Props**: `title`, `active`, `icon`, `allowDelete`。
- **Emits**: `select`, `delete`。

### 1.7 `ShinyText.vue` (金属流光徽章)
- **定位**：企业数字员工 Pro 标识背景流光文本。
- **Props**: `text`, `disabled`, `speed`。

### 1.8 `GlideSelect.vue` (浮动高光模型切换器)
- **定位**：Claude 3.7 / GPT-4o / o3-mini 模型角标快速切换。
- **Props**: `modelValue`, `options`。
- **Emits**: `update:modelValue`。

---

## 2. 日间温润白与夜间曜石灰色彩令牌规范

在 `frontend/src/index.css` 中定义了双轨语义令牌，并通过 `<html class="dark">` 实现无缝切换：

```css
/* 日间模式 (温润纸质象牙白 · WCAG AAA) */
:root {
  --bg-main:         #fbf9f5; /* 纸质象牙白主画布 */
  --bg-sidebar:      #f3f0e6; /* 燕麦米色侧栏 */
  --bg-card:         #ffffff; /* 纯白卡片 */
  --bg-input:        #ffffff; /* 纯白输入框 */
  --text-main:       #111827; /* 墨黑正文 (>15:1 对比度) */
  --text-secondary:  #4b5563; /* 石板灰次级文本 (>7:1 对比度) */
  --text-muted:      #9ca3af; /* 中性提示灰 */
  --border-subtle:   rgba(15, 23, 42, 0.08);
  --border-card:     rgba(15, 23, 42, 0.12);
  --brand-primary:   #2563eb;
}

/* 夜间模式 (曜石灰与深板岩 · WCAG AA) */
.dark {
  --bg-main:         #0f172a; /* 曜石灰主画布 */
  --bg-sidebar:      #0b0f19; /* 深板岩侧栏 */
  --bg-card:         #1e293b; /* 板岩卡片 */
  --bg-input:        #1e293b; /* 板岩输入框 */
  --text-main:       #f8fafc; /* 珍珠白正文 (>10:1 对比度) */
  --text-secondary:  #94a3b8; /* 次级浅板岩 */
  --text-muted:      #64748b; /* 暗提示灰 */
  --border-subtle:   rgba(255, 255, 255, 0.08);
  --border-card:     rgba(255, 255, 255, 0.12);
  --brand-primary:   #3b82f6;
}
```

---

## 3. 双核矢量图标标准 (Zero Emoji Standard)

全前端已 100% 驱逐 Emoji 符号，所有视觉元素由双核图标库提供：
- 通用动作与导航：`lucide-vue-next` (24x24 viewBox, stroke-width: 2)。
- 高级多模态与专业图标：`@hugeicons/vue` + `@hugeicons/core-free-icons`。
- 图标尺寸阶梯：
  - 微标记与胶囊：`w-3.5 h-3.5` (14px)
  - 按钮与导航：`w-4 h-4` (16px)
  - 核心入口与头像：`w-5 h-5` ~ `w-6 h-6` (20~24px)
