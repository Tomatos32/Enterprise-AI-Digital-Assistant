<template>
  <div class="h-full w-full relative flex flex-col bg-bg-main overflow-hidden">
    <!-- Mode A: Dify Managed WebApp Viewport -->
    <div v-if="isDifyMode" class="w-full h-full flex flex-col relative">
      <!-- Top Status Control Bar -->
      <div class="h-9 bg-slate-900/90 border-b border-border-subtle flex items-center justify-between px-3 sm:px-4 text-xs select-none z-10 shrink-0">
        <div class="flex items-center space-x-2">
          <span class="flex h-2 w-2 relative">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span class="font-semibold text-text-main flex items-center gap-1.5">
            <span>Dify 托管前台</span>
            <span class="px-1.5 py-0.5 text-[10px] rounded bg-brand-primary/20 text-brand-primary border border-brand-primary/30 font-mono">
              {{ modelName }}
            </span>
          </span>
          <span class="hidden md:inline text-text-muted text-[11px]">| 本地 Ollama 驱动</span>
        </div>

        <div class="flex items-center space-x-2 sm:space-x-3">
          <!-- External New Tab Link -->
          <a
            :href="difyUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="text-[11px] text-text-secondary hover:text-text-main flex items-center gap-1 transition-colors duration-150"
            title="在新标签页中打开 Dify 原生页面"
          >
            <span class="hidden sm:inline">独立窗口</span>
            <ExternalLink class="w-3.5 h-3.5 text-text-muted hover:text-text-secondary" />
          </a>

          <!-- Hot Mode Toggle Button -->
          <button
            @click="toggleUIMode"
            class="interactive-action px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-border-subtle text-text-main text-[11px] font-medium flex items-center gap-1.5 transition-colors duration-150 cursor-pointer active:scale-95 shadow-sm"
          >
            <ArrowRightLeft class="w-3 h-3 text-brand-primary" />
            <span>切回自研界面</span>
          </button>
        </div>
      </div>

      <!-- Dify Iframe Sandboxed Workspace -->
      <div class="flex-1 w-full h-full relative bg-slate-950 overflow-hidden">
        <iframe
          :src="difyUrl"
          class="w-full h-full border-none bg-slate-950"
          allow="microphone; camera; clipboard-write; clipboard-read"
        />
      </div>
    </div>

    <!-- Mode B: Native Self-Developed Vue3 + LangGraph Chat Container -->
    <div v-else class="w-full h-full flex flex-col relative">
      <!-- Lightweight Switcher Pill (Floating in Custom Mode) -->
      <div class="absolute top-2 right-4 z-20 hidden sm:flex items-center">
        <button
          @click="toggleUIMode"
          title="切换至 Dify 托管体验前台"
          class="interactive-action px-2.5 py-1 rounded-full bg-slate-900/80 hover:bg-slate-800/90 border border-border-subtle hover:border-brand-primary/40 text-[11px] text-text-secondary hover:text-text-main flex items-center space-x-1.5 shadow-md backdrop-blur-sm transition-all duration-150 cursor-pointer active:scale-95"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
          <span>Dify 前台</span>
          <ArrowRightLeft class="w-3 h-3 text-text-muted" />
        </button>
      </div>

      <!-- Self-Developed Chat Container Component -->
      <ChatContainer class="flex-1" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { ExternalLink, ArrowRightLeft } from 'lucide-vue-next';
import ChatContainer from '../components/ChatContainer.vue';

// 1. 读取 Vite 环境变量
const initialMode = import.meta.env.VITE_UI_MODE || 'custom';
const difyUrl = import.meta.env.VITE_DIFY_WEBAPP_URL || 'http://localhost/chat/app-token';
const modelName = import.meta.env.VITE_LLM_MODEL || 'qwen3.5:2b';

// 2. 响应式控制模式状态（支持运行时无刷新热切换）
const currentMode = ref(initialMode);
const isDifyMode = computed(() => currentMode.value === 'dify');

// 3. 运行时切换模式
const toggleUIMode = () => {
  currentMode.value = currentMode.value === 'dify' ? 'custom' : 'dify';
};
</script>
