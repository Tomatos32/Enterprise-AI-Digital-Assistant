<template>
  <div class="min-h-screen w-full bg-bg-main text-text-main flex flex-col justify-between p-4 sm:p-8 transition-colors duration-200">
    <!-- Top Bar: Brand & Theme Toggle -->
    <div class="max-w-5xl w-full mx-auto flex items-center justify-between">
      <div class="flex items-center space-x-2.5">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center shadow-md shadow-blue-500/20">
          <Sparkles class="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 class="text-sm sm:text-base font-bold text-text-main leading-tight">企业级数字员工协同平台</h1>
          <p class="text-[11px] text-text-muted">统一身份认证与权限治理中心</p>
        </div>
      </div>

      <button
        type="button"
        @click="toggleTheme"
        :title="isDark ? '切换至日间温润白模式' : '切换至夜间曜石灰模式'"
        class="w-9 h-9 rounded-xl glass-panel hover:bg-slate-200/60 dark:hover:bg-slate-800 border border-border-subtle flex items-center justify-center text-text-secondary hover:text-text-main transition-colors duration-150 cursor-pointer shadow-sm"
      >
        <Sun v-if="isDark" class="w-4 h-4 text-amber-400" />
        <Moon v-else class="w-4 h-4 text-slate-700" />
      </button>
    </div>

    <!-- Main Two-Column Auth Container -->
    <div class="max-w-5xl w-full mx-auto my-8 grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
      <!-- Left: Enterprise Capability Summary -->
      <div class="lg:col-span-5 rounded-3xl glass-card border border-border-card p-6 sm:p-8 flex flex-col justify-between space-y-6 shadow-xl">
        <div class="space-y-4">
          <span class="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-brand-primary/10 text-brand-primary border border-brand-primary/30 text-xs font-medium">
            <ShieldCheck class="w-3.5 h-3.5" />
            <span>企业级角色隔离架构</span>
          </span>

          <h2 class="text-xl sm:text-2xl font-bold text-text-main leading-snug">
            按职责隔离工作空间，<br />保障制度检索与审批安全合规
          </h2>

          <p class="text-xs sm:text-sm text-text-secondary leading-relaxed">
            支持普通员工、部门主管与系统管理员三类核心业务身份。每个身份拥有独立的会话持久化空间与严格的接口访问边界。
          </p>
        </div>

        <div class="space-y-3 pt-4 border-t border-border-subtle">
          <div class="flex items-start space-x-3">
            <div class="w-7 h-7 rounded-lg bg-blue-500/15 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
              <User class="w-4 h-4" />
            </div>
            <div>
              <div class="text-xs font-semibold text-text-main">普通员工</div>
              <div class="text-[11px] text-text-muted">智能问答、规章知识库检索及个人采购工单发起</div>
            </div>
          </div>

          <div class="flex items-start space-x-3">
            <div class="w-7 h-7 rounded-lg bg-amber-500/15 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0 mt-0.5">
              <Briefcase class="w-4 h-4" />
            </div>
            <div>
              <div class="text-xs font-semibold text-text-main">部门主管</div>
              <div class="text-[11px] text-text-muted">开放待我审批工作台，执行大额采购人机协同决策</div>
            </div>
          </div>

          <div class="flex items-start space-x-3">
            <div class="w-7 h-7 rounded-lg bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
              <ShieldCheck class="w-4 h-4" />
            </div>
            <div>
              <div class="text-xs font-semibold text-text-main">系统管理员</div>
              <div class="text-[11px] text-text-muted">解锁系统管理控制台，统筹参数配置、任务与遥测</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Credentials Form & Quick Role Switcher -->
      <div class="lg:col-span-7 rounded-3xl glass-card border border-border-card p-6 sm:p-8 shadow-xl space-y-6">
        <!-- Notice Banner if redirected -->
        <div
          v-if="noticeMessage || errorMessage"
          class="p-3 rounded-xl border text-xs flex items-start space-x-2"
          :class="errorMessage ? 'bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300' : 'bg-amber-500/10 border-amber-500/30 text-amber-800 dark:text-amber-200'"
        >
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          <span>{{ errorMessage || noticeMessage }}</span>
        </div>

        <!-- Standard Username/Password Login Form -->
        <form @submit.prevent="handleFormLogin" class="space-y-4">
          <div>
            <h3 class="text-base font-bold text-text-main">账号密码登录</h3>
            <p class="text-xs text-text-muted mt-0.5">请输入企业域账号与密码获取访问凭证</p>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1.5">用户账号</label>
              <div class="relative">
                <User class="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  v-model="username"
                  type="text"
                  required
                  autocomplete="username"
                  placeholder="请输入账号名"
                  class="w-full pl-9 pr-3 py-2.5 rounded-xl bg-bg-input border border-border-card text-xs sm:text-sm text-text-main placeholder-text-muted focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary/30 transition-colors"
                />
              </div>
            </div>

            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1.5">登录密码</label>
              <div class="relative">
                <Lock class="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  v-model="password"
                  type="password"
                  required
                  autocomplete="current-password"
                  placeholder="请输入登录密码"
                  class="w-full pl-9 pr-3 py-2.5 rounded-xl bg-bg-input border border-border-card text-xs sm:text-sm text-text-main placeholder-text-muted focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary/30 transition-colors"
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            :disabled="authStore.isLoading"
            class="w-full py-2.5 px-4 rounded-xl bg-brand-primary hover:bg-brand-primary-hover text-white font-semibold text-xs sm:text-sm shadow-md shadow-blue-600/20 flex items-center justify-center space-x-2 transition-colors duration-150 cursor-pointer disabled:opacity-50"
          >
            <LogIn class="w-4 h-4" />
            <span>{{ authStore.isLoading ? '正在验证身份...' : '登录工作台' }}</span>
          </button>
        </form>

        <!-- Quick Demo Role Switch Cards (No Plaintext Passwords) -->
        <div class="pt-5 border-t border-border-subtle space-y-3">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="text-xs font-bold text-text-main">快捷演示身份体验</h4>
              <p class="text-[11px] text-text-muted mt-0.5">点击下方角色卡片直接完成身份上下文切换与视图验证</p>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <button
              v-for="identity in authStore.demoIdentities"
              :key="identity.username"
              type="button"
              :disabled="authStore.isLoading"
              @click="handleQuickSwitch(identity.username)"
              class="p-3 rounded-2xl border border-border-subtle hover:border-brand-primary/50 bg-slate-100/70 dark:bg-slate-900/70 hover:bg-slate-200/60 dark:hover:bg-slate-800/80 text-left transition-all duration-150 cursor-pointer group flex flex-col justify-between space-y-2 disabled:opacity-50"
            >
              <div class="flex items-center justify-between">
                <div
                  class="w-8 h-8 rounded-xl flex items-center justify-center"
                  :class="getRoleBadgeClass(identity.role)"
                >
                  <component :is="getRoleIcon(identity.role)" class="w-4 h-4" />
                </div>
                <ArrowRight class="w-3.5 h-3.5 text-text-muted group-hover:text-brand-primary group-hover:translate-x-0.5 transition-all" />
              </div>

              <div>
                <div class="text-xs font-bold text-text-main">{{ identity.display_name }}</div>
                <div class="text-[11px] text-text-secondary mt-0.5">{{ identity.role_label }}</div>
                <div class="text-[10px] text-text-muted mt-0.5 truncate">{{ identity.department }}</div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="max-w-5xl w-full mx-auto text-center text-[11px] text-text-muted">
      企业级数字员工统一鉴权与角色隔离基座
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import {
  Sparkles,
  ShieldCheck,
  User,
  Briefcase,
  Lock,
  LogIn,
  ArrowRight,
  AlertCircle,
  Sun,
  Moon,
} from 'lucide-vue-next';
import { useAuthStore } from '../stores/authStore';
import { usePreferencesStore } from '../stores/preferencesStore';

