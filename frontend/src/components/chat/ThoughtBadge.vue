<template>
  <div class="my-2 select-none">
    <!-- ThoughtLine with Live Stopwatch, Breathing Beacon & Step Accordion -->
    <ThoughtLine
      :working="status === 'thinking'"
      :elapsed="durationSeconds"
      :steps="reasoningSteps"
      :preview="thoughtText"
      :collapsible="true"
      :collapse-on-settle="preferencesStore.autoCollapseThought"
    />

    <!-- Active Tool Execution Chips (CallChip) during/after retrieval -->
    <div v-if="toolCalls && toolCalls.length > 0" class="flex flex-wrap gap-1.5 my-1.5">
      <CallChip
        v-for="tool in toolCalls"
        :key="tool.name"
        :tool-name="tool.name"
        :status="tool.status"
        :duration-ms="tool.durationMs"
        :input-summary="tool.summary"
      />
    </div>

    <!-- Completed Knowledge Sources Accordion Capsule (Shown ONLY when real sources exist) -->
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
            <span class="text-[10px] text-text-muted">权威内网知识库</span>
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
              <p v-if="source.snippet" class="mt-1.5 text-[11px] text-text-secondary leading-relaxed line-clamp-3 font-sans pl-3 border-l-2 border-brand-primary/40">
                {{ source.snippet }}
              </p>

              <!-- Footer with ID & Action -->
              <div class="mt-2 pt-1.5 flex items-center justify-between text-[10px] text-text-muted border-t border-border-subtle/50">
                <span class="font-mono">编号: {{ source.doc_id || 'DOC-REF' }}</span>
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
import { usePreferencesStore } from '../../stores/preferencesStore';

const preferencesStore = usePreferencesStore();

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
  thoughtText: {
    type: String,
    default: '',
  },
  durationSeconds: {
    type: Number,
    default: undefined,
  },
  toolCalls: {
    type: Array,
    default: () => [],
  },
});

const isOpen = ref(false);

const formattedSources = computed(() => {
  return props.sources || [];
});

const hasSources = computed(() => {
  return formattedSources.value.length > 0;
});

const sourceCount = computed(() => {
  return formattedSources.value.length;
});

const displayTitle = computed(() => props.title);

const reasoningSteps = computed(() => {
  if (props.thoughtSteps && props.thoughtSteps.length > 0) {
    return props.thoughtSteps.map((s) => (typeof s === 'string' ? s : (s.title || String(s))));
  }
  return [];
});
</script>
