<template>
  <teleport to="body">
    <div
      v-show="modelValue || isAnimating"
      class="fixed inset-0 z-50 select-none overflow-hidden"
    >
      <!-- Backdrop -->
      <transition
        name="modal-backdrop"
        @before-enter="isAnimating = true"
        @after-leave="isAnimating = false"
      >
        <div
          v-if="modelValue"
          @click="closeDrawer"
          class="fixed inset-0 bg-black/55"
          aria-hidden="true"
        ></div>
      </transition>

      <!-- Off-Canvas Drawer Panel (--ease-drawer) -->
      <transition name="drawer">
        <aside
          v-if="modelValue"
          class="fixed inset-y-0 left-0 w-72 max-w-[85vw] bg-bg-sidebar border-r border-border-card flex flex-col justify-between z-10"
          style="padding-bottom: env(safe-area-inset-bottom, 12px); padding-top: env(safe-area-inset-top, 0px);"
        >
          <!-- Top Header -->
          <div class="h-14 px-3.5 flex items-center justify-between border-b border-border-subtle shrink-0">
            <div class="flex items-center gap-2.5 overflow-hidden">
              <div class="w-7 h-7 rounded-lg bg-action-primary text-action-primary-fg flex items-center justify-center shrink-0">
                <Bot class="w-4 h-4" />
              </div>
              <h2 class="text-sm font-semibold text-text-main leading-tight truncate">企业数字员工</h2>
            </div>

            <button
              type="button"
              @click="closeDrawer"
              title="关闭导航"
              class="btn-pressable w-10 h-10 -mr-1.5 rounded-lg flex items-center justify-center text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- New Chat Primary CTA -->
          <div class="p-3 shrink-0">
            <button
              type="button"
              @click="handleNewChat"
              class="btn-primary w-full h-10 px-3.5 rounded-lg flex items-center justify-center gap-1.5 text-xs font-medium cursor-pointer"
            >
              <Plus class="w-4 h-4" />
              <span>新建对话</span>
            </button>
          </div>

          <!-- Scrollable Session History -->
          <div class="flex-1 overflow-y-auto px-2.5 pb-3 space-y-5 overscroll-contain">
            <template v-for="group in sessionGroups" :key="group.label">
              <div v-if="group.items.length > 0" class="space-y-1">
                <div class="px-2 py-0.5 text-[11px] font-medium text-text-muted">{{ group.label }}</div>
                <div class="space-y-0.5">
                  <div
                    v-for="s in group.items"
                    :key="s.id"
                    @click="handleSelect(s.id)"
                    class="group px-3 py-2 min-h-[40px] rounded-lg text-xs flex items-center justify-between cursor-pointer transition-colors duration-150"
                    :class="
                      s.id === chatStore.activeSessionId
                        ? 'bg-bg-card border border-border-card text-text-main font-semibold'
                        : 'text-text-secondary hover:text-text-main hover:bg-bg-hover'
                    "
                  >
                    <div class="flex items-center gap-2.5 truncate">
                      <MessageSquare class="w-3.5 h-3.5 shrink-0 opacity-70" />
                      <span class="truncate">{{ s.title }}</span>
                    </div>
                    <button
                      type="button"
                      @click.stop="chatStore.deleteSession(s.id)"
                      title="删除会话"
                      class="p-1.5 text-text-muted hover:text-status-danger rounded-md transition-colors duration-150"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- Workspace Navigation -->
          <div class="p-3 border-t border-border-subtle shrink-0 space-y-4">
            <div class="space-y-1">
              <div class="px-1 text-[11px] font-medium text-text-muted">业务协同</div>

              <nav class="space-y-0.5">
                <router-link
                  v-if="authStore.canApprove"
                  to="/approvals"
                  @click="closeDrawer"
                  class="flex items-center justify-between px-2.5 h-10 rounded-lg text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
                  active-class="bg-bg-card border border-border-card text-text-main font-semibold"
                >
                  <div class="flex items-center gap-2.5 truncate">
                    <ClipboardList class="w-4 h-4 shrink-0" />
                    <span class="truncate">待我审批</span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <span
                      v-if="pendingApprovalsCount > 0"
                      class="px-1.5 py-0.5 text-[10px] font-mono rounded-md bg-bg-surface text-text-main border border-border-card"
                    >
                      {{ pendingApprovalsCount }}
                    </span>
                    <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                  </div>
                </router-link>

                <router-link
                  to="/knowledge"
                  @click="closeDrawer"
                  class="flex items-center justify-between px-2.5 h-10 rounded-lg text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
                  active-class="bg-bg-card border border-border-card text-text-main font-semibold"
                >
                  <div class="flex items-center gap-2.5 truncate">
                    <BookOpen class="w-4 h-4 shrink-0" />
                    <span class="truncate">规章制度知识库</span>
                  </div>
                  <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                </router-link>
              </nav>
            </div>

            <!-- Admin Console -->
            <div v-if="authStore.isAdmin" class="pt-3 border-t border-border-subtle space-y-1">
              <div class="px-1 text-[11px] font-medium text-text-muted">系统管理</div>

              <nav class="space-y-0.5">
                <router-link
                  to="/admin/settings"
                  @click="closeDrawer"
                  class="flex items-center justify-between px-2.5 h-9 rounded-lg text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
                  active-class="bg-bg-card border border-border-card text-text-main font-semibold"
                >
                  <div class="flex items-center gap-2.5 truncate">
                    <SlidersHorizontal class="w-4 h-4 shrink-0" />
                    <span class="truncate">模型与参数配置</span>
                  </div>
                  <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                </router-link>

                <router-link
                  to="/admin/tasks"
                  @click="closeDrawer"
                  class="flex items-center justify-between px-2.5 h-9 rounded-lg text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
                  active-class="bg-bg-card border border-border-card text-text-main font-semibold"
                >
                  <div class="flex items-center gap-2.5 truncate">
                    <ListTodo class="w-4 h-4 shrink-0" />
                    <span class="truncate">知识库任务中心</span>
                  </div>
                  <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                </router-link>

                <router-link
                  to="/admin/monitoring"
                  @click="closeDrawer"
                  class="flex items-center justify-between px-2.5 h-9 rounded-lg text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
                  active-class="bg-bg-card border border-border-card text-text-main font-semibold"
                >
                  <div class="flex items-center gap-2.5 truncate">
                    <Activity class="w-4 h-4 shrink-0" />
                    <span class="truncate">系统监控看板</span>
                  </div>
                  <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                </router-link>
              </nav>
            </div>
          </div>

          <!-- Bottom Profile & Role Switch -->
          <div class="p-3 border-t border-border-subtle space-y-2.5 shrink-0">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5 overflow-hidden">
                <div class="w-8 h-8 rounded-full border border-border-card bg-bg-card text-text-main flex items-center justify-center text-xs font-semibold shrink-0">
                  {{ authStore.avatarInitial }}
                </div>
                <div class="truncate">
                  <div class="text-xs font-semibold text-text-main truncate">{{ authStore.displayName }}</div>
                  <div class="text-[11px] text-text-muted truncate">
                    {{ authStore.department }} · {{ authStore.roleLabel }}
                  </div>
                </div>
              </div>

              <div class="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  @click="handleOpenSettings"
                  :title="authStore.isAdmin ? '模型与参数配置' : '显示偏好'"
                  class="btn-pressable w-8 h-8 rounded-lg flex items-center justify-center text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer"
                >
                  <Settings class="w-4 h-4" />
                </button>

                <button
                  type="button"
                  @click="handleLogout"
                  title="退出登录"
                  class="btn-pressable w-8 h-8 rounded-lg flex items-center justify-center text-status-danger hover:bg-bg-hover cursor-pointer"
                >
                  <LogOut class="w-4 h-4" />
                </button>
              </div>
            </div>

            <div class="grid grid-cols-3 gap-1.5">
              <button
                v-for="identity in authStore.demoIdentities"
                :key="identity.username"
                type="button"
                @click="handleRoleSwitch(identity.username)"
                class="btn-pressable py-1.5 px-1.5 rounded-lg text-[11px] font-medium text-center border cursor-pointer truncate"
                :class="
                  identity.username === authStore.currentUsername
                    ? 'bg-action-primary border-action-primary text-action-primary-fg'
                    : 'bg-bg-card border-border-card text-text-secondary hover:text-text-main'
                "
              >
                {{ identity.role_label }}
              </button>
            </div>
          </div>
        </aside>
      </transition>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import {
  Bot,
  X,
  Plus,
  MessageSquare,
  ClipboardList,
  BookOpen,
  Trash2,
  ChevronRight,
  SlidersHorizontal,
  ListTodo,
  Activity,
  LogOut,
  Settings,
} from 'lucide-vue-next';
import { useChatStore } from '../../stores/chatStore';
import { useApprovalStore } from '../../stores/approvalStore';
import { useAuthStore } from '../../stores/authStore';
import { usePreferencesStore } from '../../stores/preferencesStore';
import { useRouter, useRoute } from 'vue-router';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['update:modelValue', 'newSession', 'selectSession']);

