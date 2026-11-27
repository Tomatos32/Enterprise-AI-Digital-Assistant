<template>
  <div
    ref="rootRef"
    class="pointer-events-none absolute inset-0 overflow-hidden select-none"
    aria-hidden="true"
  >
    <!-- Base Monochrome Architectural Dot Grid -->
    <div
      class="absolute inset-0 dot-grid-base"
      :style="baseGridStyle"
    ></div>

    <!-- Subtle Pointer-Proximity Monochrome Dot Highlight (Zero Colored Glow) -->
    <div
      v-if="interactive && pointerActive && !prefersReducedMotion"
      class="absolute inset-0 dot-grid-active"
      :style="activeGridStyle"
    ></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  gap: {
    type: Number,
    default: 22,
  },
  dotSize: {
    type: Number,
    default: 1,
  },
  interactive: {
    type: Boolean,
    default: true,
  },
  radius: {
    type: Number,
    default: 140,
  },
});

const rootRef = ref(null);
const pointerX = ref(0);
const pointerY = ref(0);
const pointerActive = ref(false);
const prefersReducedMotion = ref(false);

const baseGridStyle = computed(() => ({
  backgroundImage: `radial-gradient(circle, var(--dot-grid-color) ${props.dotSize}px, transparent ${props.dotSize}px)`,
  backgroundSize: `${props.gap}px ${props.gap}px`,
  maskImage: 'radial-gradient(ellipse 78% 72% at 50% 45%, #000 45%, transparent 100%)',
  WebkitMaskImage: 'radial-gradient(ellipse 78% 72% at 50% 45%, #000 45%, transparent 100%)',
}));

const activeGridStyle = computed(() => ({
  backgroundImage: `radial-gradient(circle, var(--dot-grid-active) ${props.dotSize}px, transparent ${props.dotSize}px)`,
  backgroundSize: `${props.gap}px ${props.gap}px`,
  maskImage: `radial-gradient(${props.radius}px circle at ${pointerX.value}px ${pointerY.value}px, #000 0%, transparent 100%)`,
  WebkitMaskImage: `radial-gradient(${props.radius}px circle at ${pointerX.value}px ${pointerY.value}px, #000 0%, transparent 100%)`,
}));

let parentEl = null;

const handlePointerMove = (e) => {
  if (!rootRef.value || prefersReducedMotion.value) return;
  const rect = rootRef.value.getBoundingClientRect();
  pointerX.value = e.clientX - rect.left;
  pointerY.value = e.clientY - rect.top;
  pointerActive.value = true;
};

const handlePointerLeave = () => {
  pointerActive.value = false;
};

onMounted(() => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    prefersReducedMotion.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  if (props.interactive && rootRef.value?.parentElement) {
    parentEl = rootRef.value.parentElement;
    parentEl.addEventListener('pointermove', handlePointerMove, { passive: true });
    parentEl.addEventListener('pointerleave', handlePointerLeave, { passive: true });
  }
});

onUnmounted(() => {
  if (parentEl) {
    parentEl.removeEventListener('pointermove', handlePointerMove);
    parentEl.removeEventListener('pointerleave', handlePointerLeave);
    parentEl = null;
  }
});
</script>
