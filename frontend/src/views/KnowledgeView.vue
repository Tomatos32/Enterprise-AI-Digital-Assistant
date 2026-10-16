<template>
  <div class="h-full flex-1 flex flex-col lg:flex-row overflow-hidden bg-bg-main select-none transition-colors duration-200">
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
          <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-200 dark:bg-slate-800 text-brand-primary border border-border-subtle">
            {{ filteredDocs.length }}/{{ allDocs.length }}
          </span>
        </div>

        <!-- View Mode Segment (List vs 3D Folder Cloud) -->
        <div class="flex items-center space-x-1 p-0.5 rounded-xl bg-slate-200/60 dark:bg-slate-900/60 border border-border-subtle">
          <button
            @click="viewMode = 'reader'"
            class="flex-1 py-1 text-[11px] font-medium rounded-lg transition-colors duration-150 flex items-center justify-center space-x-1"
            :class="viewMode === 'reader' ? 'bg-white dark:bg-slate-800 text-text-main shadow-sm font-semibold' : 'text-text-secondary hover:text-text-main'"
          >
            <FileText class="w-3 h-3" />
            <span>阅读模式</span>
          </button>
          <button
            @click="viewMode = 'folders'"
            class="flex-1 py-1 text-[11px] font-medium rounded-lg transition-colors duration-150 flex items-center justify-center space-x-1"
            :class="viewMode === 'folders' ? 'bg-white dark:bg-slate-800 text-text-main shadow-sm font-semibold' : 'text-text-secondary hover:text-text-main'"
          >
            <Folder class="w-3 h-3" />
            <span>分类文件夹云</span>
          </button>
        </div>

        <!-- Search Bar -->
        <div class="relative">
          <Search class="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索规章名称、条款或编号..."
            class="w-full pl-8 pr-3 py-1.5 glass-panel border border-border-subtle text-text-main placeholder-text-muted text-xs rounded-xl focus:outline-none focus:border-brand-primary transition-colors duration-150"
          />
        </div>

        <!-- Category Filter Pills -->
        <div class="flex items-center space-x-1 overflow-x-auto pb-0.5">
          <button
            v-for="cat in categories"
            :key="cat"
            @click="selectedCategory = cat"
            class="interactive-action px-2 py-0.5 rounded-lg text-[10px] font-medium transition-colors duration-150 cursor-pointer shrink-0"
            :class="selectedCategory === cat ? 'bg-brand-primary text-white shadow-sm' : 'text-text-secondary hover:text-text-main glass-panel'"
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
          :class="activeDoc.id === doc.id ? 'bg-slate-200/80 dark:bg-slate-800/90 border-brand-primary/50 shadow-md ring-1 ring-brand-primary/20' : 'glass-card hover:bg-slate-200/50 dark:hover:bg-slate-800/50 border-border-subtle'"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="text-[10px] font-mono text-brand-primary font-medium">{{ doc.id }}</span>
            <span class="text-[9px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-text-muted font-sans">{{ doc.category }}</span>
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
      <!-- Mode 1: 3D Folder Float Cards Cloud -->
      <div v-if="viewMode === 'folders'" class="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
        <div>
          <h2 class="text-base sm:text-lg font-bold text-text-main">企业知识库核心业务分类</h2>
          <p class="text-xs text-text-secondary mt-1">悬停体验 3D 浮动翻盖与知识卡片云，点击直达各领域规章制度全文</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <FolderFloat
            v-for="folder in folderCategories"
            :key="folder.title"
            :title="folder.title"
            :category="folder.category"
            :count="folder.count"
            :description="folder.description"
            :last-updated="folder.lastUpdated"
            @click="handleFolderClick(folder.category)"
          />
        </div>
      </div>

      <!-- Mode 2: Detailed Document Reader View -->
      <div v-else class="flex-1 flex flex-col h-full overflow-hidden">
        <!-- Article Header & Quick Actions -->
        <header class="p-4 sm:px-6 py-3.5 border-b border-border-subtle glass-panel flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
          <div>
            <div class="flex items-center space-x-2 text-[11px] text-text-muted">
              <span class="font-mono text-brand-primary font-medium">{{ activeDoc.id }}</span>
              <span>·</span>
              <span>{{ activeDoc.category }}</span>
              <span>·</span>
              <span class="text-emerald-500 flex items-center space-x-1">
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
              class="interactive-action px-3 py-1.5 rounded-xl glass-panel hover:bg-slate-200/50 dark:hover:bg-slate-800 text-xs text-text-secondary hover:text-text-main border border-border-subtle flex items-center space-x-1.5 transition-colors duration-150 cursor-pointer shadow-sm"
              title="复制制度引用格式"
            >
              <component :is="isCopied ? Check : Copy" class="w-3.5 h-3.5 text-text-secondary" />
              <span>{{ isCopied ? '已复制引用' : '复制引用' }}</span>
            </button>

            <!-- Ask Digital Assistant Prompt -->
            <button
              @click="askAboutPolicy"
              class="interactive-action px-3.5 py-1.5 rounded-xl bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-medium flex items-center space-x-1.5 shadow-md shadow-blue-500/20 transition-colors duration-150 cursor-pointer active:scale-95"
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
            <div class="p-3.5 rounded-2xl glass-card border border-border-card shadow-sm flex flex-wrap items-center justify-between text-xs gap-3">
              <div class="flex items-center space-x-4">
                <div>
                  <span class="text-[10px] text-text-muted block">版本编号</span>
                  <span class="font-mono text-text-main mt-0.5 block font-medium">{{ activeDoc.version }}</span>
                </div>
                <div>
                  <span class="text-[10px] text-text-muted block">密级要求</span>
                  <span class="text-text-main mt-0.5 block font-medium">{{ activeDoc.confidentiality }}</span>
                </div>
                <div>
                  <span class="text-[10px] text-text-muted block">最近修订日</span>
                  <span class="font-mono text-text-main mt-0.5 block">{{ activeDoc.updatedAt }}</span>
                </div>
              </div>

              <div class="flex items-center space-x-1.5 text-[11px] text-amber-600 dark:text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-lg">
                <Sparkles class="w-3 h-3 text-amber-500" />
                <span>支持全量向量检索与 LangGraph 自动引用</span>
              </div>
            </div>

            <!-- Rendered Markdown Full Document -->
            <article
              class="markdown-body p-6 sm:p-8 rounded-3xl glass-card border border-border-card shadow-lg leading-relaxed text-text-main font-sans text-xs sm:text-sm"
              v-html="renderedMarkdownContent"
            ></article>
          </div>
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
  Sparkles,
  FileText,
  Folder
} from 'lucide-vue-next';
import { enterpriseKnowledgeDocs } from '../data/knowledgeBase';
import { renderMarkdown } from '../utils/markdown';
import FolderFloat from '../components/ui/FolderFloat.vue';

