<template>
  <div class="relative w-full max-w-4xl mx-auto select-none" ref="barContainerRef">
    <!-- Popover Menu: @ Data Sources (Origin-Bottom-Left) -->
    <transition name="popover-up">
      <div
        v-if="showAtMenu"
        class="origin-bottom-left absolute bottom-full mb-2 left-2 w-72 rounded-xl bg-bg-card p-1.5 border border-border-card shadow-sm z-40 space-y-0.5"
      >
        <div class="px-2 py-1 text-[11px] font-medium text-text-muted">
          数据源 (@)
        </div>
        <button
          v-for="source in dataSources"
          :key="source.id"
          type="button"
          @click="insertDataSource(source)"
          class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-left text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer transition-colors duration-150"
        >
          <component :is="source.icon" class="w-4 h-4 text-text-secondary shrink-0" />
          <div class="flex-1 min-w-0">
            <div class="font-medium text-text-main truncate">{{ source.name }}</div>
            <div class="text-[11px] text-text-muted truncate">{{ source.desc }}</div>
          </div>
        </button>
      </div>
    </transition>

    <!-- Popover Menu: / Built-in Commands (Origin-Bottom-Left) -->
    <transition name="popover-up">
      <div
        v-if="showSlashMenu"
        class="origin-bottom-left absolute bottom-full mb-2 left-2 w-72 rounded-xl bg-bg-card p-1.5 border border-border-card shadow-sm z-40 space-y-0.5"
      >
        <div class="px-2 py-1 text-[11px] font-medium text-text-muted">
          快捷指令 (/)
        </div>
        <button
          v-for="cmd in slashCommands"
          :key="cmd.command"
          type="button"
          @click="insertCommand(cmd)"
          class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-left text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer transition-colors duration-150"
        >
          <component :is="cmd.icon" class="w-4 h-4 text-text-secondary shrink-0" />
          <div class="flex-1 min-w-0">
            <div class="font-mono font-medium text-text-main truncate">{{ cmd.command }}</div>
            <div class="text-[11px] text-text-muted truncate">{{ cmd.desc }}</div>
          </div>
        </button>
      </div>
    </transition>

    <!-- Main Linear Input Container -->
    <div
      class="rounded-xl p-2.5 sm:p-3 bg-bg-input border border-border-card transition-colors duration-150 focus-within:border-border-focus relative"
    >
      <!-- Voice Recording Overlay -->
      <div v-if="isRecordingVoice" class="p-1.5 flex items-center justify-between gap-2">
        <VoicePill
          :active="isRecordingVoice"
          @cancel="isRecordingVoice = false"
          @finish="handleVoiceFinished"
        />
        <span class="text-xs text-text-muted">点击停止生成文本</span>
      </div>

      <!-- Standard Input Layout -->
      <div v-else class="space-y-2">
        <!-- Top Toolbar -->
        <div class="flex items-center justify-between px-0.5">
          <div class="flex items-center gap-1.5">
            <button
              type="button"
              @click.stop="toggleAtMenu"
              title="指定数据源 (@)"
              class="btn-pressable hidden sm:inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer"
            >
              <Database class="w-3 h-3" />
              <span>@数据源</span>
            </button>

            <button
              type="button"
              @click.stop="toggleSlashMenu"
              title="快捷指令 (/)"
              class="btn-pressable hidden sm:inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer"
            >
              <Terminal class="w-3 h-3" />
              <span>/指令</span>
            </button>

            <span
              v-if="attachedSource"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-bg-surface border border-border-card text-text-main text-[11px] font-medium"
            >
              <BookOpen class="w-3 h-3 text-text-secondary" />
              <span class="max-w-[140px] truncate">{{ attachedSource }}</span>
              <button
                type="button"
                @click="clearAttachedSource"
                class="text-text-muted hover:text-text-main cursor-pointer"
                title="移除数据源"
              >
                <X class="w-3 h-3" />
              </button>
            </span>
          </div>

          <div class="text-[11px] text-text-muted hidden md:block">
            Shift + Enter 换行 · Enter 发送
          </div>
        </div>

        <!-- Textarea -->
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

        <!-- Bottom Action Row -->
        <div class="flex items-center justify-between pt-1.5 px-0.5 border-t border-border-subtle">
          <div class="flex items-center gap-1">
            <button
              type="button"
              @click="isRecordingVoice = true"
              title="语音输入"
              class="btn-pressable p-1.5 rounded-lg text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer"
            >
              <Mic class="w-4 h-4" />
            </button>

            <button
              type="button"
              title="附加文件"
              class="btn-pressable p-1.5 rounded-lg text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer"
              @click="handleUploadClick"
            >
              <Paperclip class="w-4 h-4" />
            </button>
            <input ref="fileInputRef" type="file" class="hidden" @change="handleFileChange" accept=".md,.pdf,.xlsx,.csv,.txt" />
          </div>

          <div>
            <!-- Streaming Stop Button -->
            <button
              v-if="isStreaming"
              type="button"
              @click="$emit('abort')"
              title="停止生成"
              class="btn-primary w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer"
            >
              <Square class="w-3 h-3 fill-current" />
            </button>

            <!-- High-Contrast Monochrome Send Button -->
            <button
              v-else
              type="button"
              :disabled="!canSend"
              @click="handleSend"
              title="发送 (Enter)"
              class="btn-pressable w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer disabled:opacity-35 disabled:pointer-events-none"
              :class="
                canSend
                  ? 'bg-action-primary text-action-primary-fg hover:bg-action-primary-hover'
                  : 'bg-bg-surface text-text-muted border border-border-subtle'
              "
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
  HelpCircle,
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
  { id: 'kb_all', name: '规章制度知识库', desc: '差旅、采购与固定资产制度', icon: BookOpen },
  { id: 'db_mysql', name: '业务台账数据库', desc: '库存、采购记录与组织架构', icon: Database },
  { id: 'erp_sap', name: 'ERP 供应链台账', desc: '采购订单与物料目录', icon: FileText },
];

const slashCommands = [
  { command: '/audit', desc: '查询当前待审批单据', icon: CheckCircle },
  { command: '/kb', desc: '定向检索规章制度条款', icon: Search },
  { command: '/help', desc: '查看可用功能与指令', icon: HelpCircle },
];

const placeholderText = computed(() => '输入问题、工单需求或采购申请...');

const canSend = computed(() => inputContent.value.trim().length > 0 && !props.isStreaming);

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
  if (e.isComposing) return;
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
  inputContent.value = '请帮我核对办公设备采购审批流程标准。';
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
