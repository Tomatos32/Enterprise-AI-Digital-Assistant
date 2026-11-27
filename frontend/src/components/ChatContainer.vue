<template>
  <div class="flex flex-col h-full max-w-4xl mx-auto w-full px-3 sm:px-6 py-3 sm:py-4 font-sans relative">
    <!-- Chat Messages Scroll Container -->
    <main
      ref="chatBox"
      @scroll="handleScroll"
      class="flex-1 overflow-y-auto rounded-xl bg-bg-card border border-border-subtle relative scroll-smooth overscroll-contain"
      :class="
        preferencesStore.chatDensity === 'compact'
          ? 'space-y-3 p-3 sm:p-4'
          : 'space-y-5 p-4 sm:p-6'
      "
    >
      <!-- Minimalist Empty State with Neutral Architectural DotGridBackdrop -->
      <div
        v-if="messages.length === 0"
        class="h-full min-h-[360px] flex flex-col items-center justify-center text-center p-4 sm:p-8 relative overflow-hidden"
      >
        <DotGridBackdrop :gap="22" :dot-size="1" />

        <div class="relative z-10 flex flex-col items-center max-w-xl">
          <div class="w-11 h-11 rounded-xl bg-action-primary text-action-primary-fg flex items-center justify-center mb-4 shrink-0">
            <Bot class="w-5 h-5" />
          </div>

          <h3 class="text-base sm:text-lg font-semibold text-text-main tracking-tight">
            企业数字员工
          </h3>
          <p class="text-xs sm:text-sm text-text-secondary mt-1.5 mb-6">
            规章检索、工单协同与审批办理
          </p>

          <!-- Preset Quick Sample Prompts -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full">
            <button
              v-for="sample in samplePrompts"
              :key="sample"
              type="button"
              @click="sendSamplePrompt(sample)"
              class="btn-pressable px-3.5 py-2.5 text-left text-xs bg-bg-main hover:bg-bg-hover border border-border-card hover:border-border-strong text-text-secondary hover:text-text-main rounded-lg flex items-center justify-between gap-2 cursor-pointer"
            >
              <span class="line-clamp-1">{{ sample }}</span>
              <ArrowUpRight class="w-3.5 h-3.5 text-text-muted shrink-0" />
            </button>
          </div>
        </div>
      </div>

      <!-- Messages List -->
      <MessageItem
        v-for="msg in messages"
        :key="msg.id"
        :message="msg"
        @approvalAction="submitApprovalAction"
      />
    </main>

    <!-- Floating Scroll-To-Bottom Button -->
    <transition name="popover-up">
      <button
        v-if="!isAtBottom && messages.length > 0"
        type="button"
        @click="scrollToBottomManual"
        class="btn-secondary origin-bottom-right absolute bottom-24 sm:bottom-28 right-6 sm:right-10 z-20 px-3 py-1.5 rounded-full text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer shadow-sm"
        title="回到底部"
      >
        <ArrowDown class="w-3.5 h-3.5" />
        <span>最新消息</span>
      </button>
    </transition>

    <!-- Bottom Input Area -->
    <footer class="mt-3 w-full">
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
import { Bot, ArrowDown, ArrowUpRight } from 'lucide-vue-next';
import { useChatStream } from '../composables/useChatStream';
import { useChatStore } from '../stores/chatStore';
import { useAuthStore } from '../stores/authStore';
import { usePreferencesStore } from '../stores/preferencesStore';
import MessageItem from './chat/MessageItem.vue';
import ChatInput from './chat/ChatInput.vue';
import DotGridBackdrop from './ui/DotGridBackdrop.vue';

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
} = useChatStream();

const chatBox = ref(null);
const isAtBottom = ref(true);

watch(
  isConnected,
  (val) => {
    chatStore.isOnline = val;
  },
  { immediate: true }
);

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

watch(
  () => chatStore.activeSessionId,
  async (newId) => {
    if (newId) {
      await syncActiveSessionMessages(newId);
    }
  }
);

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

const handleScroll = () => {
  if (!chatBox.value) return;
  const { scrollTop, scrollHeight, clientHeight } = chatBox.value;
  const distanceToBottom = scrollHeight - scrollTop - clientHeight;
  isAtBottom.value = distanceToBottom < 60;
};

const autoScrollToBottom = async () => {
  await nextTick();
  if (chatBox.value && isAtBottom.value) {
    chatBox.value.scrollTop = chatBox.value.scrollHeight;
  }
};

const scrollToBottomManual = () => {
  if (chatBox.value) {
    chatBox.value.scrollTo({
      top: chatBox.value.scrollHeight,
      behavior: 'smooth',
    });
    isAtBottom.value = true;
  }
};

watch(messages, autoScrollToBottom, { deep: true });

const handleSend = async (payload) => {
  const text = typeof payload === 'string' ? payload : payload?.text || '';
  if (!text || isStreaming.value) return;

  if (!chatStore.activeSessionId) {
    await chatStore.createSession('新对话');
    if (chatStore.activeSessionId) {
      currentThreadId.value = chatStore.activeSessionId;
    }
  }

  if (
    chatStore.activeSession &&
    (chatStore.activeSession.title === '新对话' || !chatStore.activeSession.title)
  ) {
    const summary = text.slice(0, 18);
    const newTitle = summary.length >= 18 ? summary + '...' : summary;
    chatStore.renameSession(chatStore.activeSessionId, newTitle);
  }

  // Only forward explicit user directives (@data_source, /slash_command, model).
  // All tool & approval business slots are extracted purely on the backend.
  const customMetadata = {};
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

  isAtBottom.value = true;
  sendMessage(text, customMetadata, chatStore.activeSessionId);
};

const sendSamplePrompt = (promptText) => {
  handleSend(promptText);
};
</script>
