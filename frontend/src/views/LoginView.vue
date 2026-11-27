<template>
  <div class="relative min-h-screen w-full bg-bg-main text-text-main flex flex-col justify-between p-4 sm:p-8 overflow-hidden transition-colors duration-180">
    <!-- Subtle Monochrome Architectural Dot Grid Backdrop -->
    <DotGridBackdrop :gap="24" :dot-size="1" :radius="150" />

    <!-- Top Bar: Brand & Theme Toggle -->
    <header class="relative z-10 max-w-5xl w-full mx-auto flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-action-primary text-action-primary-fg flex items-center justify-center shrink-0">
          <Layers class="w-4 h-4" />
        </div>
        <div>
          <h1 class="text-sm sm:text-base font-semibold tracking-tight text-text-main leading-tight">
            企业数字员工工作台
          </h1>
          <p class="text-[11px] text-text-muted">统一身份认证</p>
        </div>
      </div>

      <button
        type="button"
        @click="toggleTheme"
        :title="isDark ? '切换至日间模式' : '切换至夜间模式'"
        :aria-label="isDark ? '切换至日间模式' : '切换至夜间模式'"
        class="btn-secondary w-9 h-9 rounded-lg flex items-center justify-center text-text-secondary hover:text-text-main cursor-pointer"
      >
        <Sun v-if="isDark" class="w-4 h-4" />
        <Moon v-else class="w-4 h-4" />
      </button>
    </header>

    <!-- Main Two-Column Auth Container -->
    <main class="relative z-10 max-w-5xl w-full mx-auto my-8 grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
      <!-- Left: Role Isolation Overview -->
      <section class="lg:col-span-5 rounded-xl bg-bg-card border border-border-card p-6 sm:p-8 flex flex-col justify-between gap-6">
        <div class="space-y-3">
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-surface border border-border-subtle text-[11px] font-medium text-text-secondary">
            <ShieldCheck class="w-3.5 h-3.5 text-text-main" />
            <span>角色权限隔离</span>
          </span>

          <h2 class="text-xl sm:text-2xl font-semibold tracking-tight text-text-main leading-snug">
            按业务职责隔离空间，<br />保障检索与审批合规
          </h2>

          <p class="text-xs sm:text-sm text-text-secondary leading-relaxed">
            支持普通员工、部门主管与系统管理员三类身份，会话历史与接口权限严格边界隔离。
          </p>
        </div>

        <div class="space-y-3 pt-5 border-t border-border-subtle">
          <div class="flex items-start gap-3">
            <div class="w-7 h-7 rounded-lg bg-bg-surface border border-border-subtle text-text-secondary flex items-center justify-center shrink-0 mt-0.5">
              <User class="w-3.5 h-3.5" />
            </div>
            <div>
              <div class="text-xs font-semibold text-text-main">普通员工</div>
              <div class="text-[11px] text-text-muted">规章问答、制度查阅与日常申请</div>
            </div>
          </div>

          <div class="flex items-start gap-3">
            <div class="w-7 h-7 rounded-lg bg-bg-surface border border-border-subtle text-text-secondary flex items-center justify-center shrink-0 mt-0.5">
              <Briefcase class="w-3.5 h-3.5" />
            </div>
            <div>
              <div class="text-xs font-semibold text-text-main">部门主管</div>
              <div class="text-[11px] text-text-muted">待办审批工作台与大额采购决策</div>
            </div>
          </div>

          <div class="flex items-start gap-3">
            <div class="w-7 h-7 rounded-lg bg-bg-surface border border-border-subtle text-text-secondary flex items-center justify-center shrink-0 mt-0.5">
              <ShieldCheck class="w-3.5 h-3.5" />
            </div>
            <div>
              <div class="text-xs font-semibold text-text-main">系统管理员</div>
              <div class="text-[11px] text-text-muted">模型参数配置、知识库入库与运维监控</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Right: Credentials Form & Quick Role Switcher -->
      <section class="lg:col-span-7 rounded-xl bg-bg-card border border-border-card p-6 sm:p-8 space-y-6">
        <!-- Notice / Error Banner -->
        <transition name="banner-slide">
          <div
            v-if="noticeMessage || errorMessage"
            role="alert"
            class="px-3.5 py-2.5 rounded-lg border text-xs flex items-start gap-2.5"
            :class="
              errorMessage
                ? 'bg-bg-surface border-status-danger/40 text-status-danger'
                : 'bg-bg-surface border-border-strong text-text-main'
            "
          >
            <span
              class="w-1.5 h-1.5 rounded-full shrink-0 mt-1.5"
              :class="errorMessage ? 'bg-status-danger' : 'bg-status-approval'"
            ></span>
            <span class="leading-relaxed">{{ errorMessage || noticeMessage }}</span>
          </div>
        </transition>

        <!-- Standard Username/Password Login Form -->
        <form @submit.prevent="handleFormLogin" class="space-y-4">
          <div>
            <h3 class="text-base font-semibold text-text-main">账号密码登录</h3>
            <p class="text-xs text-text-muted mt-0.5">输入企业账号与密码以进入工作台</p>
          </div>

          <div class="space-y-3">
            <div>
              <label for="login-username" class="block text-xs font-medium text-text-secondary mb-1.5">
                用户账号
              </label>
              <div class="relative">
                <User class="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="login-username"
                  v-model="username"
                  type="text"
                  required
                  autocomplete="username"
                  placeholder="请输入账号名"
                  class="w-full pl-9 pr-3 py-2.5 rounded-lg bg-bg-input border border-border-card text-xs sm:text-sm text-text-main placeholder-text-muted focus:outline-none focus:border-border-focus transition-colors duration-150"
                />
              </div>
            </div>

            <div>
              <label for="login-password" class="block text-xs font-medium text-text-secondary mb-1.5">
                登录密码
              </label>
              <div class="relative">
                <Lock class="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="login-password"
                  v-model="password"
                  type="password"
                  required
                  autocomplete="current-password"
                  placeholder="请输入登录密码"
                  class="w-full pl-9 pr-3 py-2.5 rounded-lg bg-bg-input border border-border-card text-xs sm:text-sm text-text-main placeholder-text-muted focus:outline-none focus:border-border-focus transition-colors duration-150"
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            :disabled="authStore.isLoading"
            class="btn-primary w-full py-2.5 px-4 rounded-lg font-medium text-xs sm:text-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <LogIn class="w-4 h-4" />
            <span>{{ authStore.isLoading ? '正在验证身份...' : '登录工作台' }}</span>
          </button>
        </form>

        <!-- Quick Demo Role Switch Cards (No Plaintext Passwords) -->
        <div class="pt-5 border-t border-border-subtle space-y-3">
          <div>
            <h4 class="text-xs font-semibold text-text-main">快捷演示身份</h4>
            <p class="text-[11px] text-text-muted mt-0.5">选择角色一键切换上下文</p>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <button
              v-for="identity in authStore.demoIdentities"
              :key="identity.username"
              type="button"
              :disabled="authStore.isLoading"
              @click="handleQuickSwitch(identity.username)"
              class="btn-pressable p-3 rounded-lg border border-border-subtle bg-bg-surface hover:bg-bg-hover hover:border-border-strong text-left cursor-pointer group flex flex-col justify-between gap-2.5 disabled:opacity-50"
            >
              <div class="flex items-center justify-between">
                <div class="w-7 h-7 rounded-md bg-bg-card border border-border-subtle text-text-main flex items-center justify-center">
                  <component :is="getRoleIcon(identity.role)" class="w-3.5 h-3.5" />
                </div>
                <ArrowRight class="w-3.5 h-3.5 text-text-muted group-hover:text-text-main group-hover:translate-x-0.5 transition-[transform,color] duration-150" />
              </div>

              <div>
                <div class="text-xs font-semibold text-text-main">{{ identity.display_name }}</div>
                <div class="text-[11px] text-text-secondary mt-0.5">{{ identity.role_label }}</div>
                <div class="text-[10px] text-text-muted mt-0.5 truncate">{{ identity.department }}</div>
              </div>
            </button>
          </div>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="relative z-10 max-w-5xl w-full mx-auto text-center text-[11px] text-text-muted">
      企业数字员工统一认证中心
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import {
  Layers,
  ShieldCheck,
  User,
  Briefcase,
  Lock,
  LogIn,
  ArrowRight,
  Sun,
  Moon,
} from 'lucide-vue-next';
import { useAuthStore } from '../stores/authStore';
import { usePreferencesStore } from '../stores/preferencesStore';
import DotGridBackdrop from '../components/ui/DotGridBackdrop.vue';

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
    errorMessage.value = res.error || '身份切换失败，请检查服务状态';
  }
};

onMounted(() => {
  authStore.fetchDemoIdentities();
});
</script>
