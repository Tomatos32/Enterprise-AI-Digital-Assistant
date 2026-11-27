<template>
  <div class="h-full flex-1 flex flex-col lg:flex-row overflow-hidden bg-bg-main select-none transition-colors duration-180">
    <!-- Left Navigation: Knowledge Tree & Search Sidebar -->
    <aside
      class="w-full lg:w-80 shrink-0 border-b lg:border-b-0 lg:border-r border-border-subtle bg-bg-sidebar flex flex-col h-auto lg:h-full max-h-72 lg:max-h-full overflow-hidden"
    >
      <!-- Sidebar Header -->
      <div class="p-3.5 border-b border-border-subtle space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-7 h-7 rounded-lg bg-bg-card border border-border-card flex items-center justify-center text-text-main shrink-0">
              <BookOpen class="w-3.5 h-3.5" />
            </div>
            <div>
              <h2 class="text-xs sm:text-sm font-semibold text-text-main leading-tight">企业规章知识库</h2>
              <span class="text-[10px] text-text-muted">官方制度 · {{ allDocs.length }} 篇</span>
            </div>
          </div>
          <span class="px-2 py-0.5 rounded-md text-[10px] font-mono tabular-nums bg-bg-surface text-text-secondary border border-border-subtle">
            {{ filteredDocs.length }}/{{ allDocs.length }}
          </span>
        </div>

        <!-- View Mode Segment -->
        <div class="flex items-center gap-1 p-0.5 rounded-lg bg-bg-surface border border-border-subtle">
          <button
            type="button"
            @click="viewMode = 'reader'"
            class="btn-pressable flex-1 py-1 text-[11px] font-medium rounded-md flex items-center justify-center gap-1.5 border cursor-pointer"
            :class="
              viewMode === 'reader'
                ? 'bg-bg-card text-text-main border-border-card font-semibold'
                : 'border-transparent text-text-secondary hover:text-text-main'
            "
          >
            <FileText class="w-3 h-3" />
            <span>正文阅读</span>
          </button>
          <button
            type="button"
            @click="viewMode = 'folders'"
            class="btn-pressable flex-1 py-1 text-[11px] font-medium rounded-md flex items-center justify-center gap-1.5 border cursor-pointer"
            :class="
              viewMode === 'folders'
                ? 'bg-bg-card text-text-main border-border-card font-semibold'
                : 'border-transparent text-text-secondary hover:text-text-main'
            "
          >
            <Folder class="w-3 h-3" />
            <span>分类目录</span>
          </button>
        </div>

        <!-- Search Bar -->
        <div class="relative">
          <Search class="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索规章名称、条款或编号..."
            class="w-full pl-8 pr-3 py-1.5 bg-bg-input border border-border-card text-text-main placeholder-text-muted text-xs rounded-lg focus:outline-none focus:border-border-focus transition-colors duration-150"
          />
        </div>

        <!-- Category Filter Pills -->
        <div class="flex items-center gap-1 overflow-x-auto pb-0.5">
          <button
            v-for="cat in categories"
            :key="cat"
            type="button"
            @click="selectedCategory = cat"
            class="btn-pressable px-2.5 py-0.5 rounded-md text-[10px] font-medium border cursor-pointer shrink-0"
            :class="
              selectedCategory === cat
                ? 'bg-action-primary text-action-primary-fg border-action-primary'
                : 'bg-bg-card text-text-secondary border-border-subtle hover:text-text-main hover:border-border-card'
            "
          >
            {{ cat }}
          </button>
        </div>
      </div>

      <!-- Document List Tree -->
      <div class="flex-1 overflow-y-auto p-2 space-y-1.5">
        <button
          v-for="doc in filteredDocs"
          :key="doc.id"
          type="button"
          @click="selectDoc(doc)"
          class="btn-pressable w-full text-left p-2.5 rounded-lg border cursor-pointer group"
          :class="
            activeDoc.id === doc.id
              ? 'bg-bg-card border-border-strong'
              : 'bg-transparent border-transparent hover:bg-bg-hover hover:border-border-subtle'
          "
        >
          <div class="flex items-center justify-between mb-1">
            <span class="text-[10px] font-mono text-text-secondary font-medium">{{ doc.id }}</span>
            <span class="text-[9px] px-1.5 py-0.5 rounded bg-bg-surface border border-border-subtle text-text-muted">
              {{ doc.category }}
            </span>
          </div>
          <h4 class="text-xs font-semibold text-text-main truncate">
            {{ doc.title }}
          </h4>
          <p class="text-[11px] text-text-muted line-clamp-2 mt-1 leading-relaxed">
            {{ doc.summary }}
          </p>
        </button>

        <div v-if="filteredDocs.length === 0" class="py-8 text-center text-xs text-text-muted">
          未找到匹配的规章制度
        </div>
      </div>
    </aside>

    <!-- Right Reading & Query Viewport -->
    <main class="flex-1 flex flex-col h-full overflow-hidden bg-bg-main">
      <!-- Mode 1: Category Directory Grid -->
      <div v-if="viewMode === 'folders'" class="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
        <div class="max-w-5xl mx-auto space-y-6">
          <div class="border-b border-border-subtle pb-4">
            <h2 class="text-base sm:text-lg font-semibold text-text-main tracking-tight">企业规章分类目录</h2>
            <p class="text-xs text-text-muted mt-1">按业务领域选择并查阅对应制度全文</p>
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
      </div>

      <!-- Mode 2: Detailed Document Reader View -->
      <div v-else class="flex-1 flex flex-col h-full overflow-hidden">
        <!-- Article Header & Quick Actions -->
        <header class="px-4 sm:px-6 py-3.5 border-b border-border-subtle bg-bg-card flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
          <div>
            <div class="flex items-center gap-2 text-[11px] text-text-muted">
              <span class="font-mono text-text-secondary font-medium">{{ activeDoc.id }}</span>
              <span>·</span>
              <span>{{ activeDoc.category }}</span>
              <span>·</span>
              <span class="inline-flex items-center gap-1 text-status-success font-medium">
                <ShieldCheck class="w-3 h-3" />
                <span>生效版本</span>
              </span>
            </div>
            <h1 class="text-base sm:text-lg font-semibold text-text-main mt-0.5 tracking-tight">
              {{ activeDoc.title }}
            </h1>
          </div>

          <!-- Action Buttons -->
          <div class="flex items-center gap-2">
            <button
              type="button"
              @click="copyCitation"
              class="btn-secondary px-3 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer"
              title="复制制度引用格式"
            >
              <component :is="isCopied ? Check : Copy" class="w-3.5 h-3.5 text-text-secondary" />
              <span>{{ isCopied ? '已复制引用' : '复制引用' }}</span>
            </button>

            <button
              type="button"
              @click="askAboutPolicy"
              class="btn-primary px-3.5 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer"
              title="围绕当前制度发起提问"
            >
              <MessageSquare class="w-3.5 h-3.5" />
              <span>向助手提问</span>
            </button>
          </div>
        </header>

        <!-- Markdown Reading Body -->
        <div class="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 select-text">
          <div class="max-w-4xl mx-auto space-y-4">
            <!-- Policy Document Metadata Bar -->
            <div class="p-3.5 rounded-xl bg-bg-card border border-border-card flex flex-wrap items-center justify-between text-xs gap-4">
              <div class="flex flex-wrap items-center gap-6">
                <div>
                  <span class="text-[10px] text-text-muted block">版本编号</span>
                  <span class="font-mono tabular-nums text-text-main mt-0.5 block font-medium">
                    {{ activeDoc.version }}
                  </span>
                </div>
                <div>
                  <span class="text-[10px] text-text-muted block">密级要求</span>
                  <span class="text-text-main mt-0.5 block font-medium">{{ activeDoc.confidentiality }}</span>
                </div>
                <div>
                  <span class="text-[10px] text-text-muted block">最近修订</span>
                  <span class="font-mono tabular-nums text-text-main mt-0.5 block">
                    {{ activeDoc.updatedAt }}
                  </span>
                </div>
              </div>

              <span class="inline-flex items-center gap-1.5 text-[11px] text-text-secondary bg-bg-surface border border-border-subtle px-2.5 py-1 rounded-md">
                <span class="w-1.5 h-1.5 rounded-full bg-status-success"></span>
                <span>已纳入智能检索</span>
              </span>
            </div>

            <!-- Rendered Markdown Full Document -->
            <article
              class="markdown-body p-6 sm:p-8 rounded-xl bg-bg-card border border-border-card leading-relaxed text-text-main font-sans text-xs sm:text-sm"
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
  FileText,
  Folder,
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
    description: '涵盖办公设备配置标准、超额审批门禁与采购单流转。',
    lastUpdated: '2026-09-18',
  },
  {
    title: '差旅与日常业务招待报销规章',
    category: '财务报销',
    count: 9,
    description: '明确差旅住宿标准、交通舱位规范与发票合规要求。',
    lastUpdated: '2026-09-10',
  },
  {
    title: 'IT 系统安全与生产运维应急制度',
    category: '运维资产',
    count: 21,
    description: '涵盖故障响应时效、架构标准与容灾切换操作规范。',
    lastUpdated: '2026-09-22',
  },
  {
    title: '员工考勤年假与入职离职交接协同',
    category: '行政人事',
    count: 12,
    description: '年休假核算公式、休假审批流程与离职交接清单。',
    lastUpdated: '2026-08-30',
  },
  {
    title: '企业数据合规与敏感信息保护条例',
    category: '数据安全',
    count: 8,
    description: '隐私合规要求、权限隔离规范与敏感信息脱敏标准。',
    lastUpdated: '2026-09-20',
  },
  {
    title: '客户支持与服务级别协议 (SLA)',
    category: '客户服务',
    count: 6,
    description: '大客户工单响应承诺、超时升级规则与服务回执标准。',
    lastUpdated: '2026-08-15',
  },
];

const filteredDocs = computed(() => {
  return allDocs.filter((doc) => {
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
  const match = allDocs.find((d) => d.category === category);
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
      prompt: `请帮我解读《${activeDoc.value.title}》的核心条款与主要申报流程。`,
    },
  });
};
</script>
