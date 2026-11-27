<template>
  <div class="relative inline-block text-left" ref="containerRef">
    <button
      type="button"
      @click="isOpen = !isOpen"
      class="btn-secondary inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg cursor-pointer"
    >
      <component :is="selectedOption?.icon || SlidersHorizontal" class="w-3.5 h-3.5 text-text-secondary shrink-0" />
      <span class="max-w-[140px] truncate">{{ selectedOption?.label || '选择项' }}</span>
      <ChevronDown
        class="w-3 h-3 text-text-muted transition-transform duration-150"
        :class="{ 'rotate-180': isOpen }"
      />
    </button>

    <transition name="popover">
      <div
        v-if="isOpen"
        class="origin-top-left absolute left-0 mt-1.5 w-60 rounded-xl p-1.5 bg-bg-card border border-border-card shadow-sm z-50 space-y-0.5"
      >
        <button
          v-for="opt in options"
          :key="opt.id"
          type="button"
          @click="selectOption(opt.id)"
          class="w-full flex items-start gap-2.5 p-2 rounded-lg text-xs text-left cursor-pointer transition-colors duration-150"
          :class="[
            modelValue === opt.id
              ? 'bg-bg-surface text-text-main font-semibold'
              : 'text-text-secondary hover:text-text-main hover:bg-bg-hover'
          ]"
        >
          <component
            :is="opt.icon || SlidersHorizontal"
            class="w-3.5 h-3.5 mt-0.5 shrink-0 text-text-secondary"
          />
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between gap-1">
              <span class="truncate">{{ opt.label }}</span>
              <span
                v-if="opt.badge"
                class="px-1.5 py-0.5 text-[10px] font-mono rounded bg-bg-card border border-border-subtle text-text-secondary"
              >
                {{ opt.badge }}
              </span>
            </div>
            <div v-if="opt.desc" class="text-[11px] text-text-muted truncate mt-0.5">{{ opt.desc }}</div>
          </div>
          <Check v-if="modelValue === opt.id" class="w-3.5 h-3.5 text-text-main shrink-0 mt-0.5" />
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { ChevronDown, Check, SlidersHorizontal } from 'lucide-vue-next';

const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  options: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(['update:modelValue']);
const isOpen = ref(false);
const containerRef = ref(null);

const selectedOption = computed(
  () => props.options.find((o) => o.id === props.modelValue) || props.options[0]
);

const selectOption = (id) => {
  emit('update:modelValue', id);
  isOpen.value = false;
};

const handleOutsideClick = (e) => {
  if (containerRef.value && !containerRef.value.contains(e.target)) {
    isOpen.value = false;
  }
};

const handleKeydown = (e) => {
  if (e.key === 'Escape' && isOpen.value) {
    isOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleOutsideClick);
  document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick);
  document.removeEventListener('keydown', handleKeydown);
});
</script>
