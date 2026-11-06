<template>
  <aside
    class="h-full flex flex-col justify-between shrink-0 select-none overflow-hidden relative bg-bg-sidebar border-r border-border-subtle transition-all duration-200 ease-out z-20"
    :class="isCollapsed ? 'w-16' : 'w-64'"
  >
    <!-- Top Brand & Collapse Toggle Bar -->
    <div class="p-3 flex items-center justify-between border-b border-border-subtle/60">
      <!-- Expanded Brand Header -->
      <div v-if="!isCollapsed" class="flex items-center space-x-2.5 overflow-hidden">
        <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center shadow-md shadow-blue-500/20 shrink-0">
          <Sparkles class="w-4 h-4 text-white" />
        </div>
        <div class="truncate">
          <h2 class="text-sm font-bold text-text-main leading-tight truncate flex items-center space-x-1">
            <ShinyText text="企业数字员工" />
            <span class="text-[10px] px-1 py-0.2 rounded bg-brand-primary/20 text-brand-primary font-mono">PRO</span>
          </h2>
          <p class="text-[10px] text-text-muted leading-tight">AI Copilot Studio</p>
        </div>
      </div>

      <!-- Collapsed Brand Icon -->
      <div v-else class="w-full flex justify-center mb-1">
        <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center shadow-md shadow-blue-500/20">
          <Sparkles class="w-4 h-4 text-white" />
        </div>
      </div>

      <!-- Collapse Toggle Button -->
      <button
        v-if="!isCollapsed"
        @click="$emit('update:isCollapsed', true)"
        title="收起侧边栏"
        class="p-1.5 rounded-lg text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-800/80 transition-colors duration-150 cursor-pointer"
      >
        <ChevronLeft class="w-4 h-4" />
      </button>
    </div>

    <!-- [+ 新建对话] Action Section -->
    <div class="p-3">
      <button
        v-if="!isCollapsed"
        @click="handleNewChat"
        class="w-full py-2 px-3 rounded-xl bg-brand-primary/10 hover:bg-brand-primary/20 text-brand-primary border border-brand-primary/30 flex items-center justify-center space-x-2 text-xs font-semibold shadow-sm transition-all duration-150 cursor-pointer group active:scale-95"
      >
        <Plus class="w-4 h-4 transition-transform duration-150 group-hover:rotate-90" />
        <span>新建对话</span>
      </button>

      <button
        v-else
        @click="handleNewChat"
        title="新建对话"
        class="w-10 h-10 mx-auto rounded-xl bg-brand-primary/10 hover:bg-brand-primary/20 text-brand-primary border border-brand-primary/30 flex items-center justify-center transition-all duration-150 cursor-pointer active:scale-95"
      >
        <Plus class="w-4 h-4" />
      </button>
    </div>

    <!-- Middle: Sessions Scroll Area with LineSidebar (Cursor Proximity Effect) -->
    <div v-if="!isCollapsed" class="flex-1 overflow-y-auto px-2 space-y-4">
      <!-- Group: 今天 -->
      <div v-if="chatStore.todaySessions.length > 0">
        <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">今天</div>
        <div class="space-y-0.5">
          <LineSidebar
            v-for="s in chatStore.todaySessions"
            :key="s.id"
            :title="s.title"
            :active="s.id === chatStore.activeSessionId"
            @select="handleSelect(s.id)"
            @delete="chatStore.deleteSession(s.id)"
          />
        </div>
      </div>

      <!-- Group: 昨天 -->
      <div v-if="chatStore.yesterdaySessions.length > 0">
        <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">昨天</div>
        <div class="space-y-0.5">
          <LineSidebar
            v-for="s in chatStore.yesterdaySessions"
            :key="s.id"
            :title="s.title"
            :active="s.id === chatStore.activeSessionId"
            @select="handleSelect(s.id)"
            @delete="chatStore.deleteSession(s.id)"
          />
        </div>
      </div>

      <!-- Group: 前 7 天 -->
      <div v-if="chatStore.previous7DaysSessions.length > 0">
        <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">前 7 天</div>
        <div class="space-y-0.5">
          <LineSidebar
            v-for="s in chatStore.previous7DaysSessions"
            :key="s.id"
            :title="s.title"
            :active="s.id === chatStore.activeSessionId"
            @select="handleSelect(s.id)"
            @delete="chatStore.deleteSession(s.id)"
          />
        </div>
      </div>

      <!-- Group: 更早历史 -->
      <div v-if="chatStore.olderSessions.length > 0">
        <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">更早</div>
        <div class="space-y-0.5">
          <LineSidebar
            v-for="s in chatStore.olderSessions"
            :key="s.id"
            :title="s.title"
            :active="s.id === chatStore.activeSessionId"
            @select="handleSelect(s.id)"
            @delete="chatStore.deleteSession(s.id)"
          />
        </div>
      </div>

      <!-- Fallback: 如果没有匹配上任何日期分组，直接完整列出所有历史会话，绝对不隐藏任何记录 -->
      <div
        v-if="
          chatStore.todaySessions.length === 0 &&
          chatStore.yesterdaySessions.length === 0 &&
          chatStore.previous7DaysSessions.length === 0 &&
          chatStore.olderSessions.length === 0 &&
          chatStore.sessions.length > 0
        "
      >
        <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">全部对话</div>
        <div class="space-y-0.5">
          <LineSidebar
            v-for="s in chatStore.sessions"
            :key="s.id"
            :title="s.title"
            :active="s.id === chatStore.activeSessionId"
            @select="handleSelect(s.id)"
            @delete="chatStore.deleteSession(s.id)"
          />
        </div>
      </div>
    </div>

    <!-- Middle: Collapsed Recent Icon Dots (Collapsed) -->
    <div v-else class="flex-1 flex flex-col items-center py-4 space-y-3 overflow-y-auto">
      <button
        @click="$emit('update:isCollapsed', false)"
        title="展开侧边栏"
        class="p-2 rounded-xl text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-800 transition-colors duration-150 cursor-pointer"
      >
        <ChevronRight class="w-4 h-4" />
      </button>

      <div class="w-8 border-t border-border-subtle my-2"></div>

      <button
        v-for="s in chatStore.sessions.slice(0, 5)"
        :key="s.id"
        @click="handleSelect(s.id)"
        :title="s.title"
        class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-150 cursor-pointer"
        :class="s.id === chatStore.activeSessionId ? 'bg-brand-primary/20 text-brand-primary' : 'text-text-muted hover:text-text-secondary hover:bg-slate-200/50 dark:hover:bg-slate-900'"
      >
        <MessageSquare class="w-4 h-4" />
      </button>
    </div>

    <!-- Lower: Business Workspaces Navigation -->
    <div class="p-2 border-t border-border-subtle bg-slate-200/40 dark:bg-slate-950/40">
      <div v-if="!isCollapsed" class="px-2 pb-1 text-[11px] font-semibold text-text-muted tracking-wider">
        企业业务协同
      </div>

      <nav class="space-y-1">
        <!-- 待我审批入口 -->
        <router-link
          to="/approvals"
          class="relative flex items-center rounded-xl p-2 text-xs transition-colors duration-150 cursor-pointer"
          :class="isCollapsed ? 'w-10 h-10 mx-auto justify-center' : 'justify-between px-2.5'"
          active-class="bg-slate-200/70 dark:bg-slate-800 text-status-approval font-semibold"
          :title="isCollapsed ? `待我审批 (${pendingApprovalsCount})` : ''"
        >
          <div class="flex items-center space-x-2.5 truncate">
            <ClipboardList class="w-4 h-4 text-status-approval shrink-0" />
            <span v-if="!isCollapsed" class="text-text-secondary hover:text-text-main truncate">待我审批</span>
          </div>
          <span
            v-if="!isCollapsed && pendingApprovalsCount > 0"
            class="px-1.5 py-0.2 text-[10px] font-bold rounded-full bg-amber-500/20 text-status-approval border border-amber-500/30"
          >
            {{ pendingApprovalsCount }}
          </span>
          <span
            v-else-if="isCollapsed && pendingApprovalsCount > 0"
            class="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-400 ring-2 ring-slate-900 animate-pulse"
          ></span>
        </router-link>

        <!-- 规章制度检索入口 -->
        <router-link
          to="/knowledge"
          class="flex items-center rounded-xl p-2 text-xs transition-colors duration-150 cursor-pointer"
          :class="isCollapsed ? 'w-10 h-10 mx-auto justify-center' : 'space-x-2.5 px-2.5'"
          active-class="bg-slate-200/70 dark:bg-slate-800 text-brand-primary font-semibold"
          :title="isCollapsed ? '企业规章知识库' : ''"
        >
          <BookOpen class="w-4 h-4 text-brand-primary shrink-0" />
          <span v-if="!isCollapsed" class="text-text-secondary hover:text-text-main truncate">规章制度知识库</span>
        </router-link>
      </nav>
    </div>

    <!-- Bottom User Profile Footer -->
    <div class="p-3 border-t border-border-subtle bg-slate-200/60 dark:bg-slate-950/70 flex items-center justify-between">
      <!-- Expanded Profile -->
      <div v-if="!isCollapsed" class="flex items-center space-x-2.5 overflow-hidden">
        <div class="w-8 h-8 rounded-full bg-slate-300 dark:bg-slate-800 border border-border-card flex items-center justify-center text-text-secondary shrink-0">
          <User class="w-4 h-4 text-slate-700 dark:text-slate-300" />
        </div>
        <div class="truncate">
          <div class="text-xs font-semibold text-text-main truncate">张经理</div>
          <div class="text-[10px] text-text-muted truncate">研发部 · 业务审批人</div>
        </div>
      </div>

      <!-- Collapsed Profile Avatar -->
      <div v-else class="w-full flex justify-center" title="张经理 (研发部)">
        <div class="w-8 h-8 rounded-full bg-slate-300 dark:bg-slate-800 border border-border-card flex items-center justify-center text-text-secondary">
          <User class="w-4 h-4 text-slate-700 dark:text-slate-300" />
        </div>
      </div>

      <button
        v-if="!isCollapsed"
        title="系统设置"
        class="p-1.5 text-text-muted hover:text-text-main rounded-lg hover:bg-slate-300/50 dark:hover:bg-slate-800 transition-colors duration-150 cursor-pointer"
      >
        <Settings class="w-4 h-4" />
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue';
import {
  MessageSquare,
  Plus,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  BookOpen,
  Settings,
  User,
  Sparkles
} from 'lucide-vue-next';
import { useChatStore } from '../../stores/chatStore';
import { useApprovalStore } from '../../stores/approvalStore';
import { useRouter } from 'vue-router';
import LineSidebar from '../ui/LineSidebar.vue';
import ShinyText from '../ui/ShinyText.vue';

const props = defineProps({
  isCollapsed: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['update:isCollapsed', 'newSession', 'selectSession']);

const chatStore = useChatStore();
const approvalStore = useApprovalStore();
const router = useRouter();

const pendingApprovalsCount = computed(() => {
  return approvalStore.pendingApprovals.length;
});

const handleNewChat = () => {
  chatStore.createSession();
  emit('newSession');
  router.push('/');
};

const handleSelect = (id) => {
  chatStore.switchSession(id);
  emit('selectSession', id);
  router.push('/');
};
</script>
