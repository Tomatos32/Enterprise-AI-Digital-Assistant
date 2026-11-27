<template>
  <div class="flex flex-col gap-1.5" :class="isUser ? 'items-end' : 'items-start'">
    <div class="flex items-center gap-2 text-xs text-text-muted px-0.5">
      <span class="font-medium text-text-secondary">
        {{ isUser ? '我' : '企业数字员工' }}
      </span>
      <span class="tabular-nums">{{ message.timestamp }}</span>
    </div>

    <div
      class="max-w-2xl p-3.5 rounded-xl text-sm leading-relaxed relative group"
      :class="[
        isUser
          ? 'bg-action-primary text-action-primary-fg rounded-br-sm'
          : 'bg-bg-surface text-text-main rounded-bl-sm border border-border-subtle'
      ]"
    >
      <div v-if="isUser" class="whitespace-pre-wrap font-sans">
        {{ message.content }}
      </div>

      <div v-else class="space-y-3">
        <div
          class="whitespace-pre-wrap font-sans text-text-main"
          :class="{ 'typing-cursor': !message.completed && message.content }"
        >
          {{ message.content || (message.completed ? '' : '正在生成回复...') }}
        </div>

        <ApprovalCard
          v-if="message.interruptData"
          :approvalData="message.interruptData"
          @action="(id, act, cmt) => $emit('approvalAction', id, act, cmt)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import ApprovalCard from './ApprovalCard.vue';

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
});

defineEmits(['approvalAction']);

const isUser = computed(() => props.message.sender === 'user');
</script>
