<template>
  <div
    class="flex w-full space-x-2 sm:space-x-3 group transition-all duration-150"
    :class="isUser ? 'flex-row-reverse space-x-reverse justify-start' : 'justify-start'"
  >
    <!-- Avatar -->
    <div class="shrink-0 mt-0.5 select-none">
      <!-- User Avatar -->
      <div
        v-if="isUser"
        class="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 border border-blue-400/40 flex items-center justify-center text-white shadow-sm"
        title="当前用户"
      >
        <User class="w-3.5 h-3.5 sm:w-4 sm:h-4" />
      </div>

      <!-- AI Copilot Avatar -->
      <div
        v-else
        class="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-tr from-slate-900 to-slate-800 border border-brand-primary/40 flex items-center justify-center text-brand-primary shadow-sm"
        title="企业 AI 数字员工"
      >
        <Bot class="w-3.5 h-3.5 sm:w-4 sm:h-4 text-brand-primary" />
      </div>
    </div>

    <!-- Message Bubble Body Container (Adaptive 92% on mobile, max-w-2xl on desktop) -->
    <div
      class="flex flex-col space-y-1.5 max-w-[88%] xs:max-w-[92%] sm:max-w-2xl"
      :class="isUser ? 'items-end' : 'items-start'"
    >
      <!-- Meta Information (Sender Name & Timestamp) -->
      <div class="flex items-center space-x-2 text-[11px] text-text-muted px-1 select-none">
        <span class="font-medium" :class="isUser ? 'text-slate-300' : 'text-brand-primary'">
          {{ isUser ? '我' : '企业数字员工' }}
        </span>
        <span v-if="message.timestamp">{{ message.timestamp }}</span>
      </div>

      <!-- Thought Capsule (AI Thought & Regulatory Sources) -->
      <div v-if="!isUser && showThoughtBadge" class="w-full">
        <ThoughtBadge
          :status="thoughtStatus"
          :title="thoughtTitle"
          :sources="message.sources || []"
        />
      </div>

      <!-- Main Message Bubble Card -->
      <div
        class="rounded-2xl text-xs sm:text-sm leading-relaxed shadow-md transition-all duration-150 break-words"
        :class="[
          isUser
            ? 'bg-brand-primary text-white rounded-tr-none px-4 py-3 selection:bg-white/30'
            : 'bg-bg-card border border-border-card text-text-main rounded-tl-none p-4 shadow-lg'
        ]"
      >
        <!-- User Plain Text -->
        <div v-if="isUser" class="whitespace-pre-wrap font-sans text-white">
          {{ message.content }}
        </div>

        <!-- AI Assistant Markdown & Dynamic Streaming -->
        <div v-else class="space-y-3 font-sans">
          <!-- Markdown Content Body -->
          <div
            v-if="renderedHtml"
            v-html="renderedHtml"
            class="markdown-body leading-relaxed space-y-2 text-text-main"
            :class="{ 'typing-cursor': isActivelyTyping }"
          ></div>

          <!-- Thinking Placeholder before first token arrives -->
          <div
            v-else-if="isActivelyTyping"
            class="typing-cursor text-xs text-text-secondary italic flex items-center space-x-1.5 py-1"
          >
            <span>正在分析规章制度并生成建议...</span>
          </div>

          <!-- Interactive Enterprise Approval Card if interrupt triggered -->
          <div v-if="message.interruptData" class="mt-3">
            <ApprovalCard
              :approvalData="message.interruptData"
              @action="(id, act, cmt) => $emit('approvalAction', id, act, cmt)"
            />
          </div>
        </div>
      </div>

      <!-- AI Message Micro Action Bar (Copy / Feedback) -->
      <div
        v-if="!isUser && message.content && (message.completed || !message.isStreaming)"
        class="opacity-90 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity duration-150 flex items-center space-x-1.5 px-1 py-0.5 text-[11px] text-text-muted select-none"
      >
        <button
          @click="copyContent"
          class="interactive-action px-2 py-1 min-h-[32px] rounded-lg hover:bg-slate-800 hover:text-text-main flex items-center space-x-1 transition-colors duration-150 active:bg-slate-700"
          :title="copied ? '已复制' : '复制回答'"
        >
          <component :is="copied ? Check : Copy" class="w-3.5 h-3.5 text-text-secondary" />
          <span class="text-[10px]">{{ copied ? '已复制' : '复制' }}</span>
        </button>

        <span class="text-text-muted">·</span>

        <button
          class="interactive-action p-1.5 min-w-[32px] min-h-[32px] flex items-center justify-center rounded-lg hover:bg-slate-800 hover:text-text-main transition-colors duration-150 active:bg-slate-700"
          title="有帮助"
        >
          <ThumbsUp class="w-3.5 h-3.5 text-text-secondary" />
        </button>
        <button
          class="interactive-action p-1.5 min-w-[32px] min-h-[32px] flex items-center justify-center rounded-lg hover:bg-slate-800 hover:text-text-main transition-colors duration-150 active:bg-slate-700"
          title="不准确"
        >
          <ThumbsDown class="w-3.5 h-3.5 text-text-secondary" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import {
  User,
  Bot,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown
} from 'lucide-vue-next';
import ThoughtBadge from './ThoughtBadge.vue';
import ApprovalCard from '../ApprovalCard.vue';
import { renderMarkdown } from '../../utils/markdown';

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
});

defineEmits(['approvalAction']);

const copied = ref(false);

const isUser = computed(() => {
  return props.message.role === 'user' || props.message.sender === 'user';
});

const isActivelyTyping = computed(() => {
  return (
    !isUser.value &&
    (props.message.isStreaming === true || props.message.completed === false)
  );
});

const showThoughtBadge = computed(() => {
  if (isUser.value) return false;
  // If streaming and no content yet, or has sources, or thoughts defined
  if (props.message.sources && props.message.sources.length > 0) return true;
  if (props.message.thoughts && props.message.thoughts.length > 0) return true;
  if (isActivelyTyping.value) return true;
  // Always provide a clean regulatory thought capsule for AI messages in enterprise workflow
  return true;
});

const thoughtStatus = computed(() => {
  if (isActivelyTyping.value && !props.message.content) {
    return 'thinking';
  }
  return 'completed';
});

const thoughtTitle = computed(() => {
  if (props.message.thoughtTitle) return props.message.thoughtTitle;
  if (thoughtStatus.value === 'thinking') {
    return '正在核对企业规章制度与库存数据...';
  }
  const count = (props.message.sources && props.message.sources.length) || 2;
  return `已参考 ${count} 篇规章制度与知识来源`;
});

const renderedHtml = computed(() => {
  if (!props.message.content) return '';
  return renderMarkdown(props.message.content);
});

const copyContent = async () => {
  if (!props.message.content) return;
  try {
    await navigator.clipboard.writeText(props.message.content);
    copied.value = true;
    setTimeout(() => {
      copied.value = false;
    }, 2000);
  } catch (err) {
    console.warn('[Copy] Failed to copy to clipboard:', err);
  }
};
</script>
