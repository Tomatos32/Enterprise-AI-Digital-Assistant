<template>
  <div
    v-if="active"
    class="flex items-center space-x-3 px-3 py-1.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 backdrop-blur-md shadow-sm animate-pulse-glow"
  >
    <!-- Live Recording Beacon -->
    <div class="flex items-center space-x-1.5">
      <span class="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping"></span>
      <span class="text-xs font-semibold tabular-nums">{{ formattedTime }}</span>
    </div>

    <!-- Dynamic Audio Waveform Simulation -->
    <div class="flex items-center space-x-0.5 h-4 px-1">
      <span
        v-for="(bar, i) in waveBars"
        :key="i"
        class="w-1 bg-rose-500 rounded-full transition-all duration-150"
        :style="{ height: `${bar}px` }"
      ></span>
    </div>

    <!-- Action Buttons: Cancel & Done -->
    <div class="flex items-center space-x-1">
      <button
        type="button"
        @click="$emit('cancel')"
        title="取消录音"
        class="p-1 rounded-lg hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 transition-colors"
      >
        <Trash2 class="w-3.5 h-3.5" />
      </button>
      <button
        type="button"
        @click="$emit('finish')"
        title="发送语音转文字"
        class="p-1 rounded-lg bg-rose-500 text-white hover:bg-rose-600 transition-colors shadow-sm"
      >
        <Square class="w-3 h-3 fill-current" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { Trash2, Square } from 'lucide-vue-next';

const props = defineProps({
  active: {
    type: Boolean,
    default: false,
  },
});

defineEmits(['finish', 'cancel']);

const seconds = ref(0);
let timer = null;
let waveTimer = null;
const waveBars = ref([4, 10, 16, 8, 14, 12, 6]);

const formattedTime = computed(() => {
  const m = Math.floor(seconds.value / 60).toString().padStart(2, '0');
  const s = (seconds.value % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
});

const startTimers = () => {
  seconds.value = 0;
  timer = setInterval(() => {
    seconds.value++;
  }, 1000);

  waveTimer = setInterval(() => {
    waveBars.value = waveBars.value.map(() => Math.floor(Math.random() * 14) + 4);
  }, 150);
};

const stopTimers = () => {
  if (timer) clearInterval(timer);
  if (waveTimer) clearInterval(waveTimer);
  timer = null;
  waveTimer = null;
};

watch(() => props.active, (val) => {
  if (val) startTimers();
  else stopTimers();
});

onMounted(() => {
  if (props.active) startTimers();
});

onUnmounted(() => {
  stopTimers();
});
</script>
