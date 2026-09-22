<template>
  <div class="h-full flex-1 flex flex-col lg:flex-row overflow-hidden bg-bg-main select-none">
    <!-- Left Navigation: Knowledge Tree & Search Sidebar -->
    <aside
      class="w-full lg:w-80 shrink-0 border-b lg:border-b-0 lg:border-r border-border-subtle bg-bg-sidebar/90 flex flex-col h-auto lg:h-full max-h-72 lg:max-h-full overflow-hidden"
    >
      <!-- Sidebar Header -->
      <div class="p-3.5 border-b border-border-subtle space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <div class="w-7 h-7 rounded-xl bg-brand-primary/10 border border-brand-primary/30 flex items-center justify-center text-brand-primary shadow-sm">
              <BookOpen class="w-4 h-4" />
            </div>
            <div>
              <h2 class="text-xs sm:text-sm font-bold text-text-main">企业规章知识库</h2>
              <span class="text-[10px] text-text-muted">权威内网规章 v2.6 · 6 篇官方制度</span>
            </div>
          </div>
          <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 text-brand-primary border border-border-subtle">
            {{ filteredDocs.length }}/{{ allDocs.length }}
          </span>
        </div>

        <!-- Search Bar -->
        <div class="relative">
          <Search class="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索规章名称、条款或编号..."
            class="w-full pl-8 pr-3 py-1.5 bg-slate-900/90 border border-border-subtle text-text-main placeholder-text-muted text-xs rounded-xl focus:outline-none focus:border-brand-primary transition-colors duration-150"
          />
        </div>

        <!-- Category Filter Pills -->
        <div class="flex items-center space-x-1 overflow-x-auto pb-0.5">
          <button
            v-for="cat in categories"
            :key="cat"
            @click="selectedCategory = cat"
            class="interactive-action px-2 py-0.5 rounded-lg text-[10px] font-medium transition-colors duration-150 cursor-pointer shrink-0"
            :class="selectedCategory === cat ? 'bg-brand-primary text-white shadow-sm' : 'text-text-secondary hover:text-text-main bg-slate-900/80'"
          >
            {{ cat }}
          </button>
        </div>
      </div>

      <!-- Document List Tree -->
      <div class="flex-1 overflow-y-auto p-2 space-y-1.5">
        <div
          v-for="doc in filteredDocs"
          :key="doc.id"
          @click="selectDoc(doc)"
          class="interactive-action p-2.5 rounded-xl border cursor-pointer transition-all duration-150 group"
          :class="activeDoc.id === doc.id ? 'bg-slate-800/90 border-brand-primary/50 shadow-md ring-1 ring-brand-primary/20' : 'bg-slate-900/40 hover:bg-slate-800/50 border-border-subtle'"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="text-[10px] font-mono text-brand-primary font-medium">{{ doc.id }}</span>
            <span class="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-text-muted font-sans">{{ doc.category }}</span>
          </div>
          <h4 class="text-xs font-semibold text-text-main group-hover:text-brand-primary transition-colors duration-150 truncate">
            {{ doc.title }}
          </h4>
          <p class="text-[11px] text-text-secondary line-clamp-2 mt-1 leading-relaxed">
            {{ doc.summary }}
          </p>
        </div>

        <div v-if="filteredDocs.length === 0" class="py-8 text-center text-xs text-text-muted">
          未找到匹配规章制度
        </div>
      </div>
    </aside>

    <!-- Right Reading & Query Viewport -->
    <main class="flex-1 flex flex-col h-full overflow-hidden bg-bg-main">
      <!-- Article Header & Quick Actions -->
      <header class="p-4 sm:px-6 py-3.5 border-b border-border-subtle bg-slate-950/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
        <div>
          <div class="flex items-center space-x-2 text-[11px] text-text-muted">
            <span class="font-mono text-brand-primary font-medium">{{ activeDoc.id }}</span>
            <span>·</span>
            <span>{{ activeDoc.category }}</span>
            <span>·</span>
            <span class="text-emerald-400 flex items-center space-x-1">
              <ShieldCheck class="w-3 h-3" />
              <span>权威发布版</span>
            </span>
          </div>
          <h1 class="text-base sm:text-lg font-bold text-text-main mt-0.5">
            {{ activeDoc.title }}
          </h1>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center space-x-2">
          <!-- Copy Citation -->
          <button
            @click="copyCitation"
            class="interactive-action px-3 py-1.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-xs text-text-secondary hover:text-text-main border border-border-subtle flex items-center space-x-1.5 transition-colors duration-150 cursor-pointer shadow-sm"
            title="复制制度引用格式"
          >
            <component :is="isCopied ? Check : Copy" class="w-3.5 h-3.5 text-text-secondary" />
            <span>{{ isCopied ? '已复制引用' : '复制引用' }}</span>
          </button>

          <!-- Ask Digital Assistant Prompt -->
          <button
            @click="askAboutPolicy"
            class="interactive-action px-3.5 py-1.5 rounded-xl bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-medium flex items-center space-x-1.5 shadow-md shadow-blue-500/20 transition-colors duration-150 cursor-pointer"
            title="向企业数字员工提问此制度"
          >
            <MessageSquare class="w-3.5 h-3.5" />
            <span>向数字员工提问</span>
          </button>
        </div>
      </header>

      <!-- Markdown Reading Body -->
      <div class="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
        <div class="max-w-4xl mx-auto space-y-4">
          <!-- Policy Document Metadata Card -->
          <div class="p-3.5 rounded-2xl glass-card border border-border-card bg-slate-900/60 shadow-sm flex flex-wrap items-center justify-between text-xs gap-3">
            <div class="flex items-center space-x-4">
              <div>
                <span class="text-[10px] text-text-muted block">版本编号</span>
                <span class="font-mono text-slate-200 mt-0.5 block font-medium">{{ activeDoc.version }}</span>
              </div>
              <div>
                <span class="text-[10px] text-text-muted block">密级要求</span>
                <span class="text-slate-200 mt-0.5 block font-medium">{{ activeDoc.confidentiality }}</span>
              </div>
              <div>
                <span class="text-[10px] text-text-muted block">最近修订日</span>
                <span class="font-mono text-slate-200 mt-0.5 block">{{ activeDoc.updatedAt }}</span>
              </div>
            </div>

            <div class="flex items-center space-x-1.5 text-[11px] text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-lg">
              <Sparkles class="w-3 h-3 text-amber-400" />
              <span>支持全量向量检索与 LangGraph 自动引用</span>
            </div>
          </div>

          <!-- Rendered Markdown Full Document -->
          <article
            class="markdown-body p-6 sm:p-8 rounded-3xl glass-card border border-border-card bg-slate-950/70 shadow-lg leading-relaxed text-text-main font-sans text-xs sm:text-sm"
            v-html="renderedMarkdownContent"
          ></article>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import {
  BookOpen,
  Search,
  Check,
  Copy,
  MessageSquare,
  ShieldCheck,
  Sparkles
} from 'lucide-vue-next';
import { enterpriseKnowledgeDocs } from '../data/knowledgeBase';
import { renderMarkdown } from '../utils/markdown';

