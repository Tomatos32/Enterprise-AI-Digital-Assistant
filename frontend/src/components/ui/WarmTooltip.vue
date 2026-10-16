<template>
  <div class="relative inline-flex group" @mouseenter="isVisible = true" @mouseleave="isVisible = false">
    <slot />
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="isVisible && content"
        class="absolute z-50 px-2 py-1 text-[11px] font-medium rounded-lg shadow-lg pointer-events-none whitespace-nowrap border border-border-subtle bg-slate-900/95 text-slate-100 dark:bg-slate-800/95 dark:text-slate-100 backdrop-blur-md"
        :class="positionClasses"
      >
        {{ content }}
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

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

const positionClasses = computed(() => {
  switch (props.position) {
    case 'bottom':
      return 'top-full left-1/2 -translate-x-1/2 mt-1.5';
    case 'left':
      return 'right-full top-1/2 -translate-y-1/2 mr-1.5';
    case 'right':
      return 'left-full top-1/2 -translate-y-1/2 ml-1.5';
    case 'top':
    default:
      return 'bottom-full left-1/2 -translate-x-1/2 mb-1.5';
  }
});
</script>