const chatStore = useChatStore();
const approvalStore = useApprovalStore();
const authStore = useAuthStore();
const preferencesStore = usePreferencesStore();
const router = useRouter();
const route = useRoute();

const isAnimating = ref(false);

const pendingApprovalsCount = computed(() => approvalStore.pendingApprovals.length);

const sessionGroups = computed(() => {
  const groups = [
    { label: '今天', items: chatStore.todaySessions },
    { label: '昨天', items: chatStore.yesterdaySessions },
    { label: '前 7 天', items: chatStore.previous7DaysSessions },
    { label: '更早', items: chatStore.olderSessions },
  ];
  const hasGrouped = groups.some((g) => g.items.length > 0);
  if (!hasGrouped && chatStore.sessions.length > 0) {
    return [{ label: '全部对话', items: chatStore.sessions }];
  }
  return groups;
});

const closeDrawer = () => {
  emit('update:modelValue', false);
};

const handleRoleSwitch = async (username) => {
  if (username === authStore.currentUsername) return;
  const res = await authStore.switchRole(username);
  if (res.success) {
    const allowedRoles = route.meta?.roles;
    if (Array.isArray(allowedRoles) && !allowedRoles.includes(authStore.currentRole)) {
      authStore.setPermissionNotice(
        `已切换为「${authStore.displayName} (${authStore.roleLabel})」，当前页面不在该角色权限范围内，已返回对话工作台。`
      );
      closeDrawer();
      router.push('/');
    }
  }
};

const handleLogout = () => {
  closeDrawer();
  authStore.logout(true);
  router.push('/login');
};

const handleOpenSettings = () => {
  closeDrawer();
  if (authStore.isAdmin) {
    router.push('/admin/settings');
  } else {
    preferencesStore.openPreferencesModal();
  }
};

const handleNewChat = async () => {
  await chatStore.createSession();
  emit('newSession');
  closeDrawer();
  router.push('/');
};

const handleSelect = (id) => {
  chatStore.switchSession(id);
  emit('selectSession', id);
  closeDrawer();
  router.push('/');
};

const handleKeydown = (e) => {
  if (e.key === 'Escape' && props.modelValue) {
    closeDrawer();
  }
};

watch(
  () => props.modelValue,
  (isOpen) => {
    if (typeof document !== 'undefined') {
      document.body.style.overflow = isOpen ? 'hidden' : '';
    }
  }
);

onMounted(() => {
  document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
  if (typeof document !== 'undefined') {
    document.body.style.overflow = '';
  }
});
</script>
