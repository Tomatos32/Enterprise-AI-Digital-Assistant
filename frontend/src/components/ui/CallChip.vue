<template>
  <div
    class="inline-flex items-center space-x-2 px-2.5 py-1 rounded-xl text-xs font-medium border backdrop-blur-md transition-all duration-200 select-none overflow-hidden relative shadow-sm"
    :class="containerClasses"
  >
    <!-- Wipe Progress Bar Animation for Running State -->
    <div
      v-if="status === 'running'"
      class="absolute inset-0 bg-blue-500/10 pointer-events-none animate-shimmer"
      style="background-size: 200% 100%; background-image: linear-gradient(90deg, transparent 0%, rgba(59, 130, 246, 0.2) 50%, transparent 100%);"
    ></div>

    <!-- Status Icon -->
    <div class="shrink-0 flex items-center justify-center">
      <svg
        v-if="status === 'running'"
        class="animate-spin w-3.5 h-3.5 text-brand-primary"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
      </svg>
      <CheckCircle2 v-else-if="status === 'success'" class="w-3.5 h-3.5 text-emerald-500" />
      <AlertCircle v-else class="w-3.5 h-3.5 text-rose-500" />
    </div>

    <!-- Tool Name & Input Description -->
    <span class="font-semibold text-text-main truncate max-w-[180px]">{{ toolLabel }}</span>
    <span v-if="inputSummary" class="text-text-muted truncate max-w-[140px] text-[11px]">{{ inputSummary }}</span>

    <!-- Duration Counter -->
    <span v-if="durationMs" class="text-[10px] text-text-secondary tabular-nums font-mono px-1 py-0.2 rounded bg-slate-200 dark:bg-slate-800">
      {{ durationMs }}ms
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { CheckCircle2, AlertCircle } from 'lucide-vue-next';

const props = defineProps({
  toolName: {
    type: String,
    required: true,
  },
  status: {
    type: String,
    default: 'running',
    validator: (v) => ['running', 'success', 'error'].includes(v),
  },
  durationMs: {
    type: Number,
    default: null,
  },
  inputSummary: {
    type: String,
    default: '',
  },
});

const toolLabel = computed(() => {
  switch (props.toolName) {
    case 'qdrant_retrieval':
    case 'vector_search':
      return '企业向量检索';
    case 'database_query':
    case 'sql_query':
      return '业务数据查询';
    case 'erp_check':
      return 'ERP 库存核验';
    case 'hr_lookup':
      return '组织架构查询';
    case 'approval_initiate':
      return '发起审批流';
    default:
      return props.toolName;
  }
});

const containerClasses = computed(() => {
  switch (props.status) {
    case 'success':
      return 'bg-emerald-500/5 dark:bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300';
    case 'error':
      return 'bg-rose-500/5 dark:bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300 animate-shake';
    case 'running':
    default:
      return 'bg-blue-500/5 dark:bg-blue-500/10 border-blue-500/30 text-blue-700 dark:text-blue-300';
  }
});
</script>
