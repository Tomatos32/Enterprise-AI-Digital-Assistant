<template>
  <teleport to="body">
    <transition
      enter-active-class="transition-opacity duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="preferencesStore.isPreferencesOpen"
        class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm select-none"
        @click.self="preferencesStore.closePreferencesModal()"
      >
        <div
          class="w-full max-w-lg rounded-3xl bg-bg-card border border-border-card shadow-2xl overflow-hidden transition-all"
          role="dialog"
          aria-modal="true"
          aria-label="个人外观与显示偏好"
        >
          <!-- Modal Header -->
          <div class="px-5 py-4 border-b border-border-subtle flex items-center justify-between bg-slate-100/70 dark:bg-slate-900/60">
            <div class="flex items-center space-x-2.5">
              <div class="w-9 h-9 rounded-xl bg-brand-primary/15 border border-brand-primary/30 flex items-center justify-center text-brand-primary shrink-0">
                <SlidersHorizontal class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-sm font-bold text-text-main">个人外观与显示偏好</h2>
                <p class="text-[11px] text-text-muted">
                  {{ authStore.displayName }} · {{ authStore.department }} · {{ authStore.roleLabel }}
                </p>
              </div>
            </div>

            <button
              type="button"
              @click="preferencesStore.closePreferencesModal()"
              title="关闭弹窗"
              class="w-8 h-8 rounded-xl flex items-center justify-center text-text-secondary hover:text-text-main hover:bg-slate-200/70 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- Modal Body -->
          <div class="p-5 space-y-5 max-h-[75vh] overflow-y-auto">
            <!-- Theme Selection -->
            <section class="space-y-2.5">
              <div class="flex items-center justify-between">
                <span class="text-xs font-semibold text-text-main flex items-center space-x-1.5">
                  <Sun class="w-3.5 h-3.5 text-amber-500" />
                  <span>界面主题外观</span>
                </span>
                <span class="text-[11px] text-text-muted">日夜双主题实时切换</span>
              </div>

              <div class="grid grid-cols-2 gap-2.5">
                <button
                  type="button"
                  @click="preferencesStore.setTheme('light')"
                  class="p-3 rounded-2xl border text-left transition-all cursor-pointer flex items-center space-x-3"
                  :class="
                    !preferencesStore.isDark
                      ? 'bg-brand-primary/10 border-brand-primary/50 text-text-main shadow-sm'
                      : 'bg-slate-100/70 dark:bg-slate-900/60 border-border-subtle text-text-secondary hover:text-text-main'
                  "
                >
                  <div class="w-8 h-8 rounded-xl bg-amber-500/15 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
                    <Sun class="w-4 h-4" />
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="text-xs font-semibold truncate">日间温润白</div>
                    <div class="text-[10px] text-text-muted truncate">象牙纸感 · 高对比阅读</div>
                  </div>
                </button>

                <button
                  type="button"
                  @click="preferencesStore.setTheme('dark')"
                  class="p-3 rounded-2xl border text-left transition-all cursor-pointer flex items-center space-x-3"
                  :class="
                    preferencesStore.isDark
                      ? 'bg-brand-primary/10 border-brand-primary/50 text-text-main shadow-sm'
                      : 'bg-slate-100/70 dark:bg-slate-900/60 border-border-subtle text-text-secondary hover:text-text-main'
                  "
                >
                  <div class="w-8 h-8 rounded-xl bg-blue-500/15 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                    <Moon class="w-4 h-4" />
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="text-xs font-semibold truncate">夜间曜石灰</div>
                    <div class="text-[10px] text-text-muted truncate">深邃护眼 · 沉浸终端</div>
                  </div>
                </button>
              </div>
            </section>

            <!-- Chat Display Density -->
            <section class="space-y-2.5">
              <div class="flex items-center justify-between">
                <span class="text-xs font-semibold text-text-main flex items-center space-x-1.5">
                  <LayoutGrid class="w-3.5 h-3.5 text-brand-primary" />
                  <span>会话排版密度</span>
                </span>
                <span class="text-[11px] text-text-muted">仅影响个人工作台视图</span>
              </div>

              <div class="grid grid-cols-2 gap-2.5">
                <button
                  type="button"
                  @click="preferencesStore.setChatDensity('comfortable')"
                  class="p-3 rounded-2xl border text-left transition-all cursor-pointer"
                  :class="
                    preferencesStore.chatDensity === 'comfortable'
                      ? 'bg-brand-primary/10 border-brand-primary/50 text-text-main shadow-sm'
                      : 'bg-slate-100/70 dark:bg-slate-900/60 border-border-subtle text-text-secondary hover:text-text-main'
                  "
                >
                  <div class="text-xs font-semibold">舒适留白</div>
                  <div class="text-[10px] text-text-muted mt-0.5">更宽裕的气泡间距与长文可读性</div>
                </button>

                <button
                  type="button"
                  @click="preferencesStore.setChatDensity('compact')"
                  class="p-3 rounded-2xl border text-left transition-all cursor-pointer"
                  :class="
                    preferencesStore.chatDensity === 'compact'
                      ? 'bg-brand-primary/10 border-brand-primary/50 text-text-main shadow-sm'
                      : 'bg-slate-100/70 dark:bg-slate-900/60 border-border-subtle text-text-secondary hover:text-text-main'
                  "
                >
                  <div class="text-xs font-semibold">紧凑高效</div>
                  <div class="text-[10px] text-text-muted mt-0.5">同屏展示更多对话轮次与审批单</div>
                </button>
              </div>
            </section>

            <!-- Thought Trace Collapse Preference -->
            <section class="p-3.5 rounded-2xl bg-slate-100/70 dark:bg-slate-900/60 border border-border-subtle flex items-center justify-between gap-3">
              <div class="flex items-start space-x-2.5 min-w-0">
                <Sparkles class="w-4 h-4 text-brand-primary shrink-0 mt-0.5" />
                <div>
                  <div class="text-xs font-semibold text-text-main">思考完成自动收起推理过程</div>
                  <div class="text-[11px] text-text-muted mt-0.5">
                    开启后，AI 生成完正文将自动折叠检索步骤与推理链详情，保持对话清爽
                  </div>
                </div>
              </div>

              <button
                type="button"
                role="switch"
                :aria-checked="preferencesStore.autoCollapseThought"
                @click="preferencesStore.setAutoCollapseThought(!preferencesStore.autoCollapseThought)"
                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none"
                :class="preferencesStore.autoCollapseThought ? 'bg-brand-primary' : 'bg-slate-300 dark:bg-slate-700'"
              >
                <span
                  class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                  :class="preferencesStore.autoCollapseThought ? 'translate-x-5' : 'translate-x-0'"
                ></span>
              </button>
            </section>

            <!-- Role-Layered Boundary Card -->
            <section
              v-if="authStore.isAdmin"
              class="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between gap-3"
            >
              <div class="flex items-start space-x-2.5 min-w-0">
                <ShieldCheck class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div class="text-xs font-bold text-text-main">管理员高级模型与节点配置</div>
                  <div class="text-[11px] text-text-secondary mt-0.5">
                    您具备系统管理员权限，可前往控制中心调配推理模式、采样参数与知识检索策略。
                  </div>
                </div>
              </div>

              <button
                type="button"
                @click="goToAdminSettings"
                class="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center space-x-1 shrink-0 transition-colors cursor-pointer"
              >
                <span>前往配置</span>
                <ArrowRight class="w-3.5 h-3.5" />
              </button>
            </section>

            <section
              v-else
              class="p-3 rounded-2xl bg-slate-100/60 dark:bg-slate-900/50 border border-border-subtle flex items-start space-x-2.5"
            >
              <Shield class="w-4 h-4 text-text-muted shrink-0 mt-0.5" />
              <p class="text-[11px] text-text-secondary leading-relaxed">
                底层大模型推理参数、检索阈值与系统级行为指令由系统管理员统一治理，此处仅保存您的个人界面偏好。
              </p>
            </section>
          </div>

          <!-- Modal Footer -->
          <div class="px-5 py-3 border-t border-border-subtle bg-slate-100/50 dark:bg-slate-900/40 flex justify-end">
            <button
              type="button"
              @click="preferencesStore.closePreferencesModal()"
              class="px-4 py-1.5 rounded-xl bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              完成
            </button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { useRouter } from 'vue-router';
import {
  SlidersHorizontal,
  X,
  Sun,
  Moon,
  LayoutGrid,
  Sparkles,
  ShieldCheck,
  Shield,
  ArrowRight,
} from 'lucide-vue-next';
import { usePreferencesStore } from '../../stores/preferencesStore';
import { useAuthStore } from '../../stores/authStore';

const router = useRouter();
const preferencesStore = usePreferencesStore();
const authStore = useAuthStore();

const goToAdminSettings = () => {
  preferencesStore.closePreferencesModal();
  router.push('/admin/settings');
};
</script>
