<template>
  <button
    :disabled="disabled || loading"
    class="relative inline-flex items-center justify-center font-medium rounded-xl transition-all duration-150 select-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-primary/40 active:scale-[0.97] disabled:opacity-50 disabled:pointer-events-none disabled:active:scale-100"
    :class="[variantClasses, sizeClasses, customClass]"
    @click="$emit('click', $event)"
  >
    <svg
      v-if="loading"
      class="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
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
      return 'bg-brand-primary hover:bg-brand-primary-hover text-white shadow-sm shadow-blue-500/20';
    case 'secondary':
      return 'bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-text-main border border-border-subtle';
    case 'ghost':
      return 'bg-transparent hover:bg-slate-200/60 dark:hover:bg-slate-800/60 text-text-secondary hover:text-text-main';
    case 'danger':
      return 'bg-rose-600 hover:bg-rose-700 text-white shadow-sm shadow-rose-600/20';
    case 'subtle':
    default:
      return 'bg-brand-primary/10 hover:bg-brand-primary/20 text-brand-primary border border-brand-primary/20';
  }
});

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'px-2.5 py-1 text-xs';
    case 'lg':
      return 'px-5 py-2.5 text-sm';
    case 'md':
    default:
      return 'px-3.5 py-1.5 text-xs';
  }
});
</script>
