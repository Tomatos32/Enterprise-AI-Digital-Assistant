<template>
  <header class="h-14 bg-bg-main border-b border-border-subtle px-4 flex items-center justify-between shrink-0 select-none relative z-10 transition-colors duration-180">
    <!-- Offline Quiet Banner (Only displays if network disconnects) -->
    <div
      v-if="!isOnline"
      class="absolute top-0 left-0 right-0 h-7 bg-bg-surface border-b border-border-card text-text-secondary text-[11px] font-medium flex items-center justify-center gap-1.5 z-30 transition-opacity duration-180"
    >
      <WifiOff class="w-3.5 h-3.5 text-status-approval shrink-0" />
      <span>连接中断，正在自动重连</span>
    </div>

    <!-- Left Controls: Sidebar Toggle & Assistant Mode Selector -->
    <div class="flex items-center gap-2">
      <button
        type="button"
        @click="$emit('toggleSidebar')"
        title="展开/收起导航"
        class="btn-pressable w-10 h-10 sm:w-8 sm:h-8 rounded-lg text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer flex items-center justify-center shrink-0"
      >
        <Menu class="w-4 h-4" />
      </button>

      <!-- Assistant Mode Selector -->
      <div ref="modeDropdownRef" class="relative">
        <button
          type="button"
          @click.stop="isDropdownOpen = !isDropdownOpen"
          class="btn-pressable flex items-center gap-2 px-2.5 py-1.5 h-8 rounded-lg bg-bg-card hover:bg-bg-hover border border-border-card text-xs font-medium text-text-main cursor-pointer"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-status-success shrink-0"></span>
          <span class="max-w-[140px] sm:max-w-[220px] truncate text-left">{{ currentModeLabel }}</span>
          <ChevronDown
            class="w-3.5 h-3.5 text-text-muted transition-transform duration-150 shrink-0"
            :class="{ 'rotate-180': isDropdownOpen }"
          />
        </button>

        <transition name="popover">
          <div
            v-if="isDropdownOpen"
            class="origin-top-left absolute top-10 left-0 w-64 max-w-[calc(100vw-1.5rem)] bg-bg-card p-1.5 rounded-xl border border-border-card shadow-sm space-y-0.5 z-30"
          >
            <button
              v-for="mode in availableModes"
              :key="mode.id"
              type="button"
              @click="selectMode(mode.id)"
              class="w-full px-2.5 py-2 rounded-lg text-xs text-left flex items-center gap-2.5 cursor-pointer transition-colors duration-150"
              :class="
                chatStore.selectedMode === mode.id
                  ? 'bg-bg-surface text-text-main font-semibold'
                  : 'text-text-secondary hover:text-text-main hover:bg-bg-hover'
              "
            >
              <component :is="mode.icon" class="w-3.5 h-3.5 text-text-secondary shrink-0" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between gap-2">
                  <span class="truncate">{{ mode.title }}</span>
                  <Check v-if="chatStore.selectedMode === mode.id" class="w-3.5 h-3.5 text-text-main shrink-0" />
                </div>
                <div class="text-[11px] text-text-muted truncate">{{ mode.desc }}</div>
              </div>
            </button>
          </div>
        </transition>
      </div>
    </div>

    <!-- Center Session Title -->
    <div class="hidden md:flex items-center text-xs text-text-secondary max-w-sm truncate">
      <span class="truncate font-medium">{{ activeSessionTitle || '企业数字员工' }}</span>
    </div>

    <!-- Right Quick Actions: Theme Toggle, New Chat & Role Switcher -->
    <div class="flex items-center gap-2">
      <button
        type="button"
        @click="toggleTheme"
        :title="isDark ? '切换至日间模式' : '切换至夜间模式'"
        class="btn-pressable w-8 h-8 rounded-lg bg-bg-card hover:bg-bg-hover border border-border-card flex items-center justify-center text-text-secondary hover:text-text-main cursor-pointer"
      >
        <Sun v-if="isDark" class="w-4 h-4" />
        <Moon v-else class="w-4 h-4" />
      </button>

      <button
        type="button"
        @click="chatStore.createSession()"
        title="新建对话"
        class="btn-pressable hidden sm:inline-flex items-center gap-1.5 px-2.5 h-8 rounded-lg bg-bg-card hover:bg-bg-hover border border-border-card text-xs font-medium text-text-main cursor-pointer"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>新对话</span>
      </button>

      <RoleSwitcherPopover />
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import {
  Menu,
  ChevronDown,
  WifiOff,
  Plus,
  Check,
  Cpu,
  Layers,
  ShieldCheck,
  Bot,
  Sun,
  Moon,
} from 'lucide-vue-next';
import { useChatStore } from '../../stores/chatStore';
import { usePreferencesStore } from '../../stores/preferencesStore';
import RoleSwitcherPopover from './RoleSwitcherPopover.vue';

defineProps({
  activeSessionTitle: {
    type: String,
    default: '',
  },
  sidebarCollapsed: {
    type: Boolean,
    default: false,
  },
});

defineEmits(['toggleSidebar']);

const chatStore = useChatStore();
const preferencesStore = usePreferencesStore();
const isDropdownOpen = ref(false);
const modeDropdownRef = ref(null);
const isOnline = computed(() => chatStore.isOnline);
const isDark = computed(() => preferencesStore.isDark);

const toggleTheme = () => {
  preferencesStore.toggleTheme();
};

const availableModes = [
  { id: 'general', title: '企业通用助手', desc: '规章检索、工单与审批协同', icon: Bot },
  { id: 'it', title: 'IT 运维助手', desc: '故障排查与 P1~P4 工单流转', icon: Cpu },
  { id: 'finance', title: '财务采购协同', desc: '预算核验、ERP 库存与审批', icon: Layers },
  { id: 'hr', title: '人事合规顾问', desc: '考勤年假与差旅报销规范', icon: ShieldCheck },
];

const currentModeLabel = computed(() => {
  const m = availableModes.find((item) => item.id === chatStore.selectedMode);
  return m ? m.title : '企业通用助手';
});

const selectMode = (modeId) => {
  chatStore.selectedMode = modeId;
  isDropdownOpen.value = false;
};

const handleClickOutside = (e) => {
  if (isDropdownOpen.value && modeDropdownRef.value && !modeDropdownRef.value.contains(e.target)) {
    isDropdownOpen.value = false;
  }
};

const handleKeydown = (e) => {
  if (e.key === 'Escape' && isDropdownOpen.value) {
    isDropdownOpen.value = false;
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
</script>
