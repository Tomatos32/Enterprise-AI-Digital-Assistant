<template>
  <div class="my-1.5 select-none">
    <!-- ThoughtLine -->
    <ThoughtLine
      glyph="dot"
      :working="status === 'thinking'"
      :elapsed="durationSeconds"
      :steps="reasoningSteps"
      :preview="thoughtText"
      :collapsible="true"
      :collapse-on-settle="preferencesStore.autoCollapseThought"
    />

    <!-- Active Tool Execution Chips -->
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

    <!-- Completed Knowledge Sources Accordion -->
    <div v-if="status !== 'thinking' && hasSources" class="inline-block max-w-full mt-1">
      <button
        type="button"
        @click="isOpen = !isOpen"
        class="btn-secondary inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs cursor-pointer"
        :title="isOpen ? '收起引用来源' : '展开引用来源'"
      >
        <BookOpen class="w-3.5 h-3.5 text-text-secondary shrink-0" />
        <span class="font-medium text-text-main">
          {{ displayTitle || `参考了 ${sourceCount} 篇制度` }}
        </span>
        <ChevronDown
          class="w-3.5 h-3.5 text-text-muted transition-transform duration-150 shrink-0"
          :class="{ 'rotate-180': isOpen }"
        />
      </button>

      <transition name="popover">
        <div
          v-if="isOpen"
          class="origin-top-left mt-2 p-3 rounded-xl bg-bg-card border border-border-card max-w-xl space-y-2 overflow-hidden"
        >
          <div class="flex items-center justify-between text-[11px] font-medium text-text-muted pb-1.5 border-b border-border-subtle">
            <span class="inline-flex items-center gap-1.5">
              <FileText class="w-3.5 h-3.5" />
              <span>引用依据</span>
            </span>
            <span class="tabular-nums">{{ sourceCount }} 篇</span>
          </div>

          <div class="space-y-1.5 max-h-56 overflow-y-auto pr-1">
            <div
              v-for="(source, idx) in formattedSources"
              :key="source.doc_id || idx"
              class="p-2.5 rounded-lg bg-bg-surface border border-border-subtle text-xs"
            >
              <div class="flex items-center justify-between gap-2">
                <div class="font-medium text-text-main truncate max-w-[320px]">
                  {{ source.title }}
                </div>
                <span
                  v-if="source.tag"
                  class="px-1.5 py-0.5 rounded text-[10px] bg-bg-card text-text-secondary border border-border-subtle font-mono shrink-0"
                >
                  {{ source.tag }}
                </span>
              </div>

              <p
                v-if="source.snippet"
                class="mt-1.5 text-[11px] text-text-secondary leading-relaxed line-clamp-3 pl-2.5 border-l-2 border-border-strong"
              >
                {{ source.snippet }}
              </p>

              <div class="mt-2 pt-1.5 flex items-center justify-between text-[10px] text-text-muted border-t border-border-subtle">
                <span class="font-mono">{{ source.doc_id || 'DOC-REF' }}</span>
                <span class="inline-flex items-center gap-1 text-text-secondary">
                  <span>制度摘录</span>
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
import { BookOpen, FileText, ExternalLink, ChevronDown } from 'lucide-vue-next';
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

const formattedSources = computed(() => props.sources || []);
const hasSources = computed(() => formattedSources.value.length > 0);
const sourceCount = computed(() => formattedSources.value.length);
const displayTitle = computed(() => props.title);

const reasoningSteps = computed(() => {
  if (props.thoughtSteps && props.thoughtSteps.length > 0) {
    return props.thoughtSteps.map((s) => (typeof s === 'string' ? s : s.title || String(s)));
  }
  return [];
});
</script>
