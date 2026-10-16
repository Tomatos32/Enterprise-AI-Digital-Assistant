<template>
  <div
    class="relative rounded-2xl p-4 glass-card cursor-pointer transition-all duration-300 ease-out select-none group border border-border-card hover:shadow-xl hover:border-brand-primary/40 overflow-hidden"
    :style="cardTransform"
    @mousemove="handleMouseMove"
    @mouseleave="handleMouseLeave"
    @click="$emit('click')"
  >
    <!-- Background Shimmer Reflection on Hover -->
    <div
      v-if="isHovered"
      class="absolute inset-0 pointer-events-none opacity-20 transition-opacity duration-300 rounded-2xl"
      :style="{
        background: `radial-gradient(280px circle at ${mouseX}px ${mouseY}px, var(--brand-primary), transparent 80%)`
      }"
    ></div>

    <!-- Top Row: Icon & Tag -->
    <div class="flex items-center justify-between mb-3 z-10 relative">
      <div class="w-10 h-10 rounded-xl bg-brand-primary/10 border border-brand-primary/20 flex items-center justify-center text-brand-primary group-hover:scale-105 transition-transform duration-200">
        <Folder class="w-5 h-5 fill-brand-primary/20" />
      </div>
      <span v-if="category" class="px-2 py-0.5 text-[10px] font-semibold rounded-md bg-slate-200 dark:bg-slate-800 text-text-secondary border border-border-subtle">
        {{ category }}
      </span>
    </div>

    <!-- Title & Description -->
    <div class="z-10 relative space-y-1">
      <h3 class="text-sm font-bold text-text-main group-hover:text-brand-primary transition-colors duration-150 flex items-center justify-between">
        <span>{{ title }}</span>
        <ChevronRight class="w-4 h-4 text-text-muted group-hover:translate-x-1 group-hover:text-brand-primary transition-all duration-150" />
      </h3>
      <p v-if="description" class="text-xs text-text-secondary line-clamp-2 leading-relaxed">
        {{ description }}
      </p>
    </div>

    <!-- Bottom Metadata: Document Count & Time -->
    <div class="mt-4 pt-3 border-t border-border-subtle flex items-center justify-between text-[11px] text-text-muted z-10 relative">
      <div class="flex items-center space-x-1">
        <FileText class="w-3.5 h-3.5" />
        <span>{{ count }} 篇规章制度</span>
      </div>
      <span v-if="lastUpdated">{{ lastUpdated }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { Folder, FileText, ChevronRight } from 'lucide-vue-next';

defineProps({
  title: {
    type: String,
    required: true,
  },
  count: {
    type: Number,
    default: 0,
  },
  category: {
    type: String,
    default: '',
  },
  description: {
    type: String,
    default: '',
  },
  lastUpdated: {
    type: String,
    default: '',
  },
});

defineEmits(['click']);

const mouseX = ref(0);
const mouseY = ref(0);
const rotateX = ref(0);
const rotateY = ref(0);
const isHovered = ref(false);

const handleMouseMove = (e) => {
  const rect = e.currentTarget.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  mouseX.value = x;
  mouseY.value = y;

  const centerX = rect.width / 2;
  const centerY = rect.height / 2;
  rotateX.value = -((y - centerY) / centerY) * 4;
  rotateY.value = ((x - centerX) / centerX) * 4;
  isHovered.value = true;
};

const handleMouseLeave = () => {
  rotateX.value = 0;
  rotateY.value = 0;
  isHovered.value = false;
};

const cardTransform = computed(() => {
  if (!isHovered.value) return {};
  return {
    transform: `perspective(800px) rotateX(${rotateX.value}deg) rotateY(${rotateY.value}deg) translateY(-2px)`,
  };
});
</script>
