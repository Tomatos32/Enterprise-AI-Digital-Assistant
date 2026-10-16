<template>
  <div class="my-2 select-none">
    <!-- Header Capsule Line -->
    <div
      class="inline-flex items-center space-x-2 px-3 py-1.5 rounded-2xl text-xs cursor-pointer transition-all duration-200 border glass-panel hover:bg-slate-200/50 dark:hover:bg-slate-800/50 shadow-sm"
      :class="isThinking ? 'border-brand-primary/40 bg-brand-primary/5' : 'border-border-subtle'"
      @click="isExpanded = !isExpanded"
    >
      <!-- Icon with Breathing Glow during Thinking -->
      <div class="relative flex items-center justify-center shrink-0">
        <Sparkles
          class="w-3.5 h-3.5"
          :class="isThinking ? 'text-brand-primary animate-pulse' : 'text-text-muted'"
        />
        <span
          v-if="isThinking"
          class="absolute -inset-1 rounded-full bg-brand-primary/20 animate-ping opacity-75"
        ></span>
      </div>

      <!-- Thinking Status & Stopwatch -->
      <span class="font-medium text-text-main">
        {{ isThinking ? '正在深度思考推理中...' : `已完成思考 · 耗时 ${durationText}` }}
      </span>

      <span v-if="isThinking" class="text-brand-primary font-mono text-[11px] tabular-nums">
        {{ currentTimer.toFixed(1) }}s
      </span>

      <!-- Expand / Collapse Chevron -->
      <ChevronDown
        class="w-3.5 h-3.5 text-text-muted transition-transform duration-200"
        :class="{ 'rotate-180': isExpanded }"
      />
    </div>

    <!-- Collapsible Reasoning Steps Content Area -->
    <transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1 max-h-0"
      enter-to-class="opacity-100 translate-y-0 max-h-96"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0 max-h-96"
      leave-to-class="opacity-0 -translate-y-1 max-h-0"
    >
      <div
        v-if="isExpanded"
        class="mt-2 pl-4 pr-3 py-2.5 rounded-2xl border-l-2 border-brand-primary/50 bg-slate-100/60 dark:bg-slate-900/40 text-xs text-text-secondary space-y-2 overflow-hidden backdrop-blur-sm"
      >
        <!-- Steps List -->
        <div v-if="steps && steps.length > 0" class="space-y-1.5">
          <div
            v-for="(step, idx) in steps"
            :key="idx"
            class="flex items-start space-x-2 text-[11px]"
          >
            <div class="w-1.5 h-1.5 rounded-full bg-brand-primary mt-1.5 shrink-0"></div>
            <div class="flex-1">
              <span class="font-medium text-text-main">{{ step.title || step }}</span>
              <p v-if="step.desc" class="text-text-muted mt-0.5 text-[10px]">{{ step.desc }}</p>
            </div>
          </div>
        </div>

        <!-- Preview Reasoning Text -->
        <div v-else-if="preview" class="text-[11px] leading-relaxed text-text-muted font-mono whitespace-pre-wrap">
          {{ preview }}
        </div>

        <div v-else class="text-[11px] text-text-muted italic">
          正在比对企业规章制度向量语义、分析意图槽位与调用策略...
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { Sparkles, ChevronDown } from 'lucide-vue-next';

const props = defineProps({
  isThinking: {
    type: Boolean,
    default: false,
  },
  durationSeconds: {
    type: Number,
    default: 0,
  },
  steps: {
    type: Array,
    default: () => [],
  },
  preview: {
    type: String,
    default: '',
  },
});

const isExpanded = ref(false);
const currentTimer = ref(0);
let timerId = null;

const durationText = computed(() => {
  const s = props.durationSeconds || currentTimer.value || 1.2;
  return `${s.toFixed(1)}s`;
});

const startTimer = () => {
  currentTimer.value = 0;
  if (timerId) clearInterval(timerId);
  timerId = setInterval(() => {
    currentTimer.value += 0.1;
  }, 100);
};

const stopTimer = () => {
  if (timerId) {
    clearInterval(timerId);
    timerId = null;
  }
};

watch(() => props.isThinking, (val) => {
  if (val) {
    isExpanded.value = true;
    startTimer();
  } else {
    stopTimer();
    // 思考完毕后平滑收起
    isExpanded.value = false;
  }
}, { immediate: true });

onMounted(() => {
  if (props.isThinking) startTimer();
});

onUnmounted(() => {
  stopTimer();
});
</script>
