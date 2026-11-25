<template>
  <div class="flex flex-col h-full max-w-4xl mx-auto w-full px-2 sm:px-4 py-2 sm:py-4 font-sans relative">
    <!-- Chat Messages Scroll Container -->
    <main
      ref="chatBox"
      @scroll="handleScroll"
      class="flex-1 overflow-y-auto rounded-2xl glass-card border border-border-subtle relative scroll-smooth overscroll-contain transition-all duration-150"
      :class="
        preferencesStore.chatDensity === 'compact'
          ? 'space-y-2 sm:space-y-2.5 p-2 sm:p-3.5'
          : 'space-y-3.5 sm:space-y-5 p-2.5 sm:p-5'
      "
    >
      <!-- Empty State Banner -->
      <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-center p-4 sm:p-8">
        <div class="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-tr from-slate-900 to-slate-800 flex items-center justify-center mb-3 sm:mb-4 text-brand-primary border border-border-card shadow-lg shadow-blue-500/10 shrink-0">
          <Bot class="w-7 h-7 sm:w-8 sm:h-8 text-brand-primary animate-pulse" />
        </div>
        <h3 class="text-sm sm:text-lg font-bold text-text-main mb-1.5 sm:mb-2">欢迎使用企业级数字员工</h3>
        <p class="text-xs sm:text-sm text-text-secondary max-w-md mb-4 sm:mb-6 leading-relaxed">
          依托权威规章知识库、多智能体协同与人机协同审批门禁，为您提供严谨高效的业务支持。
        </p>

        <!-- Preset Quick Sample Questions Pills (Zero System Emoji, Mobile Friendly) -->
        <div class="flex flex-wrap justify-center gap-1.5 sm:gap-2 max-w-xl">
          <button
            v-for="sample in samplePrompts"
            :key="sample"
            @click="sendSamplePrompt(sample)"
            class="interactive-action px-3 py-2 min-h-[38px] text-[11px] sm:text-xs bg-bg-card/90 hover:bg-bg-hover dark:bg-slate-900/90 dark:hover:bg-slate-800 border border-border-subtle hover:border-brand-primary/50 text-text-secondary hover:text-text-main rounded-xl shadow-sm flex items-center space-x-1.5 transition-colors duration-150 cursor-pointer active:scale-[0.98]"
          >
            <Sparkles class="w-3.5 h-3.5 text-brand-primary shrink-0" />
            <span>{{ sample }}</span>
          </button>
        </div>
      </div>

      <!-- Messages List using Modern MessageItem -->
      <MessageItem
        v-for="msg in messages"
        :key="msg.id"
        :message="msg"
        @approvalAction="submitApprovalAction"
      />
    </main>

    <!-- Floating Scroll-To-Bottom Capsule Button -->
    <transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 translate-y-2 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-2 scale-95"
    >
      <button
        v-if="!isAtBottom && messages.length > 0"
        @click="scrollToBottomManual"
        class="interactive-action absolute bottom-24 sm:bottom-28 right-4 sm:right-8 z-20 px-3 py-1.5 rounded-full bg-bg-card/95 hover:bg-bg-hover dark:bg-slate-900/90 dark:hover:bg-slate-800 text-text-main border border-border-card shadow-2xl flex items-center space-x-1.5 text-xs transition-colors duration-150 cursor-pointer active:scale-95"
        title="快速回到底部"
      >
        <ArrowDown class="w-3.5 h-3.5 text-brand-primary animate-bounce" />
        <span class="font-medium text-text-main">最新消息</span>
      </button>
    </transition>

    <!-- Bottom Floating Capsule Input Area (Sprint F-04 Deliverable) -->
    <footer class="mt-2 w-full">
      <ChatInput
        :is-streaming="isStreaming"
        :disabled="!isConnected"
        @send="handleSend"
        @abort="abortChat"
      />
    </footer>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from 'vue';
import { Bot, Sparkles, ArrowDown } from 'lucide-vue-next';
import { useChatStream } from '../composables/useChatStream';
import { useChatStore } from '../stores/chatStore';
import { useAuthStore } from '../stores/authStore';
import { usePreferencesStore } from '../stores/preferencesStore';
import MessageItem from './chat/MessageItem.vue';
import ChatInput from './chat/ChatInput.vue';

const authStore = useAuthStore();
const chatStore = useChatStore();
const preferencesStore = usePreferencesStore();

const {
  isConnected,
  isStreaming,
  messages,
  currentThreadId,
  sendMessage,
  abortChat,
  submitApprovalAction,
  resetThread
} = useChatStream();

