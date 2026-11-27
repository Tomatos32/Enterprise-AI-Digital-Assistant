<template>
  <div
    class="btn-pressable relative rounded-xl p-4 bg-bg-card cursor-pointer select-none group border border-border-card hover:border-border-strong overflow-hidden"
    @click="$emit('click')"
  >
    <!-- Top Row -->
    <div class="flex items-center justify-between mb-3">
      <div class="w-9 h-9 rounded-lg bg-bg-surface border border-border-subtle flex items-center justify-center text-text-main">
        <Folder class="w-4 h-4" />
      </div>
      <span
        v-if="category"
        class="px-2 py-0.5 text-[11px] font-medium rounded-md bg-bg-surface text-text-secondary border border-border-subtle"
      >
        {{ category }}
      </span>
    </div>

    <!-- Title & Concise Description -->
    <div class="space-y-1">
      <h3 class="text-sm font-semibold text-text-main flex items-center justify-between gap-2">
        <span class="truncate">{{ title }}</span>
        <ChevronRight class="w-4 h-4 text-text-muted group-hover:text-text-main transition-colors duration-150 shrink-0" />
      </h3>
      <p v-if="description" class="text-xs text-text-secondary line-clamp-2 leading-relaxed">
        {{ description }}
      </p>
    </div>

    <!-- Footer Metadata -->
    <div class="mt-4 pt-3 border-t border-border-subtle flex items-center justify-between text-[11px] text-text-muted">
      <div class="flex items-center gap-1.5">
        <FileText class="w-3.5 h-3.5" />
        <span class="tabular-nums">{{ count }} 篇制度</span>
      </div>
      <span v-if="lastUpdated" class="tabular-nums">{{ lastUpdated }}</span>
    </div>
  </div>
</template>

<script setup>
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
</script>
