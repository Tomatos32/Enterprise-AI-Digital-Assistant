<template>
  <div class="inline-flex p-1 rounded-xl bg-slate-200/70 dark:bg-slate-900/80 border border-border-subtle backdrop-blur-md select-none">
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      class="relative px-3 py-1 text-xs font-medium rounded-lg transition-all duration-200 cursor-pointer flex items-center space-x-1.5 focus:outline-none"
      :class="[
        modelValue === opt.value
          ? 'bg-white dark:bg-slate-800 text-text-main shadow-sm shadow-slate-950/10 font-semibold'
          : 'text-text-secondary hover:text-text-main hover:bg-white/40 dark:hover:bg-slate-800/40'
      ]"
      @click="$emit('update:modelValue', opt.value)"
    >
      <component :is="opt.icon" v-if="opt.icon" class="w-3.5 h-3.5" />
      <span>{{ opt.label }}</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: [String, Number],
    required: true,
  },
  options: {
    type: Array,
    required: true,
  },
});

defineEmits(['update:modelValue']);
</script>
