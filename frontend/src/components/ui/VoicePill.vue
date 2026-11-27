<template>
  <div
    v-if="active"
    class="flex items-center gap-3 px-3 py-1.5 rounded-lg bg-bg-surface border border-border-card text-text-main"
  >
    <div class="flex items-center gap-1.5">
      <span class="w-2 h-2 rounded-full bg-status-danger"></span>
      <span class="text-xs font-medium tabular-nums font-mono">{{ formattedTime }}</span>
    </div>

    <div class="flex items-center gap-0.5 h-4 px-1">
      <span
        v-for="(bar, i) in waveBars"
        :key="i"
        class="w-0.5 bg-text-secondary rounded-full transition-[height] duration-150"
        :style="{ height: `${bar}px` }"
      ></span>
    </div>

    <div class="flex items-center gap-1">
      <button
        type="button"
        @click="$emit('cancel')"
        title="取消录音"
        class="btn-pressable p-1 rounded-md text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer"
      >
        <Trash2 class="w-3.5 h-3.5" />
      </button>
      <button
        type="button"
        @click="$emit('finish')"
        title="完成语音输入"
        class="btn-primary p-1 rounded-md cursor-pointer"
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
const waveBars = ref([4, 10, 14, 8, 12, 10, 6]);

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
    waveBars.value = waveBars.value.map(() => Math.floor(Math.random() * 12) + 4);
  }, 160);
};

const stopTimers = () => {
  if (timer) clearInterval(timer);
  if (waveTimer) clearInterval(waveTimer);
  timer = null;
  waveTimer = null;
};

watch(
  () => props.active,
  (val) => {
    if (val) startTimers();
    else stopTimers();
  }
);

onMounted(() => {
  if (props.active) startTimers();
});

onUnmounted(() => {
  stopTimers();
});
</script>
