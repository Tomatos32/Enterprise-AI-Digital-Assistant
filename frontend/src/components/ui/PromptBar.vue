<template>
  <div class="relative w-full max-w-4xl mx-auto select-none" ref="barContainerRef">
    <!-- Popover Menu: @ Data Sources -->
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 translate-y-2 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-2 scale-95"
    >
      <div
        v-if="showAtMenu"
        class="absolute bottom-full mb-2 left-4 w-72 rounded-2xl glass-panel p-2 border border-border-card shadow-2xl z-40 space-y-1"
      >
        <div class="px-2 py-1 text-[10px] font-bold text-text-muted tracking-wider uppercase">
          链接企业数据源 (@)
        </div>
        <div
          v-for="source in dataSources"
          :key="source.id"
          @click="insertDataSource(source)"
          class="flex items-center space-x-2.5 px-2.5 py-2 rounded-xl text-xs text-text-secondary hover:text-text-main hover:bg-slate-200/60 dark:hover:bg-slate-800/60 cursor-pointer transition-colors duration-150"
        >
          <component :is="source.icon" class="w-4 h-4 text-brand-primary shrink-0" />
          <div class="flex-1 truncate">
            <div class="font-semibold text-text-main">{{ source.name }}</div>
            <div class="text-[10px] text-text-muted truncate">{{ source.desc }}</div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Popover Menu: / Built-in Commands -->
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 translate-y-2 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-2 scale-95"
    >
      <div
        v-if="showSlashMenu"
        class="absolute bottom-full mb-2 left-4 w-72 rounded-2xl glass-panel p-2 border border-border-card shadow-2xl z-40 space-y-1"
      >
        <div class="px-2 py-1 text-[10px] font-bold text-text-muted tracking-wider uppercase">
          快捷执行指令 (/)
        </div>
        <div
          v-for="cmd in slashCommands"
          :key="cmd.command"
          @click="insertCommand(cmd)"
          class="flex items-center space-x-2.5 px-2.5 py-2 rounded-xl text-xs text-text-secondary hover:text-text-main hover:bg-slate-200/60 dark:hover:bg-slate-800/60 cursor-pointer transition-colors duration-150"
        >
          <component :is="cmd.icon" class="w-4 h-4 text-brand-primary shrink-0" />
          <div class="flex-1 truncate">
            <div class="font-semibold text-text-main">{{ cmd.command }}</div>
            <div class="text-[10px] text-text-muted truncate">{{ cmd.desc }}</div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Main Capsule Container -->
    <div
      class="rounded-3xl p-2.5 sm:p-3 glass-panel border border-border-card shadow-lg transition-all duration-200 focus-within:border-brand-primary/60 focus-within:shadow-brand-primary/10 focus-within:shadow-xl relative backdrop-blur-xl"
    >
      <!-- Voice Recording Bar Overlay if Active -->
      <div v-if="isRecordingVoice" class="p-2 flex items-center justify-between">
        <VoicePill
          :active="isRecordingVoice"
          @cancel="isRecordingVoice = false"
          @finish="handleVoiceFinished"
        />
        <span class="text-xs text-text-secondary">松开或点击停止以生成提示词</span>
      </div>

      <!-- Normal Input Layout -->
      <div v-else class="space-y-2">
        <!-- Top Toolbar inside PromptBar: Tags & Actions -->
        <div class="flex items-center justify-between px-1">
          <div class="flex items-center space-x-1.5 sm:space-x-2">
            <!-- Quick Data Source Trigger (@) -->
            <button
              type="button"
              @click.stop="toggleAtMenu"
              title="指定企业数据源 (@)"
              class="hidden sm:inline-flex items-center space-x-1 px-2 py-0.8 text-[11px] font-medium rounded-lg text-text-secondary hover:text-text-main hover:bg-slate-200/60 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
            >
              <Database class="w-3 h-3 text-brand-primary" />
              <span>@数据源</span>
            </button>

            <!-- Quick Command Trigger (/) -->
            <button
              type="button"
              @click.stop="toggleSlashMenu"
              title="常用指令 (/)"
              class="hidden sm:inline-flex items-center space-x-1 px-2 py-0.8 text-[11px] font-medium rounded-lg text-text-secondary hover:text-text-main hover:bg-slate-200/60 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
            >
              <Terminal class="w-3 h-3 text-brand-primary" />
              <span>/指令</span>
            </button>

            <!-- Active Data Tag Badge -->
            <span
              v-if="attachedSource"
              class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-brand-primary text-[10px] font-medium"
            >
              <BookOpen class="w-2.5 h-2.5" />
              <span class="max-w-[120px] truncate">{{ attachedSource }}</span>
              <X class="w-2.5 h-2.5 cursor-pointer hover:text-rose-500" @click="clearAttachedSource" />
            </span>
          </div>

          <!-- Right Status Info -->
          <div class="text-[10px] text-text-muted hidden md:flex items-center space-x-2">
            <span>Shift + Enter 换行 · Enter 发送</span>
          </div>
        </div>

        <!-- Textarea Input Area -->
        <div class="relative px-1">
          <textarea
            ref="textareaRef"
            v-model="inputContent"
            rows="1"
            :placeholder="placeholderText"
            class="w-full bg-transparent resize-none text-sm text-text-main placeholder-text-muted focus:outline-none leading-relaxed max-h-48 overflow-y-auto"
            @input="handleInput"
            @keydown="handleKeyDown"
          ></textarea>
        </div>

        <!-- Bottom Action Row: Voice, Attachments, Send/Stop Button -->
        <div class="flex items-center justify-between pt-1 px-1 border-t border-border-subtle/50">
          <div class="flex items-center space-x-1">
            <!-- Voice Input Button -->
            <button
              type="button"
              @click="isRecordingVoice = true"
              title="语音输入 (Advanced Voice)"
              class="p-1.5 rounded-xl text-text-secondary hover:text-text-main hover:bg-slate-200/60 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
            >
              <Mic class="w-4 h-4" />
            </button>

            <!-- Attachment Button (PDF / Excel / Image) -->
            <button
              type="button"
              title="上传规章文件与表格解析"
              class="p-1.5 rounded-xl text-text-secondary hover:text-text-main hover:bg-slate-200/60 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
              @click="handleUploadClick"
            >
              <Paperclip class="w-4 h-4" />
            </button>
            <input ref="fileInputRef" type="file" class="hidden" @change="handleFileChange" accept=".md,.pdf,.xlsx,.csv,.txt" />
          </div>

          <!-- Ink Charge Send Button OR Stop Square Button -->
          <div>
            <!-- If Streaming: Stop Square Button (Aborts stream) -->
            <button
              v-if="isStreaming"
              type="button"
              @click="$emit('abort')"
              title="停止响应 (Stop Square)"
              class="w-8 h-8 rounded-xl bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 flex items-center justify-center shadow-md hover:scale-105 active:scale-95 transition-all duration-150 cursor-pointer"
            >
              <Square class="w-3.5 h-3.5 fill-current" />
            </button>

            <!-- If Idle: Ink Charge Send Button -->
            <button
              v-else
              type="button"
              :disabled="!canSend"
              @click="handleSend"
              title="发送消息 (Enter)"
              class="w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-200 cursor-pointer disabled:opacity-40 disabled:pointer-events-none"
              :class="[
                canSend
                  ? 'bg-brand-primary text-white shadow-md shadow-blue-500/30 hover:bg-brand-primary-hover active:scale-95 scale-100'
                  : 'bg-slate-300 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
              ]"
            >
              <ArrowUp class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue';