const authStore = useAuthStore();
const preferencesStore = usePreferencesStore();
const router = useRouter();
const route = useRoute();

const username = ref('');
const password = ref('');
const errorMessage = ref('');
const isDark = computed(() => preferencesStore.isDark);

const noticeMessage = computed(() => authStore.permissionNotice);

const toggleTheme = () => {
  preferencesStore.toggleTheme();
};

const getRoleIcon = (role) => {
  if (role === 'admin') return ShieldCheck;
  if (role === 'manager') return Briefcase;
  return User;
};

const getRoleBadgeClass = (role) => {
  if (role === 'admin') return 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400';
  if (role === 'manager') return 'bg-amber-500/15 text-amber-600 dark:text-amber-400';
  return 'bg-blue-500/15 text-blue-600 dark:text-blue-400';
};

const navigateAfterLogin = () => {
  const rawRedirect = typeof route.query.redirect === 'string' ? route.query.redirect : '';
  const isSafeInternal =
    rawRedirect.startsWith('/') && !rawRedirect.startsWith('//') && rawRedirect !== '/login';
  router.push(isSafeInternal ? rawRedirect : '/');
};

const handleFormLogin = async () => {
  errorMessage.value = '';
  const res = await authStore.login(username.value, password.value);
  if (res.success) {
    navigateAfterLogin();
  } else {
    errorMessage.value = res.error || '登录失败，请重试';
  }
};

const handleQuickSwitch = async (targetUsername) => {
  errorMessage.value = '';
  const res = await authStore.switchRole(targetUsername);
  if (res.success) {
    navigateAfterLogin();
  } else {
    errorMessage.value = res.error || '身份切换失败，请检查后端服务状态';
  }
};

onMounted(() => {
  authStore.fetchDemoIdentities();
});
</script>
