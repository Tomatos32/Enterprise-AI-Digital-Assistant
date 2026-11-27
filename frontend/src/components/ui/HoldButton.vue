<template>
  <button
    type="button"
    :disabled="disabled || loading"
    :aria-label="ariaLabel || holdLabel"
    :title="hint"
    class="hold-btn relative inline-flex items-center justify-center overflow-hidden rounded-lg border font-medium select-none cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus disabled:opacity-50 disabled:pointer-events-none"
    :class="[sizeClasses, variantClasses, { 'is-holding': isHolding }]"
    @pointerdown="startHold"
    @pointerup="cancelHold"
    @pointerleave="cancelHold"
    @pointercancel="cancelHold"
    @keydown.space.prevent="startHold"
    @keydown.enter.prevent="startHold"
    @keyup.space="cancelHold"
    @keyup.enter="cancelHold"
  >
    <!-- Base Content Layer -->
    <span class="relative z-10 inline-flex items-center justify-center gap-1.5 pointer-events-none">
      <slot name="icon" />
      <span>{{ isHolding ? holdingLabel : label }}</span>
    </span>

    <!-- Clip-Path Liquid Fill Layer (emil-design-eng Hold-to-Confirm pattern) -->
    <span
      class="hold-overlay absolute inset-0 z-20 inline-flex items-center justify-center gap-1.5 pointer-events-none"
      :class="overlayClasses"
      :style="overlayStyle"
      aria-hidden="true"
    >
      <slot name="icon" />
      <span>{{ isHolding ? holdingLabel : label }}</span>
    </span>
  </button>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue';

const props = defineProps({
  label: {
    type: String,
    default: '长按确认',
  },
  holdingLabel: {
    type: String,
    default: '继续按住以确认...',
  },
  hint: {
    type: String,
    default: '长按以防误触',
  },
  ariaLabel: {
    type: String,
    default: '',
  },
  duration: {
    type: Number,
    default: 850,
  },
  variant: {
    type: String,
    default: 'danger',
    validator: (v) => ['danger', 'neutral'].includes(v),
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md'].includes(v),
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['confirm']);

const isHolding = ref(false);
let holdTimer = null;

const holdLabel = computed(() => `${props.label}（${props.hint}）`);

const sizeClasses = computed(() =>
  props.size === 'sm' ? 'px-2.5 py-1.5 text-xs' : 'px-3.5 py-2 text-xs'
);

const variantClasses = computed(() => {
  if (props.variant === 'neutral') {
    return 'bg-bg-card border-border-card text-text-secondary hover:text-text-main hover:border-border-strong';
  }
  return 'bg-bg-card border-border-card text-status-danger hover:border-status-danger/50';
});

const overlayClasses = computed(() => {
  if (props.variant === 'neutral') {
    return 'bg-action-primary text-action-primary-fg';
  }
  return 'bg-status-danger text-white';
});

const overlayStyle = computed(() => ({
  clipPath: isHolding.value ? 'inset(0 0% 0 0)' : 'inset(0 100% 0 0)',
  transition: isHolding.value
    ? `clip-path ${props.duration}ms linear`
    : 'clip-path 200ms var(--ease-out)',
}));

const clearHoldTimer = () => {
  if (holdTimer) {
    clearTimeout(holdTimer);
    holdTimer = null;
  }
};

const startHold = (e) => {
  if (props.disabled || props.loading || isHolding.value) return;
  if (e?.type === 'pointerdown' && e.button !== 0) return;
  isHolding.value = true;
  clearHoldTimer();
  holdTimer = setTimeout(() => {
    isHolding.value = false;
    holdTimer = null;
    emit('confirm');
  }, props.duration);
};

const cancelHold = () => {
  if (!isHolding.value && !holdTimer) return;
  clearHoldTimer();
  isHolding.value = false;
};

onBeforeUnmount(() => {
  clearHoldTimer();
});
</script>

<style scoped>
.hold-btn {
  transition: transform 140ms var(--ease-out),
              border-color 150ms var(--ease-out),
              background-color 150ms var(--ease-out),
              color 150ms var(--ease-out);
}
.hold-btn.is-holding,
.hold-btn:active:not(:disabled) {
  transform: scale(0.97);
}
</style>