import {
  Sparkles,
  Database,
  Terminal,
  Paperclip,
  Mic,
  ArrowUp,
  Square,
  BookOpen,
  X,
  FileText,
  Search,
  CheckCircle,
  HelpCircle
} from 'lucide-vue-next';
import VoicePill from './VoicePill.vue';

const props = defineProps({
  isStreaming: {
    type: Boolean,
    default: false,
  },
  modelValue: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['update:modelValue', 'send', 'abort']);

const inputContent = ref(props.modelValue || '');
const textareaRef = ref(null);
const fileInputRef = ref(null);
const barContainerRef = ref(null);
const isRecordingVoice = ref(false);
const attachedSource = ref('');
const attachedSourceId = ref('');

const showAtMenu = ref(false);
const showSlashMenu = ref(false);

const dataSources = [
  { id: 'kb_all', name: '全量企业规章制度库', desc: '包含差旅、采购、固定资产管理制度', icon: BookOpen },
  { id: 'db_mysql', name: 'MySQL 业务台账', desc: '实时物料库存、采购记录与组织架构', icon: Database },
  { id: 'erp_sap', name: 'ERP 采购与供应链', desc: 'SAP 采购订单与物料清单', icon: FileText },
];

const slashCommands = [
  { command: '/audit', desc: '唤醒审批协同面板，检查待审流程', icon: CheckCircle },
  { command: '/kb', desc: '指定规章制度检索并提取精确条款', icon: Search },
  { command: '/help', desc: '查看企业助手支持的功能列表与帮助', icon: HelpCircle },
];

const placeholderText = computed(() => {
  return '输入业务问题，数字员工将自动理解意图并检索规章制度回答...';
});

const canSend = computed(() => {
  return inputContent.value.trim().length > 0 && !props.isStreaming;
});

const autoResize = () => {
  const el = textareaRef.value;
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = `${Math.min(el.scrollHeight, 192)}px`;
};

const handleInput = (e) => {
  const val = e.target.value;
  inputContent.value = val;
  emit('update:modelValue', val);
  autoResize();

  // 侦测最后输入的字符
  const lastChar = val.slice(-1);
  if (lastChar === '@') {
    showAtMenu.value = true;
    showSlashMenu.value = false;
  } else if (lastChar === '/') {
    showSlashMenu.value = true;
    showAtMenu.value = false;
  } else if (val.endsWith(' ') || val === '') {
    showAtMenu.value = false;
    showSlashMenu.value = false;
  }
};

const toggleAtMenu = () => {
  showAtMenu.value = !showAtMenu.value;
  showSlashMenu.value = false;
};

const toggleSlashMenu = () => {
  showSlashMenu.value = !showSlashMenu.value;
  showAtMenu.value = false;
};

const clearAttachedSource = () => {
  attachedSource.value = '';
  attachedSourceId.value = '';
};

const insertDataSource = (source) => {
  attachedSource.value = source.name;
  attachedSourceId.value = source.id || '';
  if (inputContent.value.endsWith('@')) {
    inputContent.value = inputContent.value.slice(0, -1);
    emit('update:modelValue', inputContent.value);
  }
  showAtMenu.value = false;
  textareaRef.value?.focus();
};

const insertCommand = (cmd) => {
  if (inputContent.value.endsWith('/')) {
    inputContent.value = inputContent.value.slice(0, -1);
  }
  inputContent.value += `${cmd.command} `;
  emit('update:modelValue', inputContent.value);
  showSlashMenu.value = false;
  autoResize();
  textareaRef.value?.focus();
};

const handleKeyDown = (e) => {
  if (e.isComposing) return; // Prevent triggering while typing in IME (Pinyin/Chinese)
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (canSend.value) {
      handleSend();
    }
  } else if (e.key === 'Escape') {
    showAtMenu.value = false;
    showSlashMenu.value = false;
  }
};

