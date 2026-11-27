<template>
  <aside
    class="h-full flex flex-col justify-between shrink-0 select-none overflow-hidden relative bg-bg-sidebar border-r border-border-subtle transition-[width] duration-200 ease-snappy z-20"
    :class="isCollapsed ? 'w-16' : 'w-64'"
  >
    <!-- Top Brand & Collapse Toggle -->
    <div class="h-14 px-3 flex items-center justify-between border-b border-border-subtle shrink-0">
      <div v-if="!isCollapsed" class="flex items-center gap-2.5 overflow-hidden">
        <div class="w-7 h-7 rounded-lg bg-action-primary text-action-primary-fg flex items-center justify-center shrink-0">
          <Bot class="w-4 h-4" />
        </div>
        <div class="truncate">
          <h2 class="text-sm font-semibold text-text-main leading-tight truncate">企业数字员工</h2>
        </div>
      </div>

      <div v-else class="w-full flex justify-center">
        <div class="w-7 h-7 rounded-lg bg-action-primary text-action-primary-fg flex items-center justify-center">
          <Bot class="w-4 h-4" />
        </div>
      </div>

      <button
        v-if="!isCollapsed"
        type="button"
        @click="$emit('update:isCollapsed', true)"
        title="收起侧边栏"
        class="btn-pressable p-1.5 rounded-lg text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer"
      >
        <ChevronLeft class="w-4 h-4" />
      </button>
    </div>

    <!-- Primary Action: New Chat -->
    <div class="p-3 shrink-0">
      <button
        v-if="!isCollapsed"
        type="button"
        @click="handleNewChat"
        class="btn-primary w-full h-9 px-3 rounded-lg flex items-center justify-center gap-1.5 text-xs font-medium cursor-pointer"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>新建对话</span>
      </button>

      <button
        v-else
        type="button"
        @click="handleNewChat"
        title="新建对话"
        class="btn-primary w-9 h-9 mx-auto rounded-lg flex items-center justify-center cursor-pointer"
      >
        <Plus class="w-4 h-4" />
      </button>
    </div>

    <!-- Middle: Sessions History -->
    <div v-if="!isCollapsed" class="flex-1 overflow-y-auto px-2.5 pb-4 space-y-5">
      <div v-if="chatStore.todaySessions.length > 0" class="space-y-1">
        <div class="px-2 py-0.5 text-[11px] font-medium text-text-muted">今天</div>
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

      <div v-if="chatStore.yesterdaySessions.length > 0" class="space-y-1">
        <div class="px-2 py-0.5 text-[11px] font-medium text-text-muted">昨天</div>
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

      <div v-if="chatStore.previous7DaysSessions.length > 0" class="space-y-1">
        <div class="px-2 py-0.5 text-[11px] font-medium text-text-muted">前 7 天</div>
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

      <div v-if="chatStore.olderSessions.length > 0" class="space-y-1">
        <div class="px-2 py-0.5 text-[11px] font-medium text-text-muted">更早</div>
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

      <div
        v-if="
          chatStore.todaySessions.length === 0 &&
          chatStore.yesterdaySessions.length === 0 &&
          chatStore.previous7DaysSessions.length === 0 &&
          chatStore.olderSessions.length === 0 &&
          chatStore.sessions.length > 0
        "
        class="space-y-1"
      >
        <div class="px-2 py-0.5 text-[11px] font-medium text-text-muted">全部对话</div>
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

    <!-- Middle: Collapsed Controls -->
    <div v-else class="flex-1 flex flex-col items-center py-3 gap-2 overflow-y-auto">
      <button
        type="button"
        @click="$emit('update:isCollapsed', false)"
        title="展开侧边栏"
        class="btn-pressable w-9 h-9 rounded-lg text-text-secondary hover:text-text-main hover:bg-bg-hover flex items-center justify-center cursor-pointer"
      >
        <ChevronRight class="w-4 h-4" />
      </button>

      <div class="w-7 border-t border-border-subtle my-1"></div>

      <button
        v-for="s in chatStore.sessions.slice(0, 5)"
        :key="s.id"
        type="button"
        @click="handleSelect(s.id)"
        :title="s.title"
        class="btn-pressable w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer"
        :class="
          s.id === chatStore.activeSessionId
            ? 'bg-bg-card border border-border-card text-text-main'
            : 'text-text-muted hover:text-text-main hover:bg-bg-hover'
        "
      >
        <MessageSquare class="w-4 h-4" />
      </button>
    </div>

    <!-- Lower: Business Workspaces Navigation -->
    <div class="p-2.5 border-t border-border-subtle space-y-4">
      <div class="space-y-1">
        <div v-if="!isCollapsed" class="px-2 py-0.5 text-[11px] font-medium text-text-muted">
          业务协同
        </div>

        <nav class="space-y-0.5">
          <router-link
            v-if="authStore.canApprove"
            to="/approvals"
            class="relative flex items-center rounded-lg h-9 text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
            :class="isCollapsed ? 'w-9 mx-auto justify-center' : 'justify-between px-2.5'"
            active-class="bg-bg-card border border-border-card text-text-main font-semibold"
            :title="isCollapsed ? `待我审批 (${pendingApprovalsCount})` : ''"
          >
            <div class="flex items-center gap-2.5 truncate">
              <ClipboardList class="w-4 h-4 shrink-0" />
              <span v-if="!isCollapsed" class="truncate">待我审批</span>
            </div>
            <span
              v-if="!isCollapsed && pendingApprovalsCount > 0"
              class="px-1.5 py-0.5 text-[10px] font-mono font-medium rounded-md bg-bg-surface text-text-main border border-border-card"
            >
              {{ pendingApprovalsCount }}
            </span>
            <span
              v-else-if="isCollapsed && pendingApprovalsCount > 0"
              class="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-status-approval"
            ></span>
          </router-link>

          <router-link
            to="/knowledge"
            class="flex items-center rounded-lg h-9 text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
            :class="isCollapsed ? 'w-9 mx-auto justify-center' : 'gap-2.5 px-2.5'"
            active-class="bg-bg-card border border-border-card text-text-main font-semibold"
            :title="isCollapsed ? '规章制度知识库' : ''"
          >
            <BookOpen class="w-4 h-4 shrink-0" />
            <span v-if="!isCollapsed" class="truncate">规章制度知识库</span>
          </router-link>
        </nav>
      </div>

      <!-- Admin Console Navigation (Admin Role Only) -->
      <div v-if="authStore.isAdmin" class="pt-3 border-t border-border-subtle space-y-1">
        <div v-if="!isCollapsed" class="px-2 py-0.5 text-[11px] font-medium text-text-muted">
          系统管理
        </div>

        <nav class="space-y-0.5">
          <router-link
            to="/admin/settings"
            class="flex items-center rounded-lg h-9 text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
            :class="isCollapsed ? 'w-9 mx-auto justify-center' : 'gap-2.5 px-2.5'"
            active-class="bg-bg-card border border-border-card text-text-main font-semibold"
            :title="isCollapsed ? '模型与参数配置' : ''"
          >
            <SlidersHorizontal class="w-4 h-4 shrink-0" />
            <span v-if="!isCollapsed" class="truncate">模型与参数配置</span>
          </router-link>

          <router-link
            to="/admin/tasks"
            class="flex items-center rounded-lg h-9 text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
            :class="isCollapsed ? 'w-9 mx-auto justify-center' : 'gap-2.5 px-2.5'"
            active-class="bg-bg-card border border-border-card text-text-main font-semibold"
            :title="isCollapsed ? '知识库运维与任务中心' : ''"
          >
            <ListTodo class="w-4 h-4 shrink-0" />
            <span v-if="!isCollapsed" class="truncate">知识库任务中心</span>
          </router-link>

          <router-link
            to="/admin/monitoring"
            class="flex items-center rounded-lg h-9 text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
            :class="isCollapsed ? 'w-9 mx-auto justify-center' : 'gap-2.5 px-2.5'"
            active-class="bg-bg-card border border-border-card text-text-main font-semibold"
            :title="isCollapsed ? '系统监控与 SLA 看板' : ''"
          >
            <Activity class="w-4 h-4 shrink-0" />
            <span v-if="!isCollapsed" class="truncate">系统监控看板</span>
          </router-link>
        </nav>
      </div>
    </div>

    <!-- Bottom User Profile Footer -->
    <div
      ref="profileMenuRef"
      class="relative p-2.5 border-t border-border-subtle flex"
      :class="isCollapsed ? 'flex-col items-center gap-2' : 'items-center justify-between'"
    >
      <transition name="popover-up">
        <div
          v-if="showQuickSwitch"
          class="origin-bottom-left absolute bottom-14 left-2.5 right-2.5 rounded-xl bg-bg-card border border-border-card shadow-sm p-1.5 z-50 space-y-1"
        >
          <div class="px-2 py-1 text-[11px] font-medium text-text-muted flex items-center justify-between">
            <span>切换身份</span>
            <ArrowLeftRight class="w-3 h-3" />
          </div>

          <button
            v-for="identity in authStore.demoIdentities"
            :key="identity.username"
            type="button"
            @click="handleRoleSwitch(identity.username)"
            class="w-full px-2 py-1.5 rounded-lg text-left text-xs flex items-center justify-between transition-colors duration-150 cursor-pointer"
            :class="
              identity.username === authStore.currentUsername
                ? 'bg-bg-surface text-text-main font-semibold'
                : 'text-text-secondary hover:text-text-main hover:bg-bg-hover'
            "
          >
            <div class="truncate">
              <div class="truncate">{{ identity.display_name }} · {{ identity.role_label }}</div>
              <div class="text-[10px] text-text-muted truncate">{{ identity.department }}</div>
            </div>
            <Check v-if="identity.username === authStore.currentUsername" class="w-3.5 h-3.5 text-text-main shrink-0" />
          </button>

          <div class="pt-1 border-t border-border-subtle flex items-center gap-1">
            <button
              type="button"
              @click="goToLogin"
              class="btn-pressable flex-1 py-1.5 rounded-lg text-[11px] text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer"
            >
              账号登录
            </button>
            <button
              type="button"
              @click="handleLogout"
              class="btn-pressable flex-1 py-1.5 rounded-lg text-[11px] text-status-danger hover:bg-bg-hover cursor-pointer"
            >
              退出登录
            </button>
          </div>
        </div>
      </transition>

      <button
        v-if="!isCollapsed"
        type="button"
        @click.stop="toggleQuickSwitch"
        title="切换角色身份"
        class="flex items-center gap-2.5 overflow-hidden text-left flex-1 rounded-lg p-1.5 -m-1 hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
      >
        <div class="w-8 h-8 rounded-full border border-border-card bg-bg-card text-text-main flex items-center justify-center text-xs font-semibold shrink-0">
          {{ authStore.avatarInitial }}
        </div>
        <div class="truncate flex-1">
          <div class="text-xs font-semibold text-text-main truncate">{{ authStore.displayName }}</div>
          <div class="text-[11px] text-text-muted truncate">
            {{ authStore.department }} · {{ authStore.roleLabel }}
          </div>
        </div>
      </button>

      <button
        v-else
        type="button"
        @click.stop="toggleQuickSwitch"
        class="w-full flex justify-center cursor-pointer"
        :title="`${authStore.displayName} (${authStore.department} · ${authStore.roleLabel})`"
      >
        <div class="w-8 h-8 rounded-full border border-border-card bg-bg-card text-text-main flex items-center justify-center text-xs font-semibold">
          {{ authStore.avatarInitial }}
        </div>
      </button>

      <div v-if="!isCollapsed" class="flex items-center gap-0.5 shrink-0 ml-1">
        <button
          type="button"
          @click.stop="handleOpenSettings"
          :title="authStore.isAdmin ? '模型与参数配置' : '显示偏好'"
          class="btn-pressable p-1.5 rounded-lg cursor-pointer"
          :class="
            authStore.isAdmin && route.path === '/admin/settings'
              ? 'bg-bg-card border border-border-card text-text-main'
              : 'text-text-muted hover:text-text-main hover:bg-bg-hover'
          "
        >
          <Settings class="w-4 h-4" />
        </button>

        <button
          type="button"
          @click.stop="toggleQuickSwitch"
          title="切换身份"
          class="btn-pressable p-1.5 text-text-muted hover:text-text-main rounded-lg hover:bg-bg-hover cursor-pointer"
        >
          <ArrowLeftRight class="w-4 h-4" />
        </button>
      </div>

      <button
        v-else
        type="button"
        @click.stop="handleOpenSettings"
        :title="authStore.isAdmin ? '模型与参数配置' : '显示偏好'"
        class="btn-pressable w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer"
        :class="
          authStore.isAdmin && route.path === '/admin/settings'
            ? 'bg-bg-card border border-border-card text-text-main'
            : 'text-text-muted hover:text-text-main hover:bg-bg-hover'
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
  Bot,
  MessageSquare,
  Plus,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  BookOpen,
  SlidersHorizontal,
  ListTodo,
  Activity,
  ArrowLeftRight,
  Check,
  Settings,
} from 'lucide-vue-next';
import { useChatStore } from '../../stores/chatStore';
import { useApprovalStore } from '../../stores/approvalStore';
import { useAuthStore } from '../../stores/authStore';
import { usePreferencesStore } from '../../stores/preferencesStore';
import { useRouter, useRoute } from 'vue-router';
import LineSidebar from '../ui/LineSidebar.vue';

defineProps({
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

const pendingApprovalsCount = computed(() => approvalStore.pendingApprovals.length);

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
        `已切换为「${authStore.displayName} (${authStore.roleLabel})」，当前页面不在该角色权限范围内，已返回对话工作台。`
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

const handleKeydown = (event) => {
  if (event.key === 'Escape' && showQuickSwitch.value) {
    showQuickSwitch.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
  document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
  document.removeEventListener('keydown', handleKeydown);
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
