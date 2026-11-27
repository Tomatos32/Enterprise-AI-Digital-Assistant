<template>
  <div class="h-full w-full relative flex flex-col bg-bg-main overflow-hidden transition-colors duration-180">
    <!-- Mode A: Dify Managed WebApp Viewport -->
    <div v-if="isDifyMode" class="w-full h-full flex flex-col relative">
      <div class="h-10 bg-bg-card border-b border-border-subtle flex items-center justify-between px-4 text-xs select-none z-10 shrink-0">
        <div class="flex items-center gap-2">
          <span class="w-1.5 h-1.5 rounded-full bg-status-success shrink-0"></span>
          <span class="font-medium text-text-main">Dify 托管前台</span>
          <span class="px-1.5 py-0.5 text-[10px] rounded bg-bg-surface text-text-secondary border border-border-subtle font-mono">
            {{ modelName }}
          </span>
        </div>

        <div class="flex items-center gap-2.5">
          <a
            :href="difyUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="text-[11px] text-text-secondary hover:text-text-main inline-flex items-center gap-1 transition-colors duration-150"
            title="在新标签页打开"
          >
            <span class="hidden sm:inline">独立窗口</span>
            <ExternalLink class="w-3.5 h-3.5" />
          </a>

          <button
            type="button"
            @click="toggleUIMode"
            class="btn-secondary px-2.5 py-1 rounded-lg text-[11px] font-medium inline-flex items-center gap-1.5 cursor-pointer"
          >
            <ArrowRightLeft class="w-3 h-3" />
            <span>切回自研界面</span>
          </button>
        </div>
      </div>

      <div class="flex-1 w-full h-full relative bg-bg-main overflow-hidden">
        <iframe
          :src="difyUrl"
          class="w-full h-full border-none bg-bg-main"
          allow="microphone; camera; clipboard-write; clipboard-read"
        />
      </div>
    </div>

    <!-- Mode B: Native Self-Developed Vue3 + LangGraph Chat Container -->
    <div v-else class="w-full h-full flex flex-col relative">
      <div class="absolute top-3 right-4 z-20 hidden sm:flex items-center">
        <button
          type="button"
          @click="toggleUIMode"
          title="切换至 Dify 托管前台"
          class="btn-secondary px-2.5 py-1 rounded-full text-[11px] text-text-secondary hover:text-text-main inline-flex items-center gap-1.5 cursor-pointer"
        >
          <span>Dify 前台</span>
          <ArrowRightLeft class="w-3 h-3 text-text-muted" />
        </button>
      </div>

      <ChatContainer class="flex-1" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { ExternalLink, ArrowRightLeft } from 'lucide-vue-next';
import ChatContainer from '../components/ChatContainer.vue';

const initialMode = import.meta.env.VITE_UI_MODE || 'custom';
const difyUrl = import.meta.env.VITE_DIFY_WEBAPP_URL || 'http://localhost/chat/app-token';
const modelName = import.meta.env.VITE_LLM_MODEL || 'qwen3.5:2b';

const currentMode = ref(initialMode);
const isDifyMode = computed(() => currentMode.value === 'dify');

const toggleUIMode = () => {
  currentMode.value = currentMode.value === 'dify' ? 'custom' : 'dify';
};
</script>