const chatBox = ref(null);
const isAtBottom = ref(true);

// 保持全局网络状态同步
watch(isConnected, (val) => {
  chatStore.isOnline = val;
}, { immediate: true });

let lastSyncedSessionId = '';

const syncActiveSessionMessages = async (sessionId) => {
  if (!sessionId) return;
  if (lastSyncedSessionId === sessionId && messages.value.length > 0) return;
  lastSyncedSessionId = sessionId;
  currentThreadId.value = sessionId;
  isStreaming.value = false;
  const history = await chatStore.loadSessionMessages(sessionId);
  if (chatStore.activeSessionId !== sessionId) return;
  messages.value = history || [];
  autoScrollToBottom();
};

// 保持活跃会话与当前 threadId 同步并拉取历史记录
watch(() => chatStore.activeSessionId, async (newId) => {
  if (newId) {
    await syncActiveSessionMessages(newId);
  }
});

// 监听当前登录身份切换，清理当前对话流状态等待会话切换自动同步
watch(
  () => authStore.currentUsername,
  (newUser, oldUser) => {
    if (newUser === oldUser) return;
    lastSyncedSessionId = '';
    isStreaming.value = false;
    messages.value = [];
  }
);

onMounted(async () => {
  await authStore.ensureSession();
  await chatStore.fetchSessions();
  if (chatStore.activeSessionId) {
    await syncActiveSessionMessages(chatStore.activeSessionId);
  }
});

const samplePrompts = [
  '查询采购与审批SOP标准操作流程',
  '查询IT运维部员工张伟的岗位职级与联系方式',
  '创建P1级工单：核心数据库集群CPU打满',
  '申请大额设备采购：MacBook Pro 16 1台，单价 22999 元',
];

// 检测用户滚动位置
const handleScroll = () => {
  if (!chatBox.value) return;
  const { scrollTop, scrollHeight, clientHeight } = chatBox.value;
  const distanceToBottom = scrollHeight - scrollTop - clientHeight;
  isAtBottom.value = distanceToBottom < 60;
};

// 自动贴底（仅当用户处于底部时执行，防拉扯打扰保护）
const autoScrollToBottom = async () => {
  await nextTick();
  if (chatBox.value && isAtBottom.value) {
    chatBox.value.scrollTop = chatBox.value.scrollHeight;
  }
};

// 手动平滑贴底
const scrollToBottomManual = () => {
  if (chatBox.value) {
    chatBox.value.scrollTo({
      top: chatBox.value.scrollHeight,
      behavior: 'smooth'
    });
    isAtBottom.value = true;
  }
};

// 监听消息变化进行平滑贴底
watch(messages, autoScrollToBottom, { deep: true });

const handleSend = async (payload) => {
  const text = typeof payload === 'string' ? payload : (payload?.text || '');
  if (!text || isStreaming.value) return;

  if (!chatStore.activeSessionId) {
    await chatStore.createSession('新对话');
    if (chatStore.activeSessionId) {
      currentThreadId.value = chatStore.activeSessionId;
    }
  }

  // 自动将首条消息同步作为会话标题
  if (chatStore.activeSession && (chatStore.activeSession.title === '新对话' || !chatStore.activeSession.title)) {
    const summary = text.slice(0, 18);
    const newTitle = summary.length >= 18 ? summary + '...' : summary;
    chatStore.renameSession(chatStore.activeSessionId, newTitle);
  }

  // 透传数据源 (@) 与快捷指令 (/) 元数据供后端混合认知路由器对齐
  let customMetadata = {};
  if (typeof payload === 'object' && payload.source) {
    customMetadata.data_source = payload.source;
  }
  if (typeof payload === 'object' && payload.sourceId) {
    customMetadata.data_source_id = payload.sourceId;
  }
  if (typeof payload === 'object' && payload.slashCommand) {
    customMetadata.slash_command = payload.slashCommand;
  }
  if (typeof payload === 'object' && payload.model) {
    customMetadata.model = payload.model;
  }
  if (text.includes('MacBook') || text.includes('采购')) {
    customMetadata.purchase_args = {
      item_name: 'MacBook Pro 16',
      quantity: 1,
      unit_price: 22999.0,
      department: authStore.department,
      applicant: authStore.displayName,
      reason: 'AI 数字人研发高配置要求'
    };
  }

  // 发送后强制保证处于底部
  isAtBottom.value = true;
  sendMessage(text, customMetadata, chatStore.activeSessionId);
};

const sendSamplePrompt = (promptText) => {
  handleSend(promptText);
};
</script>
