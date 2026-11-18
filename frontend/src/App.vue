<template>
  <!-- Full-Bleed Auth Layout (/login) -->
  <div v-if="isBlankLayout" class="min-h-screen w-screen bg-bg-main text-text-main font-sans antialiased">
    <router-view />
  </div>

  <!-- Standard Enterprise Copilot Studio Workspace Layout -->
  <div
    v-else
    class="h-screen w-screen overflow-hidden flex bg-bg-main text-text-main font-sans antialiased selection:bg-brand-primary/30 selection:text-white"
  >
    <!-- Desktop Collapsible Sidebar (Hidden on mobile < md) -->
    <Sidebar
      class="hidden md:flex"
      :is-collapsed="isSidebarCollapsed"
      @update:is-collapsed="val => isSidebarCollapsed = val"
      @new-session="handleNewSession"
      @select-session="handleSelectSession"
    />

    <!-- Mobile Off-Canvas Drawer (< md) -->
    <MobileDrawer
      v-model="isMobileDrawerOpen"
      @new-session="handleNewSession"
      @select-session="handleSelectSession"
    />

    <!-- Main Workspace Area -->
    <div class="flex-1 flex flex-col h-full overflow-hidden min-w-0">
      <!-- Lightweight Header -->
      <Header
        :active-session-title="chatStore.activeSession?.title || '企业通用数字员工'"
        :sidebar-collapsed="isSidebarCollapsed"
        @toggle-sidebar="handleToggleSidebar"
      />

      <!-- Global RBAC Permission Notice Banner -->
      <transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 -translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-2"
      >
        <div
          v-if="authStore.permissionNotice"
          class="mx-3 sm:mx-6 mt-2.5 px-3.5 py-2.5 rounded-2xl bg-amber-500/10 border border-amber-500/35 text-amber-800 dark:text-amber-200 text-xs flex items-center justify-between gap-3 shadow-sm shrink-0"
        >
          <div class="flex items-center space-x-2 min-w-0">
            <ShieldAlert class="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
            <span class="leading-relaxed">{{ authStore.permissionNotice }}</span>
          </div>
          <button
            type="button"
            @click="authStore.clearPermissionNotice()"
            title="关闭提示"
            class="p-1 rounded-lg hover:bg-amber-500/20 text-amber-700 dark:text-amber-300 transition-colors cursor-pointer shrink-0"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </transition>

      <!-- Content Router View -->
      <main class="flex-1 overflow-hidden relative flex flex-col">
        <router-view v-slot="{ Component }">
          <transition
            enter-active-class="transition-opacity duration-150 ease-out"
            enter-from-class="opacity-0"
            enter-to-class="opacity-100"
            leave-active-class="transition-opacity duration-100 ease-in"
            leave-from-class="opacity-100"
            leave-to-class="opacity-0"
            mode="out-in"
          >
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <!-- Personal Appearance & Display Preferences Modal (Role-Layered Entry) -->
    <UserPreferencesModal />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ShieldAlert, X } from 'lucide-vue-next';
import Sidebar from './components/layout/Sidebar.vue';
import MobileDrawer from './components/layout/MobileDrawer.vue';
import Header from './components/layout/Header.vue';
import UserPreferencesModal from './components/layout/UserPreferencesModal.vue';
import { useChatStore } from './stores/chatStore';
import { useAuthStore } from './stores/authStore';
import { useApprovalStore } from './stores/approvalStore';
import { usePreferencesStore } from './stores/preferencesStore';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const chatStore = useChatStore();
const approvalStore = useApprovalStore();
usePreferencesStore();

const isSidebarCollapsed = ref(false);
const isMobileDrawerOpen = ref(false);

const isBlankLayout = computed(() => route.meta?.layout === 'blank');

watch(
  () => authStore.isAuthenticated,
  (authed) => {
    if (authStore.initialized && !authed && route.meta?.requiresAuth) {
      router.replace({ path: '/login', query: { redirect: route.fullPath } });
    }
  }
);

watch(
  () => authStore.currentUsername,
  async (newUser, oldUser) => {
    if (newUser === oldUser) return;
    await Promise.all([
      approvalStore.handleIdentityChange(),
      chatStore.handleIdentityChange(),
    ]);
  },
  { immediate: true }
);

const handleToggleSidebar = () => {
  if (typeof window !== 'undefined' && window.innerWidth < 768) {
    isMobileDrawerOpen.value = !isMobileDrawerOpen.value;
  } else {
    isSidebarCollapsed.value = !isSidebarCollapsed.value;
  }
};

const handleNewSession = () => {
  // 新会话已在 chatStore 中创建并切换为活跃
};

const handleSelectSession = () => {
  // 活跃会话已切换
};
</script>
