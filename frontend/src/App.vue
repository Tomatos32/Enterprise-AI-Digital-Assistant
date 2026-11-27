<template>
  <!-- Full-Bleed Auth Layout (/login) -->
  <div v-if="isBlankLayout" class="min-h-screen w-screen bg-bg-main text-text-main font-sans antialiased">
    <router-view />
  </div>

  <!-- Standard Enterprise Copilot Studio Workspace Layout -->
  <div
    v-else
    class="h-screen w-screen overflow-hidden flex bg-bg-main text-text-main font-sans antialiased selection:bg-action-primary selection:text-action-primary-fg"
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
        :active-session-title="chatStore.activeSession?.title || '企业数字员工'"
        :sidebar-collapsed="isSidebarCollapsed"
        @toggle-sidebar="handleToggleSidebar"
      />

      <!-- Global RBAC Permission Notice Banner -->
      <transition name="banner-slide">
        <div
          v-if="authStore.permissionNotice"
          class="mx-4 sm:mx-6 mt-3 px-3.5 py-2.5 rounded-lg bg-bg-card border border-border-card text-text-main text-xs flex items-center justify-between gap-3 shrink-0"
        >
          <div class="flex items-center gap-2 min-w-0">
            <Lock class="w-3.5 h-3.5 text-text-secondary shrink-0" />
            <span class="leading-relaxed">{{ authStore.permissionNotice }}</span>
          </div>
          <button
            type="button"
            @click="authStore.clearPermissionNotice()"
            title="关闭提示"
            class="btn-pressable p-1 rounded-md hover:bg-bg-hover text-text-muted hover:text-text-main cursor-pointer shrink-0"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </transition>

      <!-- Content Router View -->
      <main class="flex-1 overflow-hidden relative flex flex-col">
        <router-view v-slot="{ Component }">
          <transition name="fade-fast" mode="out-in">
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
import { Lock, X } from 'lucide-vue-next';
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

const handleNewSession = () => {};
const handleSelectSession = () => {};
</script>