const router = useRouter();

const allDocs = enterpriseKnowledgeDocs;
const selectedCategory = ref('全部');
const searchQuery = ref('');
const activeDoc = ref(allDocs[0]);
const isCopied = ref(false);
const viewMode = ref('reader');

const categories = ['全部', '采购审批', '行政人事', '运维资产', '财务报销', '数据安全', '客户服务'];

const folderCategories = [
  {
    title: '固定资产与硬件采购管理规程',
    category: '采购审批',
    count: 14,
    description: '涵盖 MacBook Pro 等大额办公电脑设备配置标准、超额审批门禁与 ERP 采购单流转。',
    lastUpdated: '2026-09-18',
  },
  {
    title: '差旅与日常业务招待报销规章',
    category: '财务报销',
    count: 9,
    description: '明确差旅酒店城市标准、交通工具舱位门禁、发票税务合规及超标自理规定。',
    lastUpdated: '2026-09-10',
  },
  {
    title: 'IT 系统安全与生产运维应急制度',
    category: '运维资产',
    count: 21,
    description: '涵盖 P1~P4 级线上故障响应时效、数据库读写分离架构标准及容灾切换操作指南。',
    lastUpdated: '2026-09-22',
  },
  {
    title: '员工考勤年假与入职离职交接协同',
    category: '行政人事',
    count: 12,
    description: '年休假核算公式、病假事假审批流程及研发保密协议离职交接要点清单。',
    lastUpdated: '2026-08-30',
  },
  {
    title: '企业数据合规与大模型敏感数据脱敏',
    category: '数据安全',
    count: 8,
    description: '用户 PII 隐私合规条例、Prompt 防注入护栏标准及敏感信息流式拦截规则。',
    lastUpdated: '2026-09-20',
  },
  {
    title: '客户支持与服务级别协议 (SLA)',
    category: '客户服务',
    count: 6,
    description: '企业大客户工单响应承诺标准、超时工单升级规则与客服智能工单自动回执流程。',
    lastUpdated: '2026-08-15',
  },
];

const filteredDocs = computed(() => {
  return allDocs.filter(doc => {
    if (selectedCategory.value !== '全部' && doc.category !== selectedCategory.value) {
      return false;
    }

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
  viewMode.value = 'reader';
};

const handleFolderClick = (category) => {
  selectedCategory.value = category;
  const match = allDocs.find(d => d.category === category);
  if (match) {
    activeDoc.value = match;
  }
  viewMode.value = 'reader';
};

const renderedMarkdownContent = computed(() => {
  return renderMarkdown(activeDoc.value.content);
});

const copyCitation = async () => {
  const citationText = `[参考来源: ${activeDoc.value.title} (${activeDoc.value.id} v${activeDoc.value.version})]`;
  try {
    await navigator.clipboard.writeText(citationText);
    isCopied.value = true;
    setTimeout(() => {
      isCopied.value = false;
    }, 2000);
  } catch (err) {
    // 忽略剪贴板访问异常
  }
};

const askAboutPolicy = () => {
  router.push({
    path: '/',
    query: {
      prompt: `请帮我解读《${activeDoc.value.title}》的核心条款与主要申报流程。`
    }
  });
};
</script>
