<template>
  <div class="inline-flex p-0.5 rounded-lg bg-bg-surface border border-border-subtle select-none">
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      class="btn-pressable relative px-2.5 py-1 text-xs font-medium rounded-md cursor-pointer flex items-center gap-1.5 focus:outline-none"
      :class="[
        modelValue === opt.value
          ? 'bg-bg-card text-text-main border border-border-card font-semibold'
          : 'border border-transparent text-text-secondary hover:text-text-main'
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
