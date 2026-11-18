<template>
  <div ref="rootRef" class="relative">
    <!-- Trigger Pill / Avatar Button -->
    <button
      type="button"
      @click.stop="toggleMenu"
      :title="`${authStore.displayName} (${authStore.department} · ${authStore.roleLabel})`"
      class="flex items-center space-x-2 px-2 py-1 rounded-xl glass-panel hover:bg-slate-200/70 dark:hover:bg-slate-800/90 border border-border-subtle hover:border-brand-primary/40 transition-colors duration-150 cursor-pointer shadow-sm active:scale-[0.98]"
    >
      <div
        class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 border"
        :class="avatarBadgeClass"
      >
        {{ authStore.avatarInitial }}
      </div>

      <div class="hidden sm:flex flex-col items-start text-left leading-tight max-w-[140px]">
        <div class="flex items-center space-x-1.5 w-full">
          <span class="text-xs font-semibold text-text-main truncate">{{ authStore.displayName }}</span>
          <span
            class="px-1.5 py-0.5 text-[10px] font-medium rounded-md border shrink-0"
            :class="roleBadgeClass"
          >
            {{ authStore.roleLabel }}
          </span>
        </div>
        <span class="text-[10px] text-text-muted truncate w-full">{{ authStore.department }}</span>
      </div>

      <ChevronDown
        class="w-3.5 h-3.5 text-text-muted transition-transform duration-150 shrink-0"
        :class="{ 'rotate-180': isOpen }"
      />
    </button>

    <!-- Dropdown Popover -->
    <transition
      enter-active-class="transition ease-out duration-150"
      enter-from-class="opacity-0 translate-y-1 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition ease-in duration-100"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-1 scale-95"
    >
      <div
        v-if="isOpen"
        class="absolute right-0 mt-2 w-72 sm:w-80 rounded-2xl bg-bg-card border border-border-card shadow-2xl p-2 z-50 space-y-2"
      >
        <!-- Current Active User Summary -->
        <div class="p-2.5 rounded-xl bg-slate-100/90 dark:bg-slate-900/80 border border-border-subtle flex items-center space-x-3">
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold border shrink-0"
            :class="avatarBadgeClass"
          >
            {{ authStore.avatarInitial }}
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center space-x-1.5">
              <span class="text-xs font-bold text-text-main truncate">{{ authStore.displayName }}</span>
              <span
                class="px-1.5 py-0.5 text-[10px] font-medium rounded-md border shrink-0"
                :class="roleBadgeClass"
              >
                {{ authStore.roleLabel }}
              </span>
            </div>
            <div class="text-[11px] text-text-secondary truncate mt-0.5">
              {{ authStore.department }} · {{ authStore.currentUsername }}
            </div>
          </div>
        </div>

        <!-- Quick Role Context Switcher -->
        <div class="space-y-1">
          <div class="px-2 py-1 flex items-center justify-between text-[11px] font-semibold text-text-muted">
            <span class="flex items-center space-x-1">
              <ArrowLeftRight class="w-3 h-3 text-brand-primary" />
              <span>角色上下文快捷切换</span>
            </span>
            <span class="text-[10px] font-normal">演示协同域</span>
          </div>

          <button
            v-for="identity in identities"
            :key="identity.username"
            type="button"
            :disabled="authStore.isLoading"
            @click="handleSwitch(identity.username)"
            class="w-full p-2 rounded-xl text-left flex items-center justify-between transition-colors duration-150 cursor-pointer border"
            :class="
              identity.username === authStore.currentUsername
                ? 'bg-brand-primary/10 border-brand-primary/40 text-text-main'
                : 'border-transparent hover:bg-slate-100 dark:hover:bg-slate-800/70 text-text-secondary hover:text-text-main'
            "
          >
            <div class="flex items-center space-x-2.5 min-w-0">
              <div
                class="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                :class="getRoleIconBg(identity.role)"
              >
                <component :is="getRoleIcon(identity.role)" class="w-3.5 h-3.5" />
              </div>
              <div class="min-w-0">
                <div class="flex items-center space-x-1.5">
                  <span class="text-xs font-semibold text-text-main truncate">{{ identity.display_name }}</span>
                  <span class="text-[10px] text-text-muted">· {{ identity.role_label }}</span>
                </div>
                <div class="text-[10px] text-text-muted truncate">{{ identity.department }}</div>
              </div>
            </div>

            <Check
              v-if="identity.username === authStore.currentUsername"
              class="w-4 h-4 text-brand-primary shrink-0"
            />
          </button>
        </div>

        <!-- Divider & Utility Actions -->
        <div class="border-t border-border-subtle pt-1.5 space-y-1">
          <button
            type="button"
            @click="openPreferences"
            class="w-full px-2.5 py-1.5 rounded-xl text-xs text-text-secondary hover:text-text-main hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-between transition-colors duration-150 cursor-pointer"
          >
            <span class="flex items-center space-x-1.5">
              <SlidersHorizontal class="w-3.5 h-3.5 text-brand-primary" />
              <span>个人外观与显示偏好</span>
            </span>
            <span class="text-[10px] text-text-muted">主题 / 密度</span>
          </button>

          <div class="flex items-center justify-between gap-2">
            <button
              type="button"
              @click="goToLogin"
              class="flex-1 px-2.5 py-1.5 rounded-xl text-xs text-text-secondary hover:text-text-main hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center space-x-1.5 transition-colors duration-150 cursor-pointer"
            >
              <KeyRound class="w-3.5 h-3.5 text-brand-primary" />
              <span>账号登录</span>
            </button>

            <button
              type="button"
              @click="handleLogout"
              class="flex-1 px-2.5 py-1.5 rounded-xl text-xs text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 flex items-center justify-center space-x-1.5 transition-colors duration-150 cursor-pointer"
            >
              <LogOut class="w-3.5 h-3.5" />
              <span>退出登录</span>
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import {
  ChevronDown,
  Check,
  ArrowLeftRight,
  User,
  Briefcase,
  ShieldCheck,
  KeyRound,
  LogOut,
  SlidersHorizontal,
} from 'lucide-vue-next';
import { useAuthStore } from '../../stores/authStore';
import { usePreferencesStore } from '../../stores/preferencesStore';

