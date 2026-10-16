<template>
  <div
    class="relative group rounded-xl px-2.5 py-2 text-xs flex items-center justify-between cursor-pointer transition-all duration-150 overflow-hidden"
    :class="[
      active
        ? 'bg-slate-200/90 dark:bg-slate-800 text-text-main font-semibold shadow-sm border border-border-card'
        : 'text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-900/60'
    ]"
    @click="$emit('select')"
    @mousemove="handleMouseMove"
    @mouseleave="handleMouseLeave"
  >
    <!-- Left Border Active Line Indicator -->
    <div
      class="absolute left-0 top-1 bottom-1 w-1 rounded-r bg-brand-primary transition-all duration-200"
      :class="active ? 'opacity-100 scale-y-100' : 'opacity-0 scale-y-50 group-hover:opacity-40 group-hover:scale-y-75'"
    ></div>

    <!-- Micro Hover Spotlight Follower -->
    <div
      v-if="isHovered"
      class="absolute -inset-px pointer-events-none rounded-xl opacity-30 transition-opacity duration-300"
      :style="{
        background: `radial-gradient(120px circle at ${mouseX}px ${mouseY}px, var(--brand-primary), transparent 70%)`
      }"
    ></div>

    <!-- Content Row -->
    <div class="flex items-center space-x-2 truncate z-10">
      <component :is="icon || MessageSquare" class="w-3.5 h-3.5 shrink-0 opacity-70" />
      <span class="truncate">{{ title }}</span>
    </div>

    <!-- Delete Button -->
    <button
      v-if="allowDelete"
      @click.stop="$emit('delete')"
      title="删除会话"
      class="opacity-0 group-hover:opacity-100 p-1 text-text-muted hover:text-status-danger rounded transition-all duration-150 z-10"
    >
      <Trash2 class="w-3.5 h-3.5" />
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { MessageSquare, Trash2 } from 'lucide-vue-next';

defineProps({
  title: {
    type: String,
    required: true,
  },
  active: {
    type: Boolean,
    default: false,
  },
  icon: {
    type: Object,
    default: null,
  },
  allowDelete: {
    type: Boolean,
    default: true,
  },
});

defineEmits(['select', 'delete']);

const mouseX = ref(0);
const mouseY = ref(0);
const isHovered = ref(false);

const handleMouseMove = (e) => {
  const rect = e.currentTarget.getBoundingClientRect();
  mouseX.value = e.clientX - rect.left;
  mouseY.value = e.clientY - rect.top;
  isHovered.value = true;
};

const handleMouseLeave = () => {
  isHovered.value = false;
};
</script>
