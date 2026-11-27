<template>
  <div
    class="relative inline-flex"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
    @focusin="handleMouseEnter"
    @focusout="handleMouseLeave"
  >
    <slot />
    <div
      v-if="isVisible && content"
      role="tooltip"
      class="warm-tooltip absolute z-50 px-2 py-1 text-[11px] font-medium rounded-md pointer-events-none whitespace-nowrap border border-border-card bg-action-primary text-action-primary-fg shadow-sm"
      :class="[positionClasses, { 'is-instant': isInstant }]"
    >
      {{ content }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue';

// Shared warm-group clock (emil-design-eng: delay first hover, zero-delay subsequent hovers)
const WARM_WINDOW_MS = 450;
const INITIAL_DELAY_MS = 280;
let lastTooltipClosedAt = 0;

const props = defineProps({
  content: {
    type: String,
    default: '',
  },
  position: {
    type: String,
    default: 'top',
    validator: (v) => ['top', 'bottom', 'left', 'right'].includes(v),
  },
});

const isVisible = ref(false);
const isInstant = ref(false);
let openTimer = null;

const handleMouseEnter = () => {
  if (!props.content) return;
  if (openTimer) clearTimeout(openTimer);
  const now = Date.now();
  if (now - lastTooltipClosedAt <= WARM_WINDOW_MS) {
    isInstant.value = true;
    isVisible.value = true;
    return;
  }
  isInstant.value = false;
  openTimer = setTimeout(() => {
    isVisible.value = true;
    openTimer = null;
  }, INITIAL_DELAY_MS);
};

const handleMouseLeave = () => {
  if (openTimer) {
    clearTimeout(openTimer);
    openTimer = null;
  }
  if (isVisible.value) {
    lastTooltipClosedAt = Date.now();
    isVisible.value = false;
  }
};

onBeforeUnmount(() => {
  if (openTimer) clearTimeout(openTimer);
});

const positionClasses = computed(() => {
  switch (props.position) {
    case 'bottom':
      return 'origin-top top-full left-1/2 -translate-x-1/2 mt-1.5';
    case 'left':
      return 'origin-right right-full top-1/2 -translate-y-1/2 mr-1.5';
    case 'right':
      return 'origin-left left-full top-1/2 -translate-y-1/2 ml-1.5';
    case 'top':
    default:
      return 'origin-bottom bottom-full left-1/2 -translate-x-1/2 mb-1.5';
  }
});
</script>

<style scoped>
.warm-tooltip {
  animation: tooltip-in 125ms var(--ease-out) both;
}
.warm-tooltip.is-instant {
  animation: none;
}
@keyframes tooltip-in {
  from {
    opacity: 0;
    transform: translateX(-50%) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) scale(1);
  }
}
</style>
