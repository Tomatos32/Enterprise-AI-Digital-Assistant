<template>
  <div class="h-screen w-screen overflow-hidden flex bg-bg-main text-text-main font-sans antialiased selection:bg-brand-primary/30 selection:text-white">
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
  </div>
</template>

<script setup>
import { ref } from 'vue';
import Sidebar from './components/layout/Sidebar.vue';
import MobileDrawer from './components/layout/MobileDrawer.vue';
import Header from './components/layout/Header.vue';
import { useChatStore } from './stores/chatStore';

const chatStore = useChatStore();
const isSidebarCollapsed = ref(false);
const isMobileDrawerOpen = ref(false);

const handleToggleSidebar = () => {
  if (typeof window !== 'undefined' && window.innerWidth < 768) {
    isMobileDrawerOpen.value = !isMobileDrawerOpen.value;
  } else {
    isSidebarCollapsed.value = !isSidebarCollapsed.value;
  }
};

const handleNewSession = (session) => {
  // 新会话已在 chatStore 中创建并切换为活跃
};

const handleSelectSession = (sessionId) => {
  // 活跃会话已切换
};
</script>
