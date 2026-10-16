# Sprint-F-09: ChatGPT / Claude 原生 Web 交互与 Vuebits 旗舰动效组件集成

> **Sprint ID**: `Sprint-F-09`  
> **Target Component**: `frontend/` (Vue3 + Tailwind CSS + Vuebits + Hugeicons + Lucide)  
> **Mode**: `FRONTEND MODERNIZATION MODE (前端工程演进与体验重构模式)`  
> **Created At**: 2026-10-16T08:00:00Z  
> **Supreme Invariants**: 8 大证据包落盘 · 0 Emoji 违规 · 0 技术黑话调试占位符 · WCAG AA/AAA 日夜双主题拟合  

---

## 1. 原始需求与工程目标 (User Requirement & Objectives)

将企业级 AI 数字员工平台前端界面从通用沉浸式 UI 进一步跃升至与 **ChatGPT (GPT-4o/o1/o3/Advanced Voice)** 及 **Claude (3.5/3.7 Extended Thinking)** 原生 Web 界面并驾齐驱的顶级体验。
不仅完成动效组件替换，更实现日间纸质温润白（`#FBF9F5` / `#FFFFFF`）与夜间曜石黑（`#0F172A` / `#0B0F19`）的深度背景拟合，引入专业双核矢量图标库（`@hugeicons/vue` + `lucide-vue-next`），全站 100% 抹杀任何 Emoji 符号与底层代码注释，保障 60 FPS 物理动效与 WCAG AA/AAA 视觉对比度。

---

## 2. 八大落实步骤与工程清单 (Step-by-Step Flow)

1. **Step 1 [双核矢量图标库与动效引擎装配]**：
   - 在 `frontend/package.json` 安装 `@hugeicons/vue`、`@hugeicons/core-free-icons` 与 `lucide-vue-next` (v0.344+)，安装物理动效引擎 `motion-v` (v1.10+)；
   - 在项目根与 `frontend/components.json` 固化 `@vue-bits` 注册表 URL (`https://vue-bits.dev/r/{name}.json`)。
2. **Step 2 [日夜双主题色彩令牌与背景无缝拟合]**：
   - 重构 `frontend/src/index.css` 与 `tailwind.config.js`，建立日间模式（象牙白 `--bg-main: #fbf9f5`、侧栏 `--bg-sidebar: #f3f0e6`、墨色正文 `--text-main: #111827`）与夜间 Dark style（曜石灰 `--bg-main: #0f172a`、深板岩 `--bg-sidebar: #0b0f19`、珍珠白 `--text-main: #f8fafc`）双轨映射；
   - 在 PromptBar、顶栏与选择器统一引入 `backdrop-blur-md` 毛玻璃与环境微光阴影，实现与背景画布的平滑拟合，双主题切换带有 `transition-colors duration-200` 平滑过渡。
3. **Step 3 [全站 100% 消除 Emoji 与清除开发注释]**：
   - 全面扫描清洗前端组件与视图模板，将所有 `⚡`、`📋`、`💬`、`🤖`、`💡`、`⚠️`、`⚙️`、`✅`、`❌` 等 Emoji 符号彻底替换为 Hugeicons 与 Lucide 单线矢量 SVG 图标；
   - 彻底清除任何 `<!-- @TODO -->`、`// debug`、`node_state`、`mock_inventory` 等技术调试占位符与开发注释，确保呈现严谨纯粹的企业级生产力交互文案。
4. **Step 4 [shadcn 原子化组件拉取与双主题适配]**：
   - 部署 Vuebits 旗舰原子组件至 `src/components/ui/`，涵盖 `PromptBar`、`ThoughtLine`、`CallChip`、`StatusMark`、`VoicePill`、`GlideSelect`、`RubberSegment`、`LineSidebar`、`FolderFloat`、`WarmTooltip`、`ShinyText`、`FuseButton`，并做日间白色与夜间深色样式的深度拟合适配。
5. **Step 5 [输入交互区升维重构]**：
   - 将 `ChatInput.vue` 升级集成 `PromptBar` 与 `VoicePill`，打通 `@` 数据源菜单（企业知识库/MySQL）、`/` 内置指令菜单（/canvas, /audit）、模型切换（Claude 3.7 / GPT-4o / o3-mini）；
   - 绑定 `isStreaming` 状态使发送按钮在输入内容时充能 (`Ink Charge`)，在流式响应中自动形变为停止方块 (`Stop Square`)，无缝对接 `/api/v1/chat/abort`。
6. **Step 6 [深度思考与工具调用链重塑]**：
   - 将 `ThoughtBadge.vue` 重构为 `ThoughtLine.vue`，呼吸思索微光图标 + 实时秒表跳动 + 逐步展开推理步骤，思考完毕后通过模糊交叉淡入（Blur Crossfade）优雅收拢为 "Thought for X.Xs"；
   - 将工具调用（Qdrant 向量检索、Python 代码执行）渲染为 `CallChip.vue`，支持擦除进度动画与毫秒计时。
7. **Step 7 [侧边栏邻近微动与项目抽屉]**：
   - 改造 `Sidebar.vue`，集成 `LineSidebar.vue` 赋予历史会话光标邻近效应（Cursor Proximity Effect）；
   - 将知识库与制度中心重塑为 `FolderFloat.vue`，支持悬停翻盖倾斜与笔记浮动卡片云；
   - 顶部企业 Pro 标识引入 `ShinyText.vue` 金属流光。
8. **Step 8 [构建走查与证据归档]**：
   - 执行 `npm run build`，在 Chrome DevTools 走查日夜间双主题拟合、60 FPS 动效流畅度、0 Emoji 0 注释合规性与 WCAG AA 对比度，生成全套 8 大只读证据包并归档至 `.harness/runs/Sprint-F-09/`。

---

## 3. 验收门禁 (Acceptance Criteria & DoD)

1. `npm --prefix frontend run build` 100% 成功编译，产物无报错、无未定义依赖。
2. 全前端工程（所有 `.vue`, `.js`, `.css`）实现 **100% 零系统 Emoji**，全部统一为 Lucide / Hugeicons 矢量组件。
3. 全前端代码清除所有技术黑话调试注释与占位符。
4. 日间/夜间模式无缝切换，暗色正文对比度 $\ge 4.5:1$，日间正文对比度 $\ge 7:1$。
5. 8 大 Harness 只读证据包在 `.harness/runs/Sprint-F-09/` 完整落盘。
