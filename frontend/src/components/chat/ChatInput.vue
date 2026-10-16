<template>
  <div
    class="w-full max-w-4xl mx-auto px-2 sm:px-4 select-none relative z-10 transition-transform duration-150 ease-out"
    :style="viewportStyle"
  >
    <!-- Flagship PromptBar with @ Knowledge, / Commands, Voice Pill & Dual Theme -->
    <PromptBar
      v-model="inputText"
      :is-streaming="isStreaming"
      @send="handleSend"
      @abort="$emit('abort')"
    />

    <!-- Bottom Compliance Disclaimer -->
    <div
      class="mt-1.5 sm:mt-2 text-center text-[10px] sm:text-[11px] text-text-muted select-none flex items-center justify-center space-x-1.5"
      style="padding-bottom: env(safe-area-inset-bottom, 2px);"
    >
      <span>内容由企业 AI 驱动生成，关键业务决策请以审批单据为准</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import PromptBar from '../ui/PromptBar.vue';

const props = defineProps({
  isStreaming: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  placeholder: {
    type: String,
    default: '输入问题，输入 @ 链接知识源，或输入 / 触发内置命令...',
  },
});

const emit = defineEmits(['send', 'abort']);

const inputText = ref('');
const keyboardOffset = ref(0);

const handleViewportChange = () => {
  if (typeof window === 'undefined' || !window.visualViewport) return;
  const vv = window.visualViewport;
  const offset = Math.max(0, window.innerHeight - vv.height - (vv.offsetTop || 0));
  keyboardOffset.value = offset;
};

onMounted(() => {
  if (typeof window !== 'undefined' && window.visualViewport) {
    window.visualViewport.addEventListener('resize', handleViewportChange);
    window.visualViewport.addEventListener('scroll', handleViewportChange);
  }
});

onUnmounted(() => {
  if (typeof window !== 'undefined' && window.visualViewport) {
    window.visualViewport.removeEventListener('resize', handleViewportChange);
    window.visualViewport.removeEventListener('scroll', handleViewportChange);
  }
});

const viewportStyle = computed(() => {
  if (keyboardOffset.value > 0) {
    return {
      transform: `translateY(-${keyboardOffset.value}px)`,
    };
  }
  return {};
});

const handleSend = (payload) => {
  if (props.disabled || props.isStreaming) return;
  emit('send', payload);
};
</script>
