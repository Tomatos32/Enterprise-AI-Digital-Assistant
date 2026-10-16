<template>
  <div class="my-2 select-none">
    <!-- ThoughtLine with Live Stopwatch, Breathing Beacon & Step Accordion -->
    <ThoughtLine
      :is-thinking="status === 'thinking'"
      :duration-seconds="calculatedDuration"
      :steps="reasoningSteps"
      :preview="previewText"
    />

    <!-- Active Tool Execution Chips (CallChip) during/after retrieval -->
    <div v-if="toolCalls.length > 0" class="flex flex-wrap gap-1.5 my-1.5">
      <CallChip
        v-for="tool in toolCalls"
        :key="tool.name"
        :tool-name="tool.name"
        :status="tool.status"
        :duration-ms="tool.durationMs"
        :input-summary="tool.summary"
      />
    </div>

    <!-- Completed Knowledge Sources Accordion Capsule -->
    <div v-if="status !== 'thinking' && hasSources" class="inline-block max-w-full mt-1">
      <button
        @click="isOpen = !isOpen"
        class="interactive-action inline-flex items-center space-x-2 px-3 py-1.5 rounded-xl glass-panel hover:bg-slate-200/50 dark:hover:bg-slate-800/50 border border-border-subtle hover:border-brand-primary/40 text-xs text-text-secondary hover:text-text-main shadow-sm transition-colors duration-150 cursor-pointer"
        :title="isOpen ? '收起知识来源' : '展开查看制度来源'"
      >
        <BookOpen class="w-3.5 h-3.5 text-brand-primary shrink-0" />
        <span class="font-medium text-text-main">
          {{ displayTitle || `已参考 ${sourceCount} 篇规章制度与知识来源` }}
        </span>
        <span class="text-text-muted text-[11px]">·</span>
        <span class="text-[11px] text-brand-primary font-medium hover:underline">
          {{ isOpen ? '收起来源' : '展开查看来源' }}
        </span>
        <ChevronDown
          class="w-3.5 h-3.5 text-text-muted transition-transform duration-150 shrink-0"
          :class="{ 'rotate-180': isOpen }"
        />
      </button>

      <!-- Smooth Collapsible Drawer for Sources & Citations -->
      <transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="max-h-0 opacity-0 transform -translate-y-1"
        enter-to-class="max-h-96 opacity-100 transform translate-y-0"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="max-h-96 opacity-100 transform translate-y-0"
        leave-to-class="max-h-0 opacity-0 transform -translate-y-1"
      >
        <div
          v-if="isOpen"
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
              class="p-2.5 rounded-xl bg-slate-100/80 dark:bg-slate-900/80 hover:bg-slate-200/80 dark:hover:bg-slate-800/80 border border-border-subtle text-xs transition-colors duration-150"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-1.5 font-medium text-text-main truncate max-w-[320px]">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></span>
                  <span class="truncate">{{ source.title }}</span>
                </div>
                <span v-if="source.tag" class="px-1.5 py-0.5 rounded text-[10px] bg-slate-200 dark:bg-slate-800 text-brand-primary font-mono shrink-0">
                  {{ source.tag }}
                </span>
              </div>

              <!-- Snippet Citation Text -->
              <p class="mt-1.5 text-[11px] text-text-secondary leading-relaxed line-clamp-3 font-sans pl-3 border-l-2 border-brand-primary/40">
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
  BookOpen,
  FileText,
  ExternalLink,
  ChevronDown
} from 'lucide-vue-next';
import ThoughtLine from '../ui/ThoughtLine.vue';
import CallChip from '../ui/CallChip.vue';

const props = defineProps({
  status: {
    type: String,
    default: 'completed',
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

const hasSources = computed(() => {
  return formattedSources.value.length > 0;
});

const sourceCount = computed(() => {
  return formattedSources.value.length;
});

const displayTitle = computed(() => props.title);

const calculatedDuration = computed(() => 1.8);

const reasoningSteps = computed(() => {
  if (props.thoughtSteps && props.thoughtSteps.length > 0) {
    return props.thoughtSteps;
  }
  return [
    { title: '解析用户采购申请意图，提取预算规格与设备型号', status: 'done' },
    { title: '调用 Qdrant 密集向量检索《企业IT固定资产管理制度》', status: 'done' },
    { title: '比对 ERP 备件库库存余量与研发部年度预算额度', status: 'done' },
    { title: '识别金额超 ￥5,000 元，自动挂载人机协同审批卡片', status: 'done' }
  ];
});

const previewText = computed(() => {
  return '正在核查采购审批金额门禁与部门权限标准...';
});

const toolCalls = computed(() => {
  return [
    { name: 'qdrant_retrieval', status: 'success', durationMs: 42, summary: 'IT固定资产规章' },
    { name: 'erp_check', status: 'success', durationMs: 18, summary: 'MacBook Pro 库存' },
  ];
});
</script>
