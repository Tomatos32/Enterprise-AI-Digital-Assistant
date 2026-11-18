<template>
  <header class="h-14 bg-bg-main/80 backdrop-blur-md border-b border-border-subtle px-4 flex items-center justify-between shrink-0 select-none relative z-10 transition-colors duration-200">
    <!-- Offline Quiet Banner (Only displays if network disconnects) -->
    <div
      v-if="!isOnline"
      class="absolute top-0 left-0 right-0 h-7 bg-amber-500/10 border-b border-amber-500/40 text-amber-700 dark:text-amber-300 text-[11px] font-medium flex items-center justify-center space-x-1.5 z-30 transition-all duration-300"
    >
      <WifiOff class="w-3.5 h-3.5 text-status-approval animate-pulse" />
      <span>网络连接已断开，系统正在后台静默自动重连中...</span>
    </div>

    <!-- Left Controls: Sidebar Hamburger Toggle & Assistant Mode Selector -->
    <div class="flex items-center space-x-1.5 sm:space-x-2">
      <!-- Hamburger Sidebar Toggle Button -->
      <button
        @click="$emit('toggleSidebar')"
        title="展开/收起导航"
        class="w-11 h-11 sm:w-8 sm:h-8 rounded-xl text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-800/80 transition-colors duration-150 cursor-pointer flex items-center justify-center shrink-0 active:scale-95"
      >
        <Menu class="w-5 h-5 sm:w-4 sm:h-4" />
      </button>

      <!-- Assistant Mode Selector Capsule -->
      <div class="relative">
        <button
          @click="isDropdownOpen = !isDropdownOpen"
          class="flex items-center space-x-1.5 sm:space-x-2 px-2.5 sm:px-3 py-1.5 min-h-[38px] rounded-xl glass-panel hover:bg-slate-200/50 dark:hover:bg-slate-800/90 border border-border-subtle text-xs font-semibold text-text-main transition-colors duration-150 cursor-pointer shadow-sm active:scale-[0.98]"
        >
          <div class="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></div>
          <Bot class="w-3.5 h-3.5 text-brand-primary shrink-0" />
          <span class="max-w-[130px] xs:max-w-[160px] sm:max-w-[260px] truncate text-left">{{ currentModeLabel }}</span>
          <ChevronDown class="w-3.5 h-3.5 text-text-muted transition-transform duration-150 shrink-0" :class="{ 'rotate-180': isDropdownOpen }" />
        </button>

        <!-- Mode Selector Dropdown -->
        <div
          v-if="isDropdownOpen"
          @click="isDropdownOpen = false"
          class="absolute top-11 left-0 w-72 max-w-[calc(100vw-1.5rem)] glass-panel p-1.5 rounded-2xl border border-border-card shadow-2xl space-y-1 z-30"
        >
          <div
            v-for="mode in availableModes"
            :key="mode.id"
            @click="selectMode(mode.id)"
            class="p-2.5 rounded-xl text-xs flex items-start space-x-2.5 cursor-pointer transition-colors duration-150 active:bg-slate-200 dark:active:bg-slate-800"
            :class="chatStore.selectedMode === mode.id ? 'bg-slate-200/80 dark:bg-slate-800 text-text-main font-semibold border border-border-subtle' : 'text-text-secondary hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-900/60'"
          >
            <div class="p-1 rounded-lg bg-slate-200 dark:bg-slate-900 text-brand-primary shrink-0 mt-0.5">
              <component :is="mode.icon" class="w-3.5 h-3.5" />
            </div>
            <div class="flex-1 truncate">
              <div class="font-semibold text-text-main flex items-center justify-between">
                <span>{{ mode.title }}</span>
                <Check v-if="chatStore.selectedMode === mode.id" class="w-3.5 h-3.5 text-brand-primary" />
              </div>
              <div class="text-[10px] text-text-muted leading-tight mt-0.5">{{ mode.desc }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Center Session Natural Title -->
    <div class="hidden md:flex items-center space-x-2 text-xs text-text-secondary max-w-sm truncate">
      <span class="w-1.5 h-1.5 rounded-full bg-brand-primary"></span>
      <span class="truncate font-medium">{{ activeSessionTitle || '企业通用数字员工' }}</span>
    </div>

    <!-- Right Quick Actions: Theme Toggle, New Chat & User Avatar -->
    <div class="flex items-center space-x-2">
      <!-- Day / Night Dual Theme Toggle -->
      <button
        @click="toggleTheme"
        :title="isDark ? '切换至日间温润白模式' : '切换至夜间曜石灰模式'"
        class="w-8 h-8 rounded-xl glass-panel hover:bg-slate-200/50 dark:hover:bg-slate-800 border border-border-subtle flex items-center justify-center text-text-secondary hover:text-text-main transition-colors duration-150 cursor-pointer shadow-sm active:scale-95"
      >
        <Sun v-if="isDark" class="w-4 h-4 text-amber-400" />
        <Moon v-else class="w-4 h-4 text-slate-700" />
      </button>

      <!-- Quick New Session Button -->
      <button
        @click="chatStore.createSession()"
        title="新建对话"
        class="hidden sm:flex items-center space-x-1 px-2.5 py-1.5 rounded-xl glass-panel hover:bg-slate-200/50 dark:hover:bg-slate-800 border border-border-subtle text-xs text-text-secondary hover:text-text-main transition-colors duration-150 cursor-pointer"
      >
        <Plus class="w-3.5 h-3.5 text-brand-primary" />
        <span>新对话</span>
      </button>

      <!-- Dynamic Identity & Role Context Switcher -->
      <RoleSwitcherPopover />
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue';
import {
  Menu,
  Bot,
  ChevronDown,
  WifiOff,
  Plus,
  Check,
  Cpu,
  Layers,
  ShieldCheck,
  Sparkles,
  Sun,
  Moon
} from 'lucide-vue-next';
import { useChatStore } from '../../stores/chatStore';
import { usePreferencesStore } from '../../stores/preferencesStore';
import RoleSwitcherPopover from './RoleSwitcherPopover.vue';

const props = defineProps({
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
const isOnline = computed(() => chatStore.isOnline);
const isDark = computed(() => preferencesStore.isDark);

const toggleTheme = () => {
  preferencesStore.toggleTheme();
};

const availableModes = [
  {
    id: 'general',
    title: '企业通用助手',
    desc: '集成规章知识库检索、SOP 指引与多意图路由',
    icon: Sparkles,
  },
  {
    id: 'it',
    title: 'IT 运维数字员工',
    desc: '故障排查、网络诊断与 P1~P4 工单自动流转',
    icon: Cpu,
  },
  {
    id: 'finance',
    title: '财务与采购协同',
    desc: '大额采购预算比对、ERP 库存核验与审批门禁',
    icon: Layers,
  },
  {
    id: 'hr',
    title: '合规与人事顾问',
    desc: '考勤差旅、报销合规校验与离职交接协同',
    icon: ShieldCheck,
  },
];

const currentModeLabel = computed(() => {
  const m = availableModes.find((item) => item.id === chatStore.selectedMode);
  return m ? m.title : '企业通用助手';
});

const selectMode = (modeId) => {
  chatStore.selectedMode = modeId;
  isDropdownOpen.value = false;
};
</script>
