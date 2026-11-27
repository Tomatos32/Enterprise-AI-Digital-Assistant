<template>
  <div
    class="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg text-xs font-medium border bg-bg-card border-border-card text-text-main select-none"
  >
    <!-- Status Icon -->
    <div class="shrink-0 flex items-center justify-center">
      <svg
        v-if="status === 'running'"
        class="animate-spin w-3.5 h-3.5 text-text-secondary"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
      </svg>
      <CheckCircle2 v-else-if="status === 'success'" class="w-3.5 h-3.5 text-status-success" />
      <XCircle v-else class="w-3.5 h-3.5 text-status-danger" />
    </div>

    <span class="font-medium text-text-main truncate max-w-[180px]">{{ toolLabel }}</span>
    <span v-if="inputSummary" class="text-text-muted truncate max-w-[140px] text-[11px]">{{ inputSummary }}</span>

    <span
      v-if="durationMs"
      class="text-[10px] text-text-secondary tabular-nums font-mono px-1.5 py-0.5 rounded bg-bg-surface border border-border-subtle"
    >
      {{ durationMs }}ms
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { CheckCircle2, XCircle } from 'lucide-vue-next';

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
      return '制度向量检索';
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
</script>
