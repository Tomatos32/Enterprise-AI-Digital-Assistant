<template>
  <div class="inline-flex items-center space-x-1.5" :title="label">
    <span class="relative flex" :class="sizeClass">
      <span
        v-if="status === 'running' || status === 'warning'"
        class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
        :class="pingColorClass"
      ></span>
      <span class="relative inline-flex rounded-full h-full w-full" :class="dotColorClass"></span>
    </span>
    <span v-if="label" class="text-xs font-medium" :class="textColorClass">
      {{ label }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  status: {
    type: String,
    default: 'idle',
    validator: (v) => ['idle', 'running', 'success', 'warning', 'danger'].includes(v),
  },
  size: {
    type: String,
    default: 'sm',
  },
  label: {
    type: String,
    default: '',
  },
});

const sizeClass = computed(() => {
  return props.size === 'sm' ? 'h-2 w-2' : 'h-2.5 w-2.5';
});

const dotColorClass = computed(() => {
  switch (props.status) {
    case 'running':
      return 'bg-blue-500';
    case 'success':
      return 'bg-emerald-500';
    case 'warning':
      return 'bg-amber-500';
    case 'danger':
      return 'bg-rose-500';
    case 'idle':
    default:
      return 'bg-slate-400 dark:bg-slate-600';
  }
});

const pingColorClass = computed(() => {
  switch (props.status) {
    case 'running':
      return 'bg-blue-400';
    case 'warning':
      return 'bg-amber-400';
    default:
      return 'bg-slate-400';
  }
});

const textColorClass = computed(() => {
  switch (props.status) {
    case 'running':
      return 'text-blue-600 dark:text-blue-400';
    case 'success':
      return 'text-emerald-600 dark:text-emerald-400';
    case 'warning':
      return 'text-amber-600 dark:text-amber-400';
    case 'danger':
      return 'text-rose-600 dark:text-rose-400';
    case 'idle':
    default:
      return 'text-text-muted';
  }
});
</script>