const authStore = useAuthStore();
const preferencesStore = usePreferencesStore();
const router = useRouter();
const route = useRoute();

const isOpen = ref(false);
const rootRef = ref(null);

const identities = computed(() => authStore.demoIdentities);

const roleBadgeClass = computed(() => {
  if (authStore.currentRole === 'admin') {
    return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30';
  }
  if (authStore.currentRole === 'manager') {
    return 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30';
  }
  return 'bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30';
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

const getRoleIcon = (role) => {
  if (role === 'admin') return ShieldCheck;
  if (role === 'manager') return Briefcase;
  return User;
};

const getRoleIconBg = (role) => {
  if (role === 'admin') return 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400';
  if (role === 'manager') return 'bg-amber-500/15 text-amber-600 dark:text-amber-400';
  return 'bg-blue-500/15 text-blue-600 dark:text-blue-400';
};

const toggleMenu = () => {
  isOpen.value = !isOpen.value;
  if (isOpen.value) {
    authStore.fetchDemoIdentities();
  }
};

const handleSwitch = async (username) => {
  if (username === authStore.currentUsername) {
    isOpen.value = false;
    return;
  }
  const res = await authStore.switchRole(username);
  isOpen.value = false;
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
  isOpen.value = false;
  router.push('/login');
};

const openPreferences = () => {
  isOpen.value = false;
  preferencesStore.openPreferencesModal();
};

const handleLogout = () => {
  isOpen.value = false;
  authStore.logout(true);
  router.push('/login');
};

const onClickOutside = (event) => {
  if (isOpen.value && rootRef.value && !rootRef.value.contains(event.target)) {
    isOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', onClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside);
});
</script>
