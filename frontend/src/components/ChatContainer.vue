<template>
  <div class="flex flex-col h-screen max-w-5xl mx-auto px-4 py-6 font-sans">
    <!-- Top Navigation Header -->
    <header class="glass-panel p-4 rounded-2xl flex items-center justify-between mb-4 border border-slate-800 shadow-xl">
      <!-- Title & Avatar -->
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
          <svg class="w-6 h-6 text-slate-950 font-bold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div>
          <h1 class="font-bold text-slate-100 text-base leading-tight">企业级 AI 数字人助手</h1>
          <p class="text-xs text-slate-400">WebSocket Duplex Streaming Studio (Sprint 8)</p>
        </div>
      </div>

      <!-- Control Bar: Status Indicator, Thread Selector & Clear -->
      <div class="flex items-center space-x-3">
        <!-- WS Status Badge -->
        <div class="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-medium border"
          :class="isConnected ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30' : 'bg-rose-950/40 text-rose-400 border-rose-500/30'"
        >
          <span class="w-2 h-2 rounded-full" :class="isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'"></span>
          <span>{{ isConnected ? 'WS 已连接' : '已断开' }}</span>
        </div>

        <!-- Thread ID Display -->
        <span class="hidden sm:inline-block px-2.5 py-1 text-xs font-mono bg-slate-900 text-slate-400 rounded-lg border border-slate-800">
          ID: {{ currentThreadId }}
        </span>

        <!-- Reset Chat Button -->
        <button
          @click="resetThread"
          title="清空当前对话"
          class="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-all cursor-pointer"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </header>

    <!-- Chat Messages Scroll Container -->
    <main ref="chatBox" class="flex-1 overflow-y-auto space-y-4 p-4 rounded-2xl glass-card border border-slate-800/80 scroll-smooth">
      <!-- Empty State Banner -->
      <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-center p-8">
        <div class="w-16 h-16 rounded-2xl bg-slate-900 flex items-center justify-center mb-4 text-emerald-400 border border-slate-800 shadow-inner">
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
        <h3 class="text-lg font-bold text-slate-200 mb-2">欢迎使用企业级数字人 AI 交互终端</h3>
        <p class="text-xs text-slate-400 max-w-md mb-6 leading-relaxed">
          依托 LangGraph 状态机、Hybrid 向量检索、5 核心企业工具及 Human-in-the-Loop 人机协同审批门禁。
        </p>

        <!-- Preset Quick Sample Questions Pills -->
        <div class="flex flex-wrap justify-center gap-2 max-w-lg">
          <button
            v-for="sample in samplePrompts"
            :key="sample"
            @click="sendSamplePrompt(sample)"
            class="px-3 py-1.5 text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-emerald-500/50 text-slate-300 hover:text-emerald-300 rounded-xl transition-all duration-200 shadow-sm cursor-pointer"
          >
            💡 {{ sample }}
          </button>
        </div>
      </div>

      <!-- Messages List -->
      <MessageBubble
        v-for="msg in messages"
        :key="msg.id"
        :message="msg"
        @approvalAction="submitApprovalAction"
      />
    </main>

    <!-- Bottom Fixed Input Bar -->
    <footer class="mt-4">
      <div class="glass-panel p-2.5 rounded-2xl border border-slate-800 shadow-2xl flex items-center space-x-2">
        <input
          v-model="inputQuery"
          @keyup.enter="handleSend"
          type="text"
          placeholder="请输入您的问题或指令（如：申请大额采购 MacBook Pro）..."
          :disabled="!isConnected || isStreaming"
          class="flex-1 px-4 py-2.5 bg-slate-900/90 text-slate-100 placeholder-slate-500 rounded-xl border border-slate-800 focus:outline-none focus:border-emerald-500 text-sm font-sans"
        />

        <!-- Stop Generation (Abort) Button if Streaming -->
        <button
          v-if="isStreaming"
          @click="abortChat"
          class="px-4 py-2.5 bg-rose-600 hover:bg-rose-500 text-white rounded-xl font-medium text-xs shadow-lg shadow-rose-600/20 transition-all flex items-center space-x-1.5 cursor-pointer"
        >
          <span class="w-2 h-2 rounded-sm bg-white animate-pulse"></span>
          <span>停止生成 (Abort)</span>
        </button>

        <!-- Send Button -->
        <button
          v-else
          @click="handleSend"
          :disabled="!isConnected || !inputQuery.trim()"
          class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-medium text-xs shadow-lg shadow-emerald-600/20 transition-all flex items-center space-x-1.5 cursor-pointer"
        >
          <span>发送消息</span>
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue';
import { useWebSocket } from '../composables/useWebSocket';
import MessageBubble from './MessageBubble.vue';

const {
  isConnected,
  isStreaming,
  messages,
  currentThreadId,
  sendMessage,
  abortChat,
  submitApprovalAction,
  resetThread
} = useWebSocket();

const inputQuery = ref('');
const chatBox = ref(null);

const samplePrompts = [
  '查询采购与审批SOP标准操作流程',
  '查询IT运维部员工张伟的岗位职级与联系方式',
  '创建P1级工单：核心数据库集群CPU打满',
  '申请大额设备采购：MacBook Pro 16 1台，单价 22999 元',
];

const scrollToBottom = async () => {
  await nextTick();
  if (chatBox.value) {
    chatBox.value.scrollTop = chatBox.value.scrollHeight;
  }
};

watch(messages, scrollToBottom, { deep: true });

const handleSend = () => {
  if (!inputQuery.value.trim() || isStreaming.value) return;

  const text = inputQuery.value.trim();
  inputQuery.value = '';

  // If purchase query, attach purchase_args metadata for approval node test
  let customMetadata = {};
  if (text.includes('MacBook') || text.includes('采购')) {
    customMetadata = {
      purchase_args: {
        item_name: 'MacBook Pro 16',
        quantity: 1,
        unit_price: 22999.0,
        department: '研发部',
        reason: 'AI 数字人研发高配置要求'
      }
    };
  }

  sendMessage(text, customMetadata);
};

const sendSamplePrompt = (promptText) => {
  inputQuery.value = promptText;
  handleSend();
};
</script>
