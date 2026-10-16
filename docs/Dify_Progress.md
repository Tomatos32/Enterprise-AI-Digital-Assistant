# Dify & Local Ollama (Qwen) 接入与双模前端切换架构进展白皮书 (Dify_Progress)

> **项目名称**：企业级 AI 数字员工平台 (Enterprise AI Digital Assistant)  
> **当前开发阶段**：**HYBRID ORCHESTRATION & MODEL ADAPTATION MODE** (混合编排与开源模型适配阶段)  
> **核心目标**：本地部署 Ollama + 通义千问 Qwen 开源大模型，接入 Dify 编排平台，支持通过环境变量在「自研 Vue3 前端」与「Dify 托管前端」之间零代码平滑切换。  
> **参考基准**：[docs/PROJECT_PROGRESS.md](file:///g:/LLM_Learning/product/docs/PROJECT_PROGRESS.md) · [docs/FRONTEND_PROGRESS.md](file:///g:/LLM_Learning/product/docs/FRONTEND_PROGRESS.md) · [backend/core/llm.py](file:///g:/LLM_Learning/product/backend/core/llm.py)  
> **文档维护**：工程研发与架构组  
> **最后更新**：2026-10-08  

---

## 1. 架构总览与拓扑矩阵 (Architecture & Topology)

为了在开发阶段兼顾「Dify 可视化提示词/工作流敏捷调试」与「自研 Vue3 生产级人机协同/细粒度审批流体验」，系统采用**统一本地算力 + 双通道编排 + 双模前台**拓扑架构：

```text
               ┌────────────────────────────────────────────────────────┐
               │              本地算力层: Ollama (Qwen2.5)                │
               │   监听: 0.0.0.0:11434 (OpenAI-Compatible /v1 API)      │
               └───────────────────▲──────────────────▲─────────────────┘
                                   │                  │
                ┌──────────────────┴──┐            ┌──┴──────────────────┐
                │ Dify 本地容器编排平台  │            │ 本地 FastAPI+LangGraph │
                │ (端口 80 / 3001)    │            │ (端口 8000)          │
                └──────────▲──────────┘            └──────────▲──────────┘
                           │ (Dify WebApp / Iframe)           │ (原生 WS/REST)
               ┌───────────┴──────────────────────────────────┴──────────┐
               │              前端展现层 (Vue3 统一工作台)                  │
               │    环境变量 VITE_UI_MODE: [ custom | dify ] 自由切换      │
               └─────────────────────────────────────────────────────────┘
```

### 核心解耦与切换原则
1. **底层算力归一化**：Ollama 部署在宿主机，作为统一的 OpenAI 兼容端点（`11434/v1`），为 Dify 和自研 FastAPI 共同提供推理服务。
2. **状态与业务隔离**：
   - **自研链路**：Vue3 原生组件 ↔ WebSocket/REST ↔ FastAPI ↔ LangGraph 状态机（支持 Human-in-the-loop 三级审批阻断）。
   - **Dify 链路**：Vue3 容器视窗 ↔ Dify 嵌入式 WebApp ↔ Dify Server ↔ Ollama Qwen。
3. **零代码改动切换**：通过前端 `.env` 环境变量配置 `VITE_UI_MODE`，执行一条启动指令即可在两套交互视图之间平滑流转。

---

## 2. 本地 Ollama 与 Qwen 模型部署规程

### 2.1 Windows 环境关键网络配置（解决 Docker 通信隔离）
Windows 平台下 Ollama 默认仅绑定 `127.0.0.1`，会导致 Docker 内运行的 Dify 容器无法通信。必须在 Windows 系统环境变量中配置：

```powershell
# 允许所有网络接口访问（供 Docker 容器访问宿主机）
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")

# 允许跨域（供 Web 前端与 Dify 请求）
[System.Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "*", "User")

# 模型常驻显存时间（-1 为永不卸载，避免高频请求重复加载）
[System.Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "-1", "User")
```
*配置完成后，彻底退出系统托盘中的 Ollama 图标并重新启动 Ollama 服务。*

### 2.2 通义千问 Qwen2.5 模型选型与拉取指令

针对企业级智能体（Agent）场景中对「工具调用、指令遵循与长文本」的要求，制定如下阶梯选型规范：

| 模型规格 | 显存需求 (VRAM) | 推荐硬件环境 | 终端运行与拉取命令 | 适配开发场景 |
| :--- | :--- | :--- | :--- | :--- |
| **Qwen2.5-7B-Instruct** *(推荐基准)* | ~5.5 GB | RTX 3060 / 4060 (8G) | `ollama run qwen2.5:7b` | 日常本地极速联调、单元测试、简单 RAG |
| **Qwen2.5-14B-Instruct** | ~9.5 GB | RTX 3080 / 4070 (12G) | `ollama run qwen2.5:14b` | 复杂审批逻辑研判、长规章制度精准问答 |
| **Qwen2.5-32B-Instruct** | ~20 GB | RTX 3090 / 4090 (24G) | `ollama run qwen2.5:32b` | 接近云端闭源模型水准的高精度仿真 |

### 2.3 连通性与 OpenAI 兼容性核验
在终端执行以下校验，确认本地模型已就绪：
```bash
# 检查模型列表
curl http://localhost:11434/v1/models

# 简易对话测试
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b",
    "messages": [{"role": "user", "content": "你好，请确认你的模型版本。"}]
  }'
```

---

## 3. 后端对接 Ollama (FastAPI + LangGraph)

当前工程 `backend/core/llm.py` 内置了 `ResilientChatModel`，支持在外部 LLM 不可用时自动降级到 `LocalEnterpriseChatModel`，并天然预留了 `ollama` 协议转换。

### 3.1 配置文件更新 (`backend/.env` 或根目录 `.env`)
将大模型运行时直接指向本地 Ollama：

```ini
# ========== 本地大模型引擎配置 (Ollama + Qwen3.5) ==========
LLM_PROVIDER=ollama
LLM_MODEL=qwen3.5:2b
LLM_API_BASE=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=2048
LLM_STREAM=true

# 保持现有数据库与向量库环境不变
USE_MOCK_SYSTEMS=true
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

启动自研后端即可无缝生效：
```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Dify 接入 Ollama Qwen 并发布前端应用

### 4.1 启动 Dify 编排平台 (Docker Compose)
进入 Dify 源码的 docker 编排目录并后台启动：
```bash
cd dify/docker
docker compose up -d
```
启动完成后访问：`http://localhost` 完成初始化管理员账户设置。

### 4.2 Dify 配置 Ollama 模型提供商
1. 登录 Dify 管理后台 -> 右上角设置 -> **模型供应商 (Model Providers)**。
2. 找到 **Ollama**，点击「添加模型 (Add Model)」：
   - **模型类型**：`LLM`
   - **模型名称**：`qwen2.5:7b`
   - **基础 URL**：`http://host.docker.internal:11434` *(注意：Windows Docker 必须使用 host.docker.internal 访问宿主机)*
   - **最大 Token 数**：`4096`
3. 点击保存并通过校验（提示 Connection Succeeded）。

### 4.3 构建 Agent 应用并获取前端访问凭据
1. 在 Dify 中点击「创建空白应用」-> 类型选择 **Agent** 或 **Chatflow**。
2. 基础大模型选用刚才配置的 `qwen2.5:7b`。
3. 点击右上角 **发布 (Publish)** -> **更新 (Update)**。
4. 点击「概览 (Overview)」：
   - 提取 **公开访问链接 (WebApp URL)**：例如 `http://localhost/chatbot/ab12cd34ef56`
   - 提取 **API Key**（用于后续跨系统联动）：`app-xxxxxxxxxxxx`

---

## 5. 前端环境变量驱动双模切换实现规范 (Core Implementation)

### 5.1 前端环境配置文件矩阵

在 `frontend/` 目录下维护两套环境配置：

#### 文件 1：`frontend/.env.development` (默认自研前端模式)
```ini
# UI 模式: custom (自研 Vue3 ChatGPT/Copilot 前端)
VITE_UI_MODE=custom

# 自研后端接口代理
VITE_API_BASE=/api/v1

# 备用 Dify 访问地址 (供界面内手动切换)
VITE_DIFY_WEBAPP_URL=http://localhost/chat/your-dify-app-token
VITE_LLM_MODEL=qwen3.5:2b
```

#### 文件 2：`frontend/.env.dify` (Dify 托管前端模式)
```ini
# UI 模式: dify (Dify WebApp 托管前端)
VITE_UI_MODE=dify

# 默认加载的 Dify 应用 URL
VITE_DIFY_WEBAPP_URL=http://localhost/chat/your-dify-app-token
VITE_LLM_MODEL=qwen3.5:2b

VITE_API_BASE=/api/v1
```

---

### 5.2 Vue3 动态视窗容器组件实现 (`frontend/src/views/ChatView.vue`)

在主对话视图中，根据 `import.meta.env.VITE_UI_MODE` 自动渲染对应模式，并提供调试栏支持无重启快速预览：

```vue
<template>
  <div class="h-full w-full relative flex flex-col bg-bg-main overflow-hidden">
    <!-- 模式 A：Dify 托管 WebApp 视图 -->
    <div v-if="isDifyMode" class="w-full h-full flex flex-col relative">
      <!-- 顶部控制条：显示运行状态与便捷热切换 -->
      <div class="h-8 bg-brand-primary/10 border-b border-brand-primary/20 flex items-center justify-between px-4 text-xs text-brand-primary select-none z-10">
        <span class="flex items-center gap-1.5 font-medium">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          当前运行态: Dify 托管平台 (Local Qwen2.5 via Ollama)
        </span>
        <button 
          @click="toggleUIMode"
          class="hover:underline text-[11px] opacity-80 hover:opacity-100 cursor-pointer text-slate-300"
        >
          临时切回自研前端 ➔
        </button>
      </div>

      <!-- Dify 嵌入式沙盒 Iframe -->
      <iframe
        :src="difyUrl"
        class="w-full flex-1 border-none bg-slate-950"
        allow="microphone; camera; clipboard-write; clipboard-read"
      />
    </div>

    <!-- 模式 B：自研原生 Vue3 ChatGPT/Copilot 架构 -->
    <div v-else class="w-full h-full flex flex-col">
      <ChatContainer />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import ChatContainer from '../components/chat/ChatContainer.vue';

// 读取 Vite 环境变量
const initialMode = import.meta.env.VITE_UI_MODE || 'custom';
const difyUrl = import.meta.env.VITE_DIFY_WEBAPP_URL || 'http://localhost/chatbot';

// 动态响应式状态
const currentMode = ref(initialMode);
const isDifyMode = computed(() => currentMode.value === 'dify');

// 支持运行时免重启临时体验另一种模式
const toggleUIMode = () => {
  currentMode.value = currentMode.value === 'dify' ? 'custom' : 'dify';
};
</script>
```

---

### 5.3 脚本命令挂载 (`frontend/package.json`)

在 `frontend/package.json` 的 `scripts` 中增加专有启动命令：

```json
{
  "scripts": {
    "dev": "vite",
    "dev:dify": "vite --mode dify",
    "build": "vite build",
    "build:dify": "vite build --mode dify",
    "preview": "vite preview"
  }
}
```

---

## 6. 开发期快速验证与切换操作手册

```text
========================================================================================
场景 A: 日常业务迭代与自研功能研发 (使用自研 Vue3 消息流 + 本地 Qwen2.5)
----------------------------------------------------------------------------------------
1. 启动模型引擎 : ollama run qwen2.5:7b
2. 启动自研后端 : uvicorn backend.main:app --reload (使用 backend/.env 中 LLM_PROVIDER=ollama)
3. 启动前端工作台: npm run dev
4. 访问体验     : http://localhost:5173 (呈现自研沉浸式 Copilot 界面)

========================================================================================
场景 B: 编排调试与 Dify 原型对比 (切换为 Dify 前端 + 本地 Qwen2.5)
----------------------------------------------------------------------------------------
1. 确认 Dify 启动: cd dify/docker && docker compose up -d
2. 启动前端工作台: npm run dev:dify
3. 访问体验     : http://localhost:5173 (自动内嵌 Dify 托管应用，底层调用同一 Qwen 模型)
========================================================================================
```

---

## 7. 踩坑规避与生产加固要点 (Best Practices & Pitfalls)

1. **Docker 宿主机网络定位限制**：
   - Dify 容器内配置模型 URL 时，严禁填写 `http://localhost:11434` 或 `http://127.0.0.1:11434`（会指向 Dify 容器自身）。必须填写 `http://host.docker.internal:11434`。
2. **跨域与 CSP 阻断处理**：
   - 若 Iframe 加载 Dify 页面时报错 `Refused to display in a frame because it set 'X-Frame-Options' to 'sameorigin'`，请在 Dify 的 `docker/.env` 中配置：
     ```ini
     CONSOLE_CORS_ALLOW_ORIGINS=*
     WEB_API_CORS_ALLOW_ORIGINS=*
     ```
3. **显存竞争与 Ollama 并发保护**：
   - 当 Dify 与自研后端并发向本地 Ollama 发起请求时，本地显存可能出现排队或 OOM。建议在本地调试阶段将模型温度设为 `0.2`，最大 Token 限制为 `2048`，并确保没有启动其他占用大显存的本地进程。
4. **统一资产复用（进阶路线）**：
   - 自研知识库（Qdrant 向量库）与外部系统适配器（HR/ERP/OA）可继续在 FastAPI 封装为标准 OpenAPI 工具，并在 Dify 中作为「自定义工具 (Custom Tool)」注册，实现无论是自研界面还是 Dify 界面，均复用同一套企业级数据底座与审批流规则。
