<template>
  <div class="flex flex-col space-y-2" :class="isUser ? 'items-end' : 'items-start'">
    <!-- Sender Badge & Time -->
    <div class="flex items-center space-x-2 text-xs text-slate-400 px-1">
      <span class="font-semibold" :class="isUser ? 'text-emerald-400' : 'text-cyan-400'">
        {{ isUser ? '用户 (You)' : 'AI 数字人助手' }}
      </span>
      <span>{{ message.timestamp }}</span>
    </div>

    <!-- Node Transition Step Badges (For AI Messages) -->
    <div v-if="!isUser && message.nodeSteps && message.nodeSteps.length > 0" class="flex flex-wrap gap-1.5 my-1">
      <span
        v-for="node in message.nodeSteps"
        :key="node"
        class="px-2 py-0.5 text-[10px] font-mono font-medium rounded-md border transition-all duration-200"
        :class="getNodeBadgeClass(node)"
      >
        ● {{ node.toUpperCase() }}
      </span>
    </div>

    <!-- Main Message Bubble Container -->
    <div
      class="max-w-2xl p-4 rounded-2xl text-sm leading-relaxed shadow-lg relative group transition-all duration-200"
      :class="[
        isUser
          ? 'bg-emerald-600 text-white rounded-br-none'
          : 'glass-panel text-slate-200 rounded-bl-none border border-slate-800'
      ]"
    >
      <!-- User Message Content -->
      <div v-if="isUser" class="whitespace-pre-wrap font-sans">
        {{ message.content }}
      </div>

      <!-- AI Streaming / Complete Message Content -->
      <div v-else class="space-y-3">
        <!-- Content Text -->
        <div
          class="whitespace-pre-wrap font-sans text-slate-100"
          :class="{ 'typing-cursor': !message.completed && message.content }"
        >
          {{ message.content || (message.completed ? '' : '正在分析意图并思考中...') }}
        </div>

        <!-- Tool Execution Step Logs Card -->
        <div v-if="message.toolLogs && message.toolLogs.length > 0" class="mt-2 space-y-1.5">
          <div
            v-for="(log, idx) in message.toolLogs"
            :key="idx"
            class="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs font-mono"
          >
            <div class="flex items-center justify-between text-cyan-300">
              <span class="font-bold flex items-center space-x-1">
                <svg class="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span>Tool: {{ log.tool }}</span>
              </span>
              <span class="text-[10px] text-slate-500">{{ log.timestamp }}</span>
            </div>
            <div class="mt-1 text-slate-400 text-[11px] truncate">
              Arg: {{ JSON.stringify(log.input) }}
            </div>
            <div v-if="log.output" class="mt-1 text-emerald-400/90 text-[11px] truncate">
              Result: {{ log.output }}
            </div>
          </div>
        </div>

        <!-- Approval Card Component if Interrupt Triggered -->
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

const getNodeBadgeClass = (node) => {
  switch (node) {
    case 'router':
      return 'bg-purple-950/60 text-purple-300 border-purple-800';
    case 'retrieve':
      return 'bg-blue-950/60 text-blue-300 border-blue-800';
    case 'tool':
      return 'bg-amber-950/60 text-amber-300 border-amber-800';
    case 'approval':
      return 'bg-rose-950/60 text-rose-300 border-rose-800';
    case 'generate':
      return 'bg-emerald-950/60 text-emerald-300 border-emerald-800';
    default:
      return 'bg-slate-800 text-slate-300 border-slate-700';
  }
};
</script>
