<template>
  <div
    class="w-full max-w-3xl mx-auto px-2 sm:px-4 select-none relative z-10 transition-transform duration-150 ease-out"
    :style="viewportStyle"
  >
    <!-- Floating Capsule Container with Soft Deep Shadow -->
    <div
      class="glass-panel p-1.5 sm:p-2.5 rounded-3xl border border-border-card transition-all duration-200"
      style="box-shadow: 0 12px 30px -6px rgba(0, 0, 0, 0.5), 0 4px 12px -2px rgba(59, 130, 246, 0.08);"
      :class="{ 'border-brand-primary/40 ring-1 ring-brand-primary/20': isFocused }"
    >
      <div class="flex items-end space-x-1.5 sm:space-x-2">
        <!-- Optional Attachment Button (Paperclip) -->
        <button
          type="button"
          :disabled="disabled || isStreaming"
          class="interactive-action w-9 h-9 sm:w-8 sm:h-8 flex items-center justify-center text-text-secondary hover:text-text-main hover:bg-slate-800/80 rounded-full transition-colors duration-150 shrink-0 mb-0.5 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
          title="上传规章草案或附件凭据 (即将支持)"
        >
          <Paperclip class="w-4 h-4 text-text-secondary" />
        </button>

        <!-- Auto-Expanding Multiline Textarea (44px ~ 200px Zero Jitter) -->
        <div class="flex-1 relative flex items-center min-h-[44px]">
          <textarea
            ref="textareaRef"
            v-model="inputText"
            @input="adjustHeight"
            @keydown="handleKeyDown"
            @focus="isFocused = true"
            @blur="isFocused = false"
            :disabled="disabled"
            :placeholder="placeholder"
            rows="1"
            class="w-full bg-transparent text-text-main placeholder-text-muted resize-none border-0 focus:ring-0 focus:outline-none text-xs sm:text-sm font-sans leading-relaxed py-2.5 px-2 max-h-[200px] overflow-y-auto"
            style="min-height: 44px;"
          ></textarea>
        </div>

        <!-- Action Button (Smooth Morphing between Send and Abort) -->
        <div class="shrink-0 mb-0.5 sm:mb-1">
          <!-- Abort (Stop Generating) Button when Streaming -->
          <button
            v-if="isStreaming"
            @click="handleAbort"
            class="interactive-action w-9 h-9 sm:w-8 sm:h-8 rounded-full bg-rose-600 hover:bg-rose-500 text-white flex items-center justify-center shadow-lg shadow-rose-600/30 transition-all duration-150 cursor-pointer animate-pulse active:scale-95"
            title="停止生成 (Abort)"
          >
            <Square class="w-3.5 h-3.5 fill-current" />
          </button>

          <!-- Send Button (Circle ArrowUp Icon, ChatGPT Style) -->
          <button
            v-else
            @click="handleSend"
            :disabled="disabled || !inputText.trim()"
            class="interactive-action w-9 h-9 sm:w-8 sm:h-8 rounded-full flex items-center justify-center transition-all duration-150 shadow-md cursor-pointer active:scale-95"
            :class="[
              inputText.trim() && !disabled
                ? 'bg-brand-primary hover:bg-brand-primary-hover text-white shadow-blue-500/25'
                : 'bg-slate-800/80 text-text-muted cursor-not-allowed opacity-60'
            ]"
            title="发送 (Enter)"
          >
            <ArrowUp class="w-4 h-4 stroke-[2.5]" />
          </button>
        </div>
      </div>
    </div>

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
import { ref, watch, nextTick, computed, onMounted, onUnmounted } from 'vue';
import { ArrowUp, Square, Paperclip } from 'lucide-vue-next';

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
    default: '请输入您的问题或业务指令（如：申请大额采购 MacBook Pro）...',
  },
});

const emit = defineEmits(['send', 'abort']);

const inputText = ref('');
const textareaRef = ref(null);
const isFocused = ref(false);
const keyboardOffset = ref(0);

const MIN_HEIGHT = 44;
const MAX_HEIGHT = 200;

// 动态响应移动端虚拟软键盘 (visualViewport)
const handleViewportChange = () => {
  if (typeof window === 'undefined' || !window.visualViewport) return;
  const vv = window.visualViewport;
  // 视口高度与实际 window 高度的落差即为软键盘高度
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
      marginBottom: `${keyboardOffset.value}px`,
    };
  }
  return {};
});

// 动态调整高度 (44px ~ 200px 零抖动)
const adjustHeight = () => {
  const el = textareaRef.value;
  if (!el) return;

  // 先重置为初始高度以准确获得 scrollHeight
  el.style.height = `${MIN_HEIGHT}px`;

  const newHeight = Math.min(Math.max(el.scrollHeight, MIN_HEIGHT), MAX_HEIGHT);
  el.style.height = `${newHeight}px`;

  // 超过最大高度时开启内置细滚动条
  if (el.scrollHeight > MAX_HEIGHT) {
    el.style.overflowY = 'auto';
  } else {
    el.style.overflowY = 'hidden';
  }
};

// 键盘事件监听：Enter 发送，Shift+Enter 换行
const handleKeyDown = (e) => {
  if (e.key === 'Enter') {
    if (e.shiftKey) {
      // 允许自然换行，触发自适应撑高
      nextTick(adjustHeight);
      return;
    }
    // 纯 Enter：阻止默认换行并发送
    e.preventDefault();
    handleSend();
  }
};

const handleSend = () => {
  if (props.disabled || props.isStreaming) return;
  const content = inputText.value.trim();
  if (!content) return;

  emit('send', content);

  // 清空并重置输入框高度
  inputText.value = '';
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = `${MIN_HEIGHT}px`;
      textareaRef.value.style.overflowY = 'hidden';
    }
  });
};

const handleAbort = () => {
  emit('abort');
};

// 监听外界传入文字或输入清空
watch(inputText, (val) => {
  if (!val) {
    nextTick(() => {
      if (textareaRef.value) {
        textareaRef.value.style.height = `${MIN_HEIGHT}px`;
      }
    });
  }
});
</script>
