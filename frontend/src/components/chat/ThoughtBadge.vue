<template>
  <div class="my-2 select-none">
    <!-- Thinking State (Streaming / Retrieving) -->
    <div
      v-if="status === 'thinking'"
      class="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-900/90 border border-brand-primary/40 text-brand-primary text-xs shadow-sm shadow-blue-500/10 animate-pulse"
    >
      <Sparkles class="w-3.5 h-3.5 text-brand-primary animate-spin" style="animation-duration: 3s;" />
      <span class="font-medium text-slate-200">{{ displayTitle || '正在核对企业规章制度与库存数据...' }}</span>
      <div class="flex space-x-1 items-center">
        <span class="w-1 h-1 rounded-full bg-brand-primary animate-ping"></span>
      </div>
    </div>

    <!-- Completed State (Clickable Collapsible Capsule) -->
    <div v-else class="inline-block max-w-full">
      <button
        @click="isOpen = !isOpen"
        class="interactive-action inline-flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-slate-900/90 hover:bg-slate-800/90 border border-border-subtle hover:border-brand-primary/40 text-xs text-text-secondary hover:text-text-main shadow-sm transition-colors duration-150 cursor-pointer"
        :title="isOpen ? '收起知识来源' : '展开查看制度来源'"
      >
        <Sparkles class="w-3.5 h-3.5 text-brand-primary shrink-0" />
        <span class="font-medium text-slate-300">
          {{ displayTitle || `已参考 ${sourceCount} 篇规章制度与知识来源` }}
        </span>
        <span class="text-text-muted text-[11px]">·</span>
        <span class="text-[11px] text-brand-primary font-medium hover:underline">
          {{ isOpen ? '收起来源' : '展开查看来源' }}
        </span>
        <component
          :is="isOpen ? ChevronUp : ChevronDown"
          class="w-3.5 h-3.5 text-text-muted transition-transform duration-150 shrink-0"
        />
      </button>

      <!-- Smooth Collapsible Drawer for Sources & Citations (Zero Scale Reflow) -->
      <transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="max-h-0 opacity-0 transform -translate-y-1"
        enter-to-class="max-h-96 opacity-100 transform translate-y-0"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="max-h-96 opacity-100 transform translate-y-0"
        leave-to-class="max-h-0 opacity-0 transform -translate-y-1"
      >
        <div
          v-if="isOpen && hasSources"
          class="mt-2 p-3 rounded-2xl glass-card border border-border-card shadow-lg max-w-xl space-y-2.5 overflow-hidden"
        >
          <div class="flex items-center justify-between text-[11px] font-semibold text-text-secondary pb-1 border-b border-border-subtle">
            <span class="flex items-center space-x-1.5">
              <FileText class="w-3.5 h-3.5 text-brand-primary" />
              <span>知识库参考凭证 (已核验制度条款)</span>
            </span>
            <span class="text-[10px] text-text-muted">权威内网知识库 v2.6</span>
          </div>

          <!-- Sources Cards List -->
          <div class="space-y-2 max-h-56 overflow-y-auto pr-1">
            <div
              v-for="(source, idx) in formattedSources"
              :key="source.doc_id || idx"
              class="p-2.5 rounded-xl bg-slate-900/80 hover:bg-slate-800/80 border border-border-subtle text-xs transition-colors duration-150"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-1.5 font-medium text-text-main truncate max-w-[320px]">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></span>
                  <span class="truncate">{{ source.title }}</span>
                </div>
                <span v-if="source.tag" class="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-brand-primary font-mono shrink-0">
                  {{ source.tag }}
                </span>
              </div>

              <!-- Snippet Citation Text -->
              <p class="mt-1.5 text-[11px] text-text-secondary leading-relaxed line-clamp-3 font-sans pl-3 border-l border-brand-primary/30">
                {{ source.snippet }}
              </p>

              <!-- Footer with ID & Action -->
              <div class="mt-2 pt-1.5 flex items-center justify-between text-[10px] text-text-muted border-t border-border-subtle/50">
                <span class="font-mono">编号: {{ source.doc_id || 'DOC-2026-SOP' }}</span>
                <span class="flex items-center space-x-1 text-brand-primary hover:underline cursor-pointer">
                  <span>查看制度全文</span>
                  <ExternalLink class="w-3 h-3" />
                </span>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import {
  Sparkles,
  ChevronDown,
  ChevronUp,
  FileText,
  ExternalLink,
  CheckCircle2
} from 'lucide-vue-next';

const props = defineProps({
  status: {
    type: String,
    default: 'completed', // 'thinking' | 'completed'
  },
  title: {
    type: String,
    default: '',
  },
  sources: {
    type: Array,
    default: () => [],
  },
  thoughtSteps: {
    type: Array,
    default: () => [],
  },
});

const isOpen = ref(false);

const defaultSampleSources = [
  {
    doc_id: 'SOP-2026-081',
    title: '《企业IT资产采购与固定资产管理制度 (2026修订版)》',
    snippet: '第三章第十二条：研发人员申请配置高规格笔记本电脑（单价 ￥15,000 元以上），需经研发总监与业务归口负责人在线审批，并核对部门年度硬件预算额度。',
    tag: '固定资产规章',
  },
  {
    doc_id: 'SOP-2026-042',
    title: '《研发部硬件标准配置指南及 ERP 库存备件表》',
    snippet: 'AI 算法与大模型本地开发岗位可配置 MacBook Pro 16（64GB 内存规格及以上），目前北京园区仓库无闲置可用资产，建议发起新增采购申请。',
    tag: '硬件标准',
  },
];

const formattedSources = computed(() => {
  if (props.sources && props.sources.length > 0) {
    return props.sources;
  }
  return defaultSampleSources;
});

const hasSources = computed(() => formattedSources.value.length > 0);
const sourceCount = computed(() => formattedSources.value.length);

const displayTitle = computed(() => {
  if (props.title) return props.title;
  if (props.status === 'thinking') {
    return '正在核对企业规章制度与库存数据...';
  }
  return `已参考 ${sourceCount.value} 篇规章制度与知识来源`;
});
</script>
