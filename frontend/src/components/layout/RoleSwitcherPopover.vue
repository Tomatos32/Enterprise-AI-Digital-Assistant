<template>
  <div ref="rootRef" class="relative">
    <!-- Trigger Button -->
    <button
      type="button"
      @click.stop="toggleMenu"
      :title="`${authStore.displayName} (${authStore.department} · ${authStore.roleLabel})`"
      class="btn-pressable flex items-center gap-2 px-2 h-8 rounded-lg bg-bg-card hover:bg-bg-hover border border-border-card cursor-pointer"
    >
      <div class="w-6 h-6 rounded-full bg-bg-surface border border-border-card text-text-main flex items-center justify-center text-[11px] font-semibold shrink-0">
        {{ authStore.avatarInitial }}
      </div>

      <div class="hidden sm:flex items-center gap-1.5 max-w-[150px]">
        <span class="text-xs font-medium text-text-main truncate">{{ authStore.displayName }}</span>
        <span class="px-1.5 py-0.5 text-[10px] font-medium rounded bg-bg-surface text-text-secondary border border-border-subtle shrink-0">
          {{ authStore.roleLabel }}
        </span>
      </div>

      <ChevronDown
        class="w-3.5 h-3.5 text-text-muted transition-transform duration-150 shrink-0"
        :class="{ 'rotate-180': isOpen }"
      />
    </button>

    <!-- Origin-Aware Dropdown Popover -->
    <transition name="popover">
      <div
        v-if="isOpen"
        class="origin-top-right absolute right-0 mt-2 w-72 rounded-xl bg-bg-card border border-border-card shadow-sm p-2 z-50 space-y-2.5"
      >
        <!-- Current Active User -->
        <div class="p-2.5 rounded-lg bg-bg-surface border border-border-subtle flex items-center gap-2.5">
          <div class="w-9 h-9 rounded-full bg-bg-card border border-border-card text-text-main flex items-center justify-center text-xs font-semibold shrink-0">
            {{ authStore.avatarInitial }}
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-semibold text-text-main truncate">{{ authStore.displayName }}</span>
              <span class="px-1.5 py-0.5 text-[10px] font-medium rounded bg-bg-card text-text-secondary border border-border-card shrink-0">
                {{ authStore.roleLabel }}
              </span>
            </div>
            <div class="text-[11px] text-text-muted truncate mt-0.5">
              {{ authStore.department }} · {{ authStore.currentUsername }}
            </div>
          </div>
        </div>

        <!-- Quick Role Switch -->
        <div class="space-y-1">
          <div class="px-2 py-0.5 flex items-center justify-between text-[11px] font-medium text-text-muted">
            <span>切换身份</span>
            <ArrowLeftRight class="w-3 h-3" />
          </div>

          <button
            v-for="identity in identities"
            :key="identity.username"
            type="button"
            :disabled="authStore.isLoading"
            @click="handleSwitch(identity.username)"
            class="w-full p-2 rounded-lg text-left flex items-center justify-between transition-colors duration-150 cursor-pointer border"
            :class="
              identity.username === authStore.currentUsername
                ? 'bg-bg-surface border-border-card text-text-main'
                : 'border-transparent hover:bg-bg-hover text-text-secondary hover:text-text-main'
            "
          >
            <div class="flex items-center gap-2.5 min-w-0">
              <div class="w-7 h-7 rounded-md bg-bg-card border border-border-subtle text-text-secondary flex items-center justify-center shrink-0">
                <component :is="getRoleIcon(identity.role)" class="w-3.5 h-3.5" />
              </div>
              <div class="min-w-0">
                <div class="text-xs font-medium text-text-main truncate">
                  {{ identity.display_name }} · {{ identity.role_label }}
                </div>
                <div class="text-[10px] text-text-muted truncate">{{ identity.department }}</div>
              </div>
            </div>
            <Check v-if="identity.username === authStore.currentUsername" class="w-3.5 h-3.5 text-text-main shrink-0" />
          </button>
        </div>

        <!-- Preferences & Auth Actions -->
        <div class="pt-2 border-t border-border-subtle space-y-1">
          <button
            type="button"
            @click="openPreferences"
            class="btn-pressable w-full px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover flex items-center justify-between cursor-pointer"
          >
            <span class="flex items-center gap-2">
              <SlidersHorizontal class="w-3.5 h-3.5" />
              <span>显示偏好</span>
            </span>
            <span class="text-[11px] text-text-muted">主题与密度</span>
          </button>

          <div class="flex items-center gap-1.5 pt-1">
            <button
              type="button"
              @click="goToLogin"
              class="btn-pressable flex-1 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-main hover:bg-bg-hover flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <KeyRound class="w-3.5 h-3.5" />
              <span>账号登录</span>
            </button>

            <button
              type="button"
              @click="handleLogout"
              class="btn-pressable flex-1 px-2.5 py-1.5 rounded-lg text-xs text-status-danger hover:bg-bg-hover flex items-center justify-center gap-1.5 cursor-pointer"
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

const getRoleIcon = (role) => {
  if (role === 'admin') return ShieldCheck;
  if (role === 'manager') return Briefcase;
  return User;
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
        `已切换为「${authStore.displayName} (${authStore.roleLabel})」，当前页面不在该角色权限范围内，已返回对话工作台。`
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

const onKeydown = (event) => {
  if (event.key === 'Escape' && isOpen.value) {
    isOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', onClickOutside);
  document.addEventListener('keydown', onKeydown);
});

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside);
  document.removeEventListener('keydown', onKeydown);
});
</script>
