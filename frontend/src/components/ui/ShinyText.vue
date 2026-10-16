<template>
  <span
    class="inline-flex items-center font-semibold bg-clip-text text-transparent transition-opacity duration-200"
    :class="[
      disabled ? 'text-text-secondary' : 'animate-shimmer',
      customClass
    ]"
    :style="shimmerStyle"
  >
    <slot>{{ text }}</slot>
  </span>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  text: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  speed: {
    type: Number,
    default: 3,
  },
  customClass: {
    type: String,
    default: '',
  }
});

const shimmerStyle = computed(() => {
  if (props.disabled) return {};
  return {
    backgroundImage: 'linear-gradient(110deg, var(--text-main) 35%, var(--brand-primary) 50%, var(--text-main) 65%)',
    backgroundSize: '250% 100%',
    animationDuration: `${props.speed}s`,
  };
});
</script>
