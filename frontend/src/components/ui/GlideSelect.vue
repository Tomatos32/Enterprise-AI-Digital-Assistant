<template>
  <div class="relative inline-block text-left" ref="containerRef">
    <button
      type="button"
      @click="isOpen = !isOpen"
      class="inline-flex items-center space-x-1.5 px-2.5 py-1 text-xs font-semibold rounded-xl bg-slate-200/80 dark:bg-slate-900/90 hover:bg-slate-300/80 dark:hover:bg-slate-800 border border-border-subtle text-text-main transition-colors duration-150 cursor-pointer shadow-sm active:scale-[0.98]"
    >
      <component :is="selectedOption?.icon || Sparkles" class="w-3.5 h-3.5 text-brand-primary shrink-0" />
      <span class="max-w-[140px] truncate">{{ selectedOption?.label || '选择模型' }}</span>
      <ChevronDown class="w-3 h-3 text-text-muted transition-transform duration-150" :class="{ 'rotate-180': isOpen }" />
    </button>

    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 translate-y-1 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-1 scale-95"
    >
      <div
        v-if="isOpen"
        class="absolute left-0 mt-1.5 w-60 rounded-2xl p-1.5 glass-panel border border-border-card shadow-xl z-50 space-y-1"
      >
        <div
          v-for="opt in options"
          :key="opt.id"
          @click="selectOption(opt.id)"
          class="flex items-start space-x-2.5 p-2 rounded-xl text-xs cursor-pointer transition-colors duration-150"
          :class="[
            modelValue === opt.id
              ? 'bg-brand-primary/10 text-brand-primary font-semibold border border-brand-primary/20'
              : 'text-text-secondary hover:text-text-main hover:bg-slate-200/60 dark:hover:bg-slate-800/60'
          ]"
        >
          <component :is="opt.icon || Sparkles" class="w-4 h-4 mt-0.5 shrink-0" :class="modelValue === opt.id ? 'text-brand-primary' : 'text-text-muted'" />
          <div class="flex-1 truncate">
            <div class="flex items-center justify-between">
              <span class="truncate">{{ opt.label }}</span>
              <span v-if="opt.badge" class="ml-1 px-1.5 py-0.2 text-[9px] font-bold rounded-md bg-brand-primary/20 text-brand-primary">{{ opt.badge }}</span>
            </div>
            <div class="text-[10px] text-text-muted truncate mt-0.5">{{ opt.desc }}</div>
          </div>
          <Check v-if="modelValue === opt.id" class="w-3.5 h-3.5 text-brand-primary shrink-0 mt-0.5" />
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { ChevronDown, Check, Sparkles } from 'lucide-vue-next';

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

const selectedOption = computed(() => {
  return props.options.find(o => o.id === props.modelValue) || props.options[0];
});

const selectOption = (id) => {
  emit('update:modelValue', id);
  isOpen.value = false;
};

const handleOutsideClick = (e) => {
  if (containerRef.value && !containerRef.value.contains(e.target)) {
    isOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleOutsideClick);
});

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick);
});
</script>
