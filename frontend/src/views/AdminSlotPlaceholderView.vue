<template>
  <div class="h-full flex-1 flex flex-col bg-bg-main overflow-y-auto p-4 sm:p-8 transition-colors duration-180">
    <div class="max-w-4xl w-full mx-auto space-y-6">
      <!-- Header -->
      <header class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-border-subtle">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-bg-surface border border-border-card flex items-center justify-center text-text-main shrink-0">
            <component :is="slotMeta.icon" class="w-5 h-5" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-base sm:text-lg font-semibold text-text-main tracking-tight">{{ slotMeta.title }}</h1>
              <span class="px-2 py-0.5 rounded-md text-[10px] font-medium bg-bg-surface text-text-secondary border border-border-subtle">
                管理员专属
              </span>
            </div>
            <p class="text-xs text-text-muted mt-0.5">{{ slotMeta.subtitle }}</p>
          </div>
        </div>

        <router-link
          to="/"
          class="btn-secondary px-3 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
        >
          <MessageSquare class="w-3.5 h-3.5 text-text-secondary" />
          <span>返回对话</span>
        </router-link>
      </header>

      <!-- Access Guard Verified Card -->
      <section class="rounded-xl bg-bg-card border border-border-card p-6 sm:p-8 space-y-5">
        <div class="flex items-start gap-3">
          <div class="w-9 h-9 rounded-lg bg-bg-surface border border-border-subtle flex items-center justify-center text-text-main shrink-0">
            <ShieldCheck class="w-4 h-4" />
          </div>
          <div class="space-y-1">
            <h2 class="text-sm sm:text-base font-semibold text-text-main">管理员权限校验已通过</h2>
            <p class="text-xs sm:text-sm text-text-secondary leading-relaxed">
              当前已以系统管理员身份（{{ authStore.displayName }} · {{ authStore.department }}）进入「{{ slotMeta.title }}」。
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div class="p-4 rounded-lg bg-bg-surface border border-border-subtle space-y-1">
            <span class="text-[11px] text-text-muted">当前访问身份</span>
            <div class="text-xs font-semibold text-text-main">{{ authStore.displayName }}</div>
            <div class="text-[11px] text-text-secondary">{{ authStore.roleLabel }}</div>
          </div>

          <div class="p-4 rounded-lg bg-bg-surface border border-border-subtle space-y-1">
            <span class="text-[11px] text-text-muted">所属部门</span>
            <div class="text-xs font-semibold text-text-main">{{ authStore.department }}</div>
            <div class="text-[11px] text-text-muted">管理控制域</div>
          </div>

          <div class="p-4 rounded-lg bg-bg-surface border border-border-subtle space-y-1">
            <span class="text-[11px] text-text-muted">模块状态</span>
            <div class="text-xs font-semibold text-text-main">控制区入口已就绪</div>
            <div class="text-[11px] text-text-muted">按迭代规划开放</div>
          </div>
        </div>
      </section>
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
    subtitle: '管理模型推理参数、检索阈值与运行策略',
    icon: SlidersHorizontal,
  },
  tasks: {
    title: '异步任务调度中心',
    subtitle: '管理知识库文档解析与后台异步队列',
    icon: ListTodo,
  },
  monitoring: {
    title: '系统遥测与审计监控',
    subtitle: '追踪服务健康度、响应延迟与工单履约状态',
    icon: Activity,
  },
};

const slotMeta = computed(() => {
  const key = route.meta?.adminSlot || 'settings';
  return SLOT_CONFIG[key] || SLOT_CONFIG.settings;
});
</script>
