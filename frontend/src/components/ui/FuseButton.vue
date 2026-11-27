<template>
  <button
    type="button"
    :disabled="disabled || loading"
    class="btn-pressable relative inline-flex items-center justify-center font-medium rounded-lg select-none cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus disabled:opacity-50 disabled:pointer-events-none"
    :class="[variantClasses, sizeClasses, customClass]"
    @click="$emit('click', $event)"
  >
    <svg
      v-if="loading"
      class="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5 text-current"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
    </svg>
    <slot name="icon" />
    <span :class="{ 'ml-1.5': !!$slots.icon && !$slots.default }"><slot /></span>
  </button>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'secondary', 'ghost', 'danger', 'subtle'].includes(v),
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v),
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  customClass: {
    type: String,
    default: '',
  },
});

defineEmits(['click']);

const variantClasses = computed(() => {
  switch (props.variant) {
    case 'primary':
      return 'bg-action-primary hover:bg-action-primary-hover text-action-primary-fg border border-action-primary';
    case 'secondary':
      return 'bg-bg-card hover:bg-bg-hover text-text-main border border-border-card hover:border-border-strong';
    case 'ghost':
      return 'bg-transparent hover:bg-bg-hover text-text-secondary hover:text-text-main border border-transparent';
    case 'danger':
      return 'bg-status-danger hover:opacity-90 text-white border border-status-danger';
    case 'subtle':
    default:
      return 'bg-bg-surface hover:bg-bg-hover text-text-main border border-border-subtle';
  }
});

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'px-2.5 py-1 text-xs';
    case 'lg':
      return 'px-4 py-2 text-sm';
    case 'md':
    default:
      return 'px-3 py-1.5 text-xs';
  }
});
</script>
