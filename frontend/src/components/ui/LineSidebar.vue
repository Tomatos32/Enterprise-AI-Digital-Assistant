<template>
  <div
    class="relative group rounded-lg px-2.5 py-1.5 text-xs flex items-center justify-between cursor-pointer transition-colors duration-150 overflow-hidden"
    :class="[
      active
        ? 'bg-bg-card text-text-main font-medium border border-border-card'
        : 'text-text-secondary hover:text-text-main hover:bg-bg-hover border border-transparent'
    ]"
    @click="$emit('select')"
  >
    <!-- Crisp Monochrome Active Line -->
    <div
      class="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r bg-text-main transition-opacity duration-150"
      :class="active ? 'opacity-100' : 'opacity-0'"
    ></div>

    <!-- Content Row -->
    <div class="flex items-center gap-2 truncate pl-0.5">
      <component :is="icon || MessageSquare" class="w-3.5 h-3.5 shrink-0 opacity-65" />
      <span class="truncate">{{ title }}</span>
    </div>

    <!-- Delete Button -->
    <button
      v-if="allowDelete"
      type="button"
      @click.stop="$emit('delete')"
      title="删除会话"
      class="opacity-0 group-hover:opacity-100 p-1 text-text-muted hover:text-status-danger rounded transition-opacity duration-150"
    >
      <Trash2 class="w-3.5 h-3.5" />
    </button>
  </div>
</template>

<script setup>
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
</script>
