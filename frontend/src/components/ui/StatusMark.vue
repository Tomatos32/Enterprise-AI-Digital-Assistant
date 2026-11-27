<template>
  <div class="inline-flex items-center gap-1.5" :title="label">
    <span class="inline-flex rounded-full shrink-0" :class="[sizeClass, dotColorClass]"></span>
    <span v-if="label" class="text-xs font-medium text-text-secondary">
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

const sizeClass = computed(() => (props.size === 'sm' ? 'h-2 w-2' : 'h-2.5 w-2.5'));

const dotColorClass = computed(() => {
  switch (props.status) {
    case 'running':
      return 'bg-text-main';
    case 'success':
      return 'bg-status-success';
    case 'warning':
      return 'bg-status-approval';
    case 'danger':
      return 'bg-status-danger';
    case 'idle':
    default:
      return 'bg-text-muted';
  }
});
</script>