const router = useRouter();

const allDocs = enterpriseKnowledgeDocs;
const selectedCategory = ref('全部');
const searchQuery = ref('');
const activeDoc = ref(allDocs[0]);
const isCopied = ref(false);

const categories = ['全部', '采购审批', '行政人事', '运维资产', '财务报销', '数据安全', '客户服务'];

const filteredDocs = computed(() => {
  return allDocs.filter(doc => {
    // 分类筛选
    if (selectedCategory.value !== '全部' && doc.category !== selectedCategory.value) {
      return false;
    }

    // 关键词搜索
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase();
      const matchTitle = doc.title.toLowerCase().includes(q);
      const matchId = doc.id.toLowerCase().includes(q);
      const matchSummary = doc.summary.toLowerCase().includes(q);
      const matchContent = doc.content.toLowerCase().includes(q);
      return matchTitle || matchId || matchSummary || matchContent;
    }

    return true;
  });
});

const selectDoc = (doc) => {
  activeDoc.value = doc;
};

const renderedMarkdownContent = computed(() => {
  return renderMarkdown(activeDoc.value.content);
});

const copyCitation = async () => {
  const citation = `《${activeDoc.value.title}》（编号：${activeDoc.value.id}，版本：${activeDoc.value.version}）`;
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(citation);
      isCopied.value = true;
      setTimeout(() => {
        isCopied.value = false;
      }, 2000);
    }
  } catch (e) {
    console.warn('Clipboard write failed:', e);
  }
};

const askAboutPolicy = () => {
  const prompt = `请帮我解读《${activeDoc.value.title}》的核心要点与员工操作指南`;
  router.push({
    path: '/',
    query: { prompt }
  });
};
</script>
