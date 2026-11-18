<template>
  <div class="h-full flex-1 flex flex-col bg-bg-main overflow-y-auto p-4 sm:p-8 transition-colors duration-200">
    <div class="max-w-4xl w-full mx-auto space-y-6">
      <!-- Header -->
      <header class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-border-subtle">
        <div class="flex items-center space-x-3">
          <div class="w-11 h-11 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0 shadow-sm">
            <component :is="slotMeta.icon" class="w-5 h-5" />
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h1 class="text-base sm:text-lg font-bold text-text-main">{{ slotMeta.title }}</h1>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
                管理员专属域
              </span>
            </div>
            <p class="text-xs text-text-secondary mt-0.5">{{ slotMeta.subtitle }}</p>
          </div>
        </div>

        <router-link
          to="/"
          class="interactive-action px-3.5 py-2 rounded-xl glass-panel hover:bg-slate-200/60 dark:hover:bg-slate-800 text-xs text-text-secondary hover:text-text-main border border-border-subtle flex items-center space-x-1.5 transition-colors duration-150 self-start sm:self-auto"
        >
          <MessageSquare class="w-3.5 h-3.5 text-brand-primary" />
          <span>返回对话工作台</span>
        </router-link>
      </header>

      <!-- Access Guard Verified Card -->
      <div class="rounded-3xl glass-card border border-border-card p-6 sm:p-8 space-y-5 shadow-lg">
        <div class="flex items-start space-x-3">
          <div class="w-9 h-9 rounded-xl bg-brand-primary/10 border border-brand-primary/30 flex items-center justify-center text-brand-primary shrink-0">
            <ShieldCheck class="w-5 h-5" />
          </div>
          <div class="space-y-1">
            <h2 class="text-sm sm:text-base font-bold text-text-main">管理员控制域权限校验已生效</h2>
            <p class="text-xs sm:text-sm text-text-secondary leading-relaxed">
              当前已通过系统管理员身份（{{ authStore.displayName }} · {{ authStore.department }}）进入「{{ slotMeta.title }}」专属工作区。普通员工与部门主管访问该管理功能时将被权限校验自动拦截。
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div class="p-4 rounded-2xl bg-slate-100/80 dark:bg-slate-900/70 border border-border-subtle space-y-1">
            <span class="text-[11px] text-text-muted">当前访问身份</span>
            <div class="text-xs font-bold text-text-main">{{ authStore.displayName }}</div>
            <div class="text-[11px] text-emerald-600 dark:text-emerald-400">{{ authStore.roleLabel }}</div>
          </div>

          <div class="p-4 rounded-2xl bg-slate-100/80 dark:bg-slate-900/70 border border-border-subtle space-y-1">
            <span class="text-[11px] text-text-muted">所属部门</span>
            <div class="text-xs font-bold text-text-main">{{ authStore.department }}</div>
            <div class="text-[11px] text-text-secondary">控制面隔离域</div>
          </div>

          <div class="p-4 rounded-2xl bg-slate-100/80 dark:bg-slate-900/70 border border-border-subtle space-y-1">
            <span class="text-[11px] text-text-muted">模块建设状态</span>
            <div class="text-xs font-bold text-text-main">控制区入口已就绪</div>
            <div class="text-[11px] text-text-secondary">核心治理能力将随管理员专题迭代逐步开放</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import {
  SlidersHorizontal,
  ListTodo,
  Activity,
  ShieldCheck,
  MessageSquare,
} from 'lucide-vue-next';
import { useAuthStore } from '../stores/authStore';

const route = useRoute();
const authStore = useAuthStore();

const SLOT_CONFIG = {
  settings: {
    title: '系统配置与模型管理',
    subtitle: '统筹大模型参数配置、检索阈值治理与系统运行策略',
    icon: SlidersHorizontal,
  },
  tasks: {
    title: '异步任务调度中心',
    subtitle: '统一管理企业知识库文档入库解析与后台异步批处理队列',
    icon: ListTodo,
  },
  monitoring: {
    title: '系统遥测与审计监控',
    subtitle: '实时洞察链路健康状态、响应延时指标与异常审计轨迹',
    icon: Activity,
  },
};

const slotMeta = computed(() => {
  const key = route.meta?.adminSlot || 'settings';
  return SLOT_CONFIG[key] || SLOT_CONFIG.settings;
});
</script>