let isSending = false;
const handleSend = () => {
  if (isSending) return;
  const text = inputContent.value.trim();
  if (!text || props.isStreaming) return;
  isSending = true;
  const slashMatch = text.match(/^\/([a-zA-Z]+)(?:\s+|$)/);
  const slashCommand = slashMatch ? slashMatch[1].toLowerCase() : '';
  emit('send', {
    text,
    source: attachedSource.value,
    sourceId: attachedSourceId.value,
    slashCommand,
  });
  inputContent.value = '';
  emit('update:modelValue', '');
  clearAttachedSource();
  showAtMenu.value = false;
  showSlashMenu.value = false;
  setTimeout(() => {
    isSending = false;
  }, 350);
  nextTick(() => {
    autoResize();
  });
};

const handleVoiceFinished = () => {
  isRecordingVoice.value = false;
  inputContent.value = '请帮我核对研发部 MacBook Pro 采购申请的最新制度标准，并提交审批。';
  emit('update:modelValue', inputContent.value);
  autoResize();
};

const handleUploadClick = () => {
  fileInputRef.value?.click();
};

const handleFileChange = (e) => {
  const file = e.target.files?.[0];
  if (file) {
    attachedSource.value = file.name;
    attachedSourceId.value = 'kb_all';
  }
};

const handleOutsideClick = (e) => {
  if (barContainerRef.value && !barContainerRef.value.contains(e.target)) {
    showAtMenu.value = false;
    showSlashMenu.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleOutsideClick);
  nextTick(autoResize);
});

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick);
});
</script>
