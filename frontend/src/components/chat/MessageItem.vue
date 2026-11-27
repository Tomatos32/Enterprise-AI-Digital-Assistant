<template>
  <div
    class="flex w-full gap-2.5 sm:gap-3 group"
    :class="isUser ? 'flex-row-reverse justify-start' : 'justify-start'"
  >
    <!-- Avatar -->
    <div class="shrink-0 mt-0.5 select-none">
      <div
        v-if="isUser"
        class="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-action-primary text-action-primary-fg flex items-center justify-center"
        title="当前用户"
      >
        <User class="w-3.5 h-3.5 sm:w-4 sm:h-4" />
      </div>

      <div
        v-else
        class="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-bg-surface border border-border-card flex items-center justify-center text-text-main"
        title="企业数字员工"
      >
        <Bot class="w-3.5 h-3.5 sm:w-4 sm:h-4" />
      </div>
    </div>

    <!-- Message Body -->
    <div
      class="flex flex-col gap-1.5 max-w-[88%] sm:max-w-2xl min-w-0"
      :class="isUser ? 'items-end' : 'items-start'"
    >
      <div class="flex items-center gap-2 text-[11px] text-text-muted px-0.5 select-none">
        <span class="font-medium text-text-secondary">
          {{ isUser ? '我' : '企业数字员工' }}
        </span>
        <span v-if="message.timestamp" class="tabular-nums">{{ message.timestamp }}</span>
      </div>

      <!-- Thought & Sources Accordion -->
      <div v-if="!isUser && showThoughtBadge" class="w-full">
        <ThoughtBadge
          :status="thoughtStatus"
          :title="thoughtTitle"
          :sources="message.sources || []"
          :thought-text="message.thought || ''"
          :duration-seconds="message.durationSeconds"
          :thought-steps="message.nodeSteps || []"
          :tool-calls="message.toolLogs || []"
        />
      </div>

      <!-- Bubble Card -->
      <div
        class="rounded-xl text-xs sm:text-sm leading-relaxed break-words"
        :class="[
          isUser
            ? (preferencesStore.chatDensity === 'compact'
                ? 'bg-action-primary text-action-primary-fg rounded-tr-sm px-3 py-2'
                : 'bg-action-primary text-action-primary-fg rounded-tr-sm px-4 py-2.5')
            : (preferencesStore.chatDensity === 'compact'
                ? 'bg-bg-surface border border-border-subtle text-text-main rounded-tl-sm p-3'
                : 'bg-bg-surface border border-border-subtle text-text-main rounded-tl-sm p-4')
        ]"
      >
        <div v-if="isUser" class="whitespace-pre-wrap font-sans">
          {{ message.content }}
        </div>

        <div v-else class="space-y-3 font-sans">
          <div
            v-if="renderedHtml"
            v-html="renderedHtml"
            class="markdown-body leading-relaxed space-y-2 text-text-main"
            :class="{ 'typing-cursor': isActivelyTyping }"
          ></div>

          <div
            v-else-if="isActivelyTyping"
            class="typing-cursor text-xs text-text-secondary py-0.5"
          >
            <span>正在生成回复...</span>
          </div>

          <div v-if="message.interruptData" class="mt-3">
            <ApprovalCard
              :approvalData="message.interruptData"
              @action="(id, act, cmt) => $emit('approvalAction', id, act, cmt)"
            />
          </div>
        </div>
      </div>

      <!-- Micro Action Bar -->
      <div
        v-if="!isUser && message.content && (message.completed || !message.isStreaming)"
        class="opacity-90 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity duration-150 flex items-center gap-1 px-0.5 text-[11px] text-text-muted select-none"
      >
        <button
          type="button"
          @click="copyContent"
          class="btn-pressable px-2 py-1 min-h-[28px] rounded-md hover:bg-bg-hover hover:text-text-main inline-flex items-center gap-1 cursor-pointer"
          :title="copied ? '已复制' : '复制回答'"
        >
          <component :is="copied ? Check : Copy" class="w-3.5 h-3.5" />
          <span class="text-[11px]">{{ copied ? '已复制' : '复制' }}</span>
        </button>

        <button
          type="button"
          class="btn-pressable p-1.5 min-w-[28px] min-h-[28px] flex items-center justify-center rounded-md hover:bg-bg-hover hover:text-text-main cursor-pointer"
          title="有帮助"
        >
          <ThumbsUp class="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          class="btn-pressable p-1.5 min-w-[28px] min-h-[28px] flex items-center justify-center rounded-md hover:bg-bg-hover hover:text-text-main cursor-pointer"
          title="不准确"
        >
          <ThumbsDown class="w-3.5 h-3.5" />
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
  ThumbsDown,
} from 'lucide-vue-next';
import ThoughtBadge from './ThoughtBadge.vue';
import ApprovalCard from '../ApprovalCard.vue';
import { renderMarkdown } from '../../utils/markdown';
import { usePreferencesStore } from '../../stores/preferencesStore';

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
});

defineEmits(['approvalAction']);

const preferencesStore = usePreferencesStore();
const copied = ref(false);

const isUser = computed(() => props.message.role === 'user');

const isActivelyTyping = computed(
  () => !isUser.value && props.message.isStreaming && !props.message.completed
);

const showThoughtBadge = computed(() => {
  if (isUser.value) return false;
  return (
    props.message.isThinking ||
    (props.message.isStreaming && !props.message.content) ||
    !!props.message.thought ||
    (props.message.sources && props.message.sources.length > 0) ||
    (props.message.toolLogs && props.message.toolLogs.length > 0)
  );
});

const thoughtStatus = computed(() => {
  if (props.message.isThinking || (props.message.isStreaming && !props.message.content)) {
    return 'thinking';
  }
  return 'completed';
});

const thoughtTitle = computed(() => {
  if (thoughtStatus.value === 'thinking') {
    return '正在分析与检索...';
  }
  const count = (props.message.sources || []).length;
  return count > 0 ? `参考了 ${count} 篇制度` : '';
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
  } catch {
    // ignore clipboard error
  }
};
</script>
