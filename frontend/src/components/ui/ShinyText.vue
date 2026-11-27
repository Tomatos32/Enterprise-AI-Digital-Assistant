<template>
  <span class="inline-flex items-center font-semibold text-text-main" :class="customClass">
    <slot>{{ text }}</slot>
  </span>
</template>

<script setup>
defineProps({
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
  },
});
</script>
