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
            <span class="text-[10px] px-1 py-0.5 rounded bg-brand-primary/20 text-brand-primary font-mono">PRO</span>
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
    <div class="p-2 border-t border-border-subtle bg-slate-200/40 dark:bg-slate-950/40 space-y-2">
      <div>
        <div v-if="!isCollapsed" class="px-2 pb-1 text-[11px] font-semibold text-text-muted tracking-wider">
          企业业务协同
        </div>

        <nav class="space-y-1">
          <!-- 待我审批入口 (仅部门主管与系统管理员可见) -->
          <router-link
            v-if="authStore.canApprove"
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
              class="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-status-approval border border-amber-500/30"
            >
              {{ pendingApprovalsCount }}
            </span>
            <span
              v-else-if="isCollapsed && pendingApprovalsCount > 0"
              class="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-400 ring-2 ring-bg-sidebar animate-pulse"
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

      <!-- 系统管理控制台 (仅系统管理员可见 · 预留导航分组插槽) -->
      <div v-if="authStore.isAdmin" class="pt-2 border-t border-border-subtle/70">
        <div
          v-if="!isCollapsed"
          class="px-2 pb-1 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 tracking-wider"
        >
          系统管理控制台
        </div>

        <nav class="space-y-1">
          <router-link
            to="/admin/settings"
            class="flex items-center rounded-xl p-2 text-xs transition-colors duration-150 cursor-pointer"
            :class="isCollapsed ? 'w-10 h-10 mx-auto justify-center' : 'space-x-2.5 px-2.5'"
            active-class="bg-slate-200/70 dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 font-semibold"
            :title="isCollapsed ? '模型与参数配置' : ''"
          >
            <SlidersHorizontal class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span v-if="!isCollapsed" class="text-text-secondary hover:text-text-main truncate">模型与参数配置</span>
          </router-link>

          <router-link
            to="/admin/tasks"
            class="flex items-center rounded-xl p-2 text-xs transition-colors duration-150 cursor-pointer"
            :class="isCollapsed ? 'w-10 h-10 mx-auto justify-center' : 'space-x-2.5 px-2.5'"
            active-class="bg-slate-200/70 dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 font-semibold"
            :title="isCollapsed ? '知识库运维与任务中心' : ''"
          >
            <ListTodo class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span v-if="!isCollapsed" class="text-text-secondary hover:text-text-main truncate">知识库运维与任务中心</span>
          </router-link>

          <router-link
            to="/admin/monitoring"
            class="flex items-center rounded-xl p-2 text-xs transition-colors duration-150 cursor-pointer"
            :class="isCollapsed ? 'w-10 h-10 mx-auto justify-center' : 'space-x-2.5 px-2.5'"
            active-class="bg-slate-200/70 dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 font-semibold"
            :title="isCollapsed ? '系统监控与 SLA 看板' : ''"
          >
            <Activity class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span v-if="!isCollapsed" class="text-text-secondary hover:text-text-main truncate">系统监控与 SLA 看板</span>
          </router-link>
        </nav>
      </div>
    </div>

    <!-- Bottom User Profile Footer -->
    <div
      ref="profileMenuRef"
      class="relative p-3 border-t border-border-subtle bg-slate-200/60 dark:bg-slate-950/70 flex"
      :class="isCollapsed ? 'flex-col items-center gap-2' : 'items-center justify-between'"
    >
      <!-- Upward Quick Role Switcher Menu -->
      <transition
        enter-active-class="transition ease-out duration-150"
        enter-from-class="opacity-0 translate-y-2 scale-95"
        enter-to-class="opacity-100 translate-y-0 scale-100"
        leave-active-class="transition ease-in duration-100"
        leave-from-class="opacity-100 translate-y-0 scale-100"
        leave-to-class="opacity-0 translate-y-2 scale-95"
      >
        <div
          v-if="showQuickSwitch"
          class="absolute bottom-16 left-2 right-2 rounded-2xl bg-bg-card border border-border-card shadow-2xl p-2 z-50 space-y-1.5"
        >
          <div class="px-2 py-0.5 text-[10px] font-semibold text-text-muted flex items-center justify-between">
            <span>切换当前工作身份</span>
            <ArrowLeftRight class="w-3 h-3 text-brand-primary" />
          </div>

          <button
            v-for="identity in authStore.demoIdentities"
            :key="identity.username"
            type="button"
            @click="handleRoleSwitch(identity.username)"
            class="w-full p-2 rounded-xl text-left text-xs flex items-center justify-between transition-colors cursor-pointer"
            :class="
              identity.username === authStore.currentUsername
                ? 'bg-brand-primary/10 text-text-main font-semibold border border-brand-primary/30'
                : 'text-text-secondary hover:text-text-main hover:bg-slate-100 dark:hover:bg-slate-800/80'
            "
          >
            <div class="truncate">
              <div class="truncate">{{ identity.display_name }} · {{ identity.role_label }}</div>
              <div class="text-[10px] text-text-muted truncate">{{ identity.department }}</div>
            </div>
            <Check v-if="identity.username === authStore.currentUsername" class="w-3.5 h-3.5 text-brand-primary shrink-0" />
          </button>

          <div class="pt-1 border-t border-border-subtle flex items-center gap-1.5">
            <button
              type="button"
              @click="goToLogin"
              class="flex-1 py-1.5 rounded-lg text-[11px] text-text-secondary hover:text-text-main hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
            >
              账号登录
            </button>
            <button
              type="button"
              @click="handleLogout"
              class="flex-1 py-1.5 rounded-lg text-[11px] text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 cursor-pointer"
            >
              退出登录
            </button>
          </div>
        </div>
      </transition>

      <!-- Expanded Profile -->
      <button
        v-if="!isCollapsed"
        type="button"
        @click.stop="toggleQuickSwitch"
        title="点击切换角色身份"
        class="flex items-center space-x-2.5 overflow-hidden text-left flex-1 rounded-xl p-1 -m-1 hover:bg-slate-300/40 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
      >
        <div
          class="w-8 h-8 rounded-full border flex items-center justify-center text-xs font-bold shrink-0"
          :class="avatarBadgeClass"
        >
          {{ authStore.avatarInitial }}
        </div>
        <div class="truncate flex-1">
          <div class="text-xs font-semibold text-text-main truncate">{{ authStore.displayName }}</div>
          <div class="text-[10px] text-text-muted truncate">
            {{ authStore.department }} · {{ authStore.roleLabel }}
          </div>
        </div>
      </button>

      <!-- Collapsed Profile Avatar -->
      <button
        v-else
        type="button"
        @click.stop="toggleQuickSwitch"
        class="w-full flex justify-center cursor-pointer"
        :title="`${authStore.displayName} (${authStore.department} · ${authStore.roleLabel})`"
      >
        <div
          class="w-8 h-8 rounded-full border flex items-center justify-center text-xs font-bold"
          :class="avatarBadgeClass"
        >
          {{ authStore.avatarInitial }}
        </div>
      </button>

      <div v-if="!isCollapsed" class="flex items-center space-x-0.5 shrink-0 ml-1">
        <button
          type="button"
          @click.stop="handleOpenSettings"
          :title="authStore.isAdmin ? '模型与节点配置中心 (管理员)' : '个人外观与显示偏好'"
          class="p-1.5 rounded-lg transition-colors duration-150 cursor-pointer"
          :class="
            authStore.isAdmin && route.path === '/admin/settings'
              ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
              : 'text-text-muted hover:text-text-main hover:bg-slate-300/50 dark:hover:bg-slate-800'
          "
        >
          <Settings class="w-4 h-4" />
        </button>

        <button
          type="button"
          @click.stop="toggleQuickSwitch"
          title="切换角色上下文"
          class="p-1.5 text-text-muted hover:text-text-main rounded-lg hover:bg-slate-300/50 dark:hover:bg-slate-800 transition-colors duration-150 cursor-pointer"
        >
          <ArrowLeftRight class="w-4 h-4" />
        </button>
      </div>

      <button
        v-else
        type="button"
        @click.stop="handleOpenSettings"
        :title="authStore.isAdmin ? '模型与节点配置中心 (管理员)' : '个人外观与显示偏好'"
        class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-150 cursor-pointer"
        :class="
          authStore.isAdmin && route.path === '/admin/settings'
            ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
            : 'text-text-muted hover:text-text-main hover:bg-slate-300/50 dark:hover:bg-slate-800'
        "
      >
        <Settings class="w-4 h-4" />
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import {
  MessageSquare,
  Plus,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  BookOpen,
  Sparkles,
  SlidersHorizontal,
  ListTodo,
  Activity,
  ArrowLeftRight,
  Check,
  Settings
} from 'lucide-vue-next';
import { useChatStore } from '../../stores/chatStore';
import { useApprovalStore } from '../../stores/approvalStore';
import { useAuthStore } from '../../stores/authStore';
import { usePreferencesStore } from '../../stores/preferencesStore';
import { useRouter, useRoute } from 'vue-router';
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
const authStore = useAuthStore();
const preferencesStore = usePreferencesStore();
const router = useRouter();
const route = useRoute();

