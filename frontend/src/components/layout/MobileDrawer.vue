<template>
  <teleport to="body">
    <!-- Backdrop & Off-Canvas Drawer Root -->
    <div
      v-show="modelValue || isAnimating"
      class="fixed inset-0 z-50 select-none overflow-hidden"
    >
      <!-- Dark Frosted Backdrop -->
      <transition
        enter-active-class="transition-opacity duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-200 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
        @before-enter="isAnimating = true"
        @after-leave="isAnimating = false"
      >
        <div
          v-if="modelValue"
          @click="closeDrawer"
          class="fixed inset-0 bg-black/70 backdrop-blur-sm"
          aria-hidden="true"
        ></div>
      </transition>

      <!-- Off-Canvas Drawer Panel -->
      <transition
        enter-active-class="transition-transform duration-200 ease-out"
        enter-from-class="-translate-x-full"
        enter-to-class="translate-x-0"
        leave-active-class="transition-transform duration-200 ease-in"
        leave-from-class="translate-x-0"
        leave-to-class="-translate-x-full"
      >
        <aside
          v-if="modelValue"
          class="fixed inset-y-0 left-0 w-72 max-w-[85vw] bg-bg-sidebar border-r border-border-card shadow-2xl flex flex-col justify-between z-10"
          style="padding-bottom: env(safe-area-inset-bottom, 12px); padding-top: env(safe-area-inset-top, 0px);"
        >
          <!-- Top Header: Brand & Close Button -->
          <div class="p-3.5 flex items-center justify-between border-b border-border-subtle/80 shrink-0">
            <div class="flex items-center space-x-2.5 overflow-hidden">
              <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center shadow-md shadow-blue-500/20 shrink-0">
                <Sparkles class="w-4 h-4 text-white" />
              </div>
              <div class="truncate">
                <h2 class="text-sm font-bold text-text-main leading-tight truncate">企业数字员工</h2>
                <p class="text-[10px] text-text-muted leading-tight">AI Copilot 移动端</p>
              </div>
            </div>

            <!-- Close Drawer Button (44x44px touch target) -->
            <button
              @click="closeDrawer"
              title="关闭导航抽屉"
              class="w-11 h-11 -mr-2 rounded-xl flex items-center justify-center text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-800/80 transition-colors duration-150 cursor-pointer"
            >
              <X class="w-5 h-5" />
            </button>
          </div>

          <!-- [+ 新建对话] Action Section -->
          <div class="p-3 shrink-0">
            <button
              @click="handleNewChat"
              class="w-full h-11 px-3.5 rounded-xl bg-brand-primary/10 hover:bg-brand-primary/20 text-brand-primary border border-brand-primary/30 flex items-center justify-center space-x-2 text-xs font-semibold shadow-sm transition-all duration-150 cursor-pointer group active:scale-[0.98]"
            >
              <Plus class="w-4 h-4 transition-transform duration-150 group-hover:rotate-90" />
              <span>新建对话</span>
            </button>
          </div>

          <!-- Middle: Scrollable Sessions History List -->
          <div class="flex-1 overflow-y-auto px-2.5 py-1 space-y-3 overscroll-contain">
            <!-- Group: 今天 -->
            <div v-if="chatStore.todaySessions.length > 0">
              <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">今天</div>
              <div class="space-y-1">
                <div
                  v-for="s in chatStore.todaySessions"
                  :key="s.id"
                  @click="handleSelect(s.id)"
                  class="group px-3 py-2.5 min-h-[44px] rounded-xl text-xs flex items-center justify-between cursor-pointer transition-colors duration-150"
                  :class="s.id === chatStore.activeSessionId ? 'bg-slate-200 dark:bg-slate-800 text-text-main font-semibold border border-border-card shadow-sm' : 'text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-900/60'"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <MessageSquare class="w-4 h-4 shrink-0 text-brand-primary/80" />
                    <span class="truncate">{{ s.title }}</span>
                  </div>
                  <button
                    @click.stop="chatStore.deleteSession(s.id)"
                    title="删除会话"
                    class="p-2 text-text-muted hover:text-status-danger rounded transition-colors duration-150"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Group: 昨天 -->
            <div v-if="chatStore.yesterdaySessions.length > 0">
              <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">昨天</div>
              <div class="space-y-1">
                <div
                  v-for="s in chatStore.yesterdaySessions"
                  :key="s.id"
                  @click="handleSelect(s.id)"
                  class="group px-3 py-2.5 min-h-[44px] rounded-xl text-xs flex items-center justify-between cursor-pointer transition-colors duration-150"
                  :class="s.id === chatStore.activeSessionId ? 'bg-slate-200 dark:bg-slate-800 text-text-main font-semibold border border-border-card shadow-sm' : 'text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-900/60'"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <MessageSquare class="w-4 h-4 shrink-0 text-brand-primary/80" />
                    <span class="truncate">{{ s.title }}</span>
                  </div>
                  <button
                    @click.stop="chatStore.deleteSession(s.id)"
                    title="删除会话"
                    class="p-2 text-text-muted hover:text-status-danger rounded transition-colors duration-150"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Group: 前 7 天 -->
            <div v-if="chatStore.previous7DaysSessions.length > 0">
              <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">前 7 天</div>
              <div class="space-y-1">
                <div
                  v-for="s in chatStore.previous7DaysSessions"
                  :key="s.id"
                  @click="handleSelect(s.id)"
                  class="group px-3 py-2.5 min-h-[44px] rounded-xl text-xs flex items-center justify-between cursor-pointer transition-colors duration-150"
                  :class="s.id === chatStore.activeSessionId ? 'bg-slate-200 dark:bg-slate-800 text-text-main font-semibold border border-border-card shadow-sm' : 'text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-900/60'"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <MessageSquare class="w-4 h-4 shrink-0 text-brand-primary/80" />
                    <span class="truncate">{{ s.title }}</span>
                  </div>
                  <button
                    @click.stop="chatStore.deleteSession(s.id)"
                    title="删除会话"
                    class="p-2 text-text-muted hover:text-status-danger rounded transition-colors duration-150"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Group: 更早历史 -->
            <div v-if="chatStore.olderSessions.length > 0">
              <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">更早</div>
              <div class="space-y-1">
                <div
                  v-for="s in chatStore.olderSessions"
                  :key="s.id"
                  @click="handleSelect(s.id)"
                  class="group px-3 py-2.5 min-h-[44px] rounded-xl text-xs flex items-center justify-between cursor-pointer transition-colors duration-150"
                  :class="s.id === chatStore.activeSessionId ? 'bg-slate-200 dark:bg-slate-800 text-text-main font-semibold border border-border-card shadow-sm' : 'text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-900/60'"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <MessageSquare class="w-4 h-4 shrink-0 text-brand-primary/80" />
                    <span class="truncate">{{ s.title }}</span>
                  </div>
                  <button
                    @click.stop="chatStore.deleteSession(s.id)"
                    title="删除会话"
                    class="p-2 text-text-muted hover:text-status-danger rounded transition-colors duration-150"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Fallback: 完整保底列出未分组的历史会话 -->
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
              <div class="space-y-1">
                <div
                  v-for="s in chatStore.sessions"
                  :key="s.id"
                  @click="handleSelect(s.id)"
                  class="group px-3 py-2.5 min-h-[44px] rounded-xl text-xs flex items-center justify-between cursor-pointer transition-colors duration-150"
                  :class="s.id === chatStore.activeSessionId ? 'bg-slate-200 dark:bg-slate-800 text-text-main font-semibold border border-border-card shadow-sm' : 'text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-900/60'"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <MessageSquare class="w-4 h-4 shrink-0 text-brand-primary/80" />
                    <span class="truncate">{{ s.title }}</span>
                  </div>
                  <button
                    @click.stop="chatStore.deleteSession(s.id)"
                    title="删除会话"
                    class="p-2 text-text-muted hover:text-status-danger rounded transition-colors duration-150"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Lower: Business Workspaces Navigation -->
          <div class="p-3 border-t border-border-subtle bg-slate-200/50 dark:bg-slate-950/60 shrink-0 space-y-3">
            <div>
              <div class="px-1 pb-1.5 text-[11px] font-semibold text-text-muted tracking-wider">
                企业业务协同
              </div>

              <nav class="space-y-1.5">
                <!-- 待我审批入口 (仅部门主管与系统管理员可见) -->
                <router-link
                  v-if="authStore.canApprove"
                  to="/approvals"
                  @click="closeDrawer"
                  class="flex items-center justify-between p-2.5 min-h-[44px] rounded-xl text-xs transition-colors duration-150 cursor-pointer active:bg-slate-200 dark:active:bg-slate-800"
                  active-class="bg-slate-200 dark:bg-slate-800 text-status-approval font-semibold"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <ClipboardList class="w-4 h-4 text-status-approval shrink-0" />
                    <span class="text-text-secondary hover:text-text-main truncate">待我审批中心</span>
                  </div>
                  <div class="flex items-center space-x-1.5">
                    <span
                      v-if="pendingApprovalsCount > 0"
                      class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-status-approval border border-amber-500/30 font-mono"
                    >
                      {{ pendingApprovalsCount }} 项
                    </span>
                    <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                  </div>
                </router-link>

                <!-- 规章制度知识库入口 -->
                <router-link
                  to="/knowledge"
                  @click="closeDrawer"
                  class="flex items-center justify-between p-2.5 min-h-[44px] rounded-xl text-xs transition-colors duration-150 cursor-pointer active:bg-slate-200 dark:active:bg-slate-800"
                  active-class="bg-slate-200 dark:bg-slate-800 text-brand-primary font-semibold"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <BookOpen class="w-4 h-4 text-brand-primary shrink-0" />
                    <span class="text-text-secondary hover:text-text-main truncate">规章制度知识库</span>
                  </div>
                  <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                </router-link>
              </nav>
            </div>

            <!-- 系统管理控制台 (仅系统管理员可见 · 预留导航分组插槽) -->
            <div v-if="authStore.isAdmin" class="pt-2 border-t border-border-subtle/70">
              <div class="px-1 pb-1.5 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 tracking-wider">
                系统管理控制台
              </div>

              <nav class="space-y-1">
                <router-link
                  to="/admin/settings"
                  @click="closeDrawer"
                  class="flex items-center justify-between p-2.5 min-h-[42px] rounded-xl text-xs transition-colors duration-150 cursor-pointer"
                  active-class="bg-slate-200 dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 font-semibold"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <SlidersHorizontal class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span class="text-text-secondary hover:text-text-main truncate">模型与参数配置</span>
                  </div>
                  <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                </router-link>

                <router-link
                  to="/admin/tasks"
                  @click="closeDrawer"
                  class="flex items-center justify-between p-2.5 min-h-[42px] rounded-xl text-xs transition-colors duration-150 cursor-pointer"
                  active-class="bg-slate-200 dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 font-semibold"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <ListTodo class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span class="text-text-secondary hover:text-text-main truncate">知识库运维与任务中心</span>
                  </div>
                  <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                </router-link>

                <router-link
                  to="/admin/monitoring"
                  @click="closeDrawer"
                  class="flex items-center justify-between p-2.5 min-h-[42px] rounded-xl text-xs transition-colors duration-150 cursor-pointer"
                  active-class="bg-slate-200 dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 font-semibold"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <Activity class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span class="text-text-secondary hover:text-text-main truncate">运行遥测监控</span>
                  </div>
                  <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                </router-link>
              </nav>
            </div>
          </div>

          <!-- Bottom: User Profile & Quick Role Switcher -->
          <div class="p-3 border-t border-border-subtle bg-slate-200/60 dark:bg-slate-950/80 space-y-2.5 shrink-0">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2.5 overflow-hidden">
                <div
                  class="w-9 h-9 rounded-full border flex items-center justify-center text-xs font-bold shrink-0"
                  :class="avatarBadgeClass"
                >
                  {{ authStore.avatarInitial }}
                </div>
                <div class="truncate">
                  <div class="text-xs font-semibold text-text-main truncate">{{ authStore.displayName }}</div>
                  <div class="text-[10px] text-text-muted truncate">
                    {{ authStore.department }} · {{ authStore.roleLabel }}
                  </div>
                </div>
              </div>

              <div class="flex items-center space-x-1 shrink-0">
                <button
                  type="button"
                  @click="handleOpenSettings"
                  :title="authStore.isAdmin ? '模型与节点配置中心 (管理员)' : '个人外观与显示偏好'"
                  class="w-9 h-9 rounded-xl flex items-center justify-center transition-colors duration-150 cursor-pointer"
                  :class="
                    authStore.isAdmin && route.path === '/admin/settings'
                      ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                      : 'text-text-secondary hover:text-text-main hover:bg-slate-300/50 dark:hover:bg-slate-800'
                  "
                >
                  <Settings class="w-4 h-4" />
                </button>

                <button
                  type="button"
                  @click="handleLogout"
                  title="退出登录"
                  class="w-9 h-9 rounded-xl flex items-center justify-center text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 transition-colors duration-150 cursor-pointer"
                >
                  <LogOut class="w-4 h-4" />
                </button>
              </div>
            </div>

            <!-- Mobile One-Tap Role Pills -->
            <div class="grid grid-cols-3 gap-1">
              <button
                v-for="identity in authStore.demoIdentities"
                :key="identity.username"
                type="button"
                @click="handleRoleSwitch(identity.username)"
                class="py-1.5 px-1 rounded-lg text-[10px] font-medium text-center border transition-colors cursor-pointer truncate"
                :class="
                  identity.username === authStore.currentUsername
                    ? 'bg-brand-primary/15 border-brand-primary/40 text-brand-primary font-semibold'
                    : 'bg-bg-card/60 border-border-subtle text-text-secondary hover:text-text-main'
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
import { ref, computed, watch, onUnmounted } from 'vue';
import {
  X,
  Plus,
  MessageSquare,
  ClipboardList,
  BookOpen,
  Trash2,
  ChevronRight,
  Sparkles,
  SlidersHorizontal,
  ListTodo,
  Activity,
  LogOut,
  Settings
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
        `已切换为「${authStore.displayName} (${authStore.roleLabel})」，当前页面不在该角色权限范围内，已返回智能对话工作台。`
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

// 抽屉展开时锁住背景滚动
watch(() => props.modelValue, (isOpen) => {
  if (typeof document !== 'undefined') {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
  }
});

onUnmounted(() => {
  if (typeof document !== 'undefined') {
    document.body.style.overflow = '';
  }
});
</script>