const showQuickSwitch = ref(false);
const profileMenuRef = ref(null);

const pendingApprovalsCount = computed(() => {
  return approvalStore.pendingApprovals.length;
});

const avatarBadgeClass = computed(() => {
  if (authStore.currentRole === 'admin') {
    return 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30';
  }
  if (authStore.currentRole === 'manager') {
    return 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30';
  }
  return 'bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30';
});

const toggleQuickSwitch = () => {
  showQuickSwitch.value = !showQuickSwitch.value;
  if (showQuickSwitch.value) {
    authStore.fetchDemoIdentities();
  }
};

const handleRoleSwitch = async (username) => {
  showQuickSwitch.value = false;
  if (username === authStore.currentUsername) return;
  const res = await authStore.switchRole(username);
  if (res.success) {
    const allowedRoles = route.meta?.roles;
    if (Array.isArray(allowedRoles) && !allowedRoles.includes(authStore.currentRole)) {
      authStore.setPermissionNotice(
        `已切换为「${authStore.displayName} (${authStore.roleLabel})」，当前页面不在该角色权限范围内，已返回智能对话工作台。`
      );
      router.push('/');
    }
  }
};

const goToLogin = () => {
  showQuickSwitch.value = false;
  router.push('/login');
};

const handleLogout = () => {
  showQuickSwitch.value = false;
  authStore.logout(true);
  router.push('/login');
};

const handleOpenSettings = () => {
  showQuickSwitch.value = false;
  if (authStore.isAdmin) {
    router.push('/admin/settings');
  } else {
    preferencesStore.openPreferencesModal();
  }
};

const handleClickOutside = (event) => {
  if (showQuickSwitch.value && profileMenuRef.value && !profileMenuRef.value.contains(event.target)) {
    showQuickSwitch.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

const handleNewChat = async () => {
  await chatStore.createSession();
  emit('newSession');
  router.push('/');
};

const handleSelect = (id) => {
  chatStore.switchSession(id);
  emit('selectSession', id);
  router.push('/');
};
</script>
