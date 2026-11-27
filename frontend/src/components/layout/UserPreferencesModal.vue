<template>
  <teleport to="body">
    <transition name="modal-backdrop">
      <div
        v-if="preferencesStore.isPreferencesOpen"
        class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/55 select-none"
        @click.self="preferencesStore.closePreferencesModal()"
      >
        <transition name="modal-panel" appear>
          <div
            class="origin-center w-full max-w-md rounded-xl bg-bg-card border border-border-card shadow-lg overflow-hidden"
            role="dialog"
            aria-modal="true"
            aria-label="显示偏好"
          >
            <!-- Header -->
            <div class="px-5 py-4 border-b border-border-subtle flex items-center justify-between">
              <div>
                <h2 class="text-sm font-semibold text-text-main">显示偏好</h2>
                <p class="text-[11px] text-text-muted mt-0.5">
                  {{ authStore.displayName }} · {{ authStore.department }} · {{ authStore.roleLabel }}
                </p>
              </div>

              <button
                type="button"
                @click="preferencesStore.closePreferencesModal()"
                title="关闭 (Esc)"
                class="btn-pressable w-8 h-8 rounded-lg flex items-center justify-center text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer"
              >
                <X class="w-4 h-4" />
              </button>
            </div>

            <!-- Body -->
            <div class="p-5 space-y-6 max-h-[75vh] overflow-y-auto">
              <!-- Theme -->
              <section class="space-y-2">
                <span class="text-xs font-medium text-text-main block">界面主题</span>
                <div class="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    @click="preferencesStore.setTheme('light')"
                    class="btn-pressable p-3 rounded-lg border text-left cursor-pointer flex items-center gap-2.5"
                    :class="
                      !preferencesStore.isDark
                        ? 'bg-bg-surface border-border-strong text-text-main'
                        : 'bg-bg-card border-border-subtle text-text-secondary hover:text-text-main hover:border-border-card'
                    "
                  >
                    <Sun class="w-4 h-4 shrink-0" />
                    <div class="min-w-0">
                      <div class="text-xs font-medium">日间模式</div>
                      <div class="text-[11px] text-text-muted">浅色高对比</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    @click="preferencesStore.setTheme('dark')"
                    class="btn-pressable p-3 rounded-lg border text-left cursor-pointer flex items-center gap-2.5"
                    :class="
                      preferencesStore.isDark
                        ? 'bg-bg-surface border-border-strong text-text-main'
                        : 'bg-bg-card border-border-subtle text-text-secondary hover:text-text-main hover:border-border-card'
                    "
                  >
                    <Moon class="w-4 h-4 shrink-0" />
                    <div class="min-w-0">
                      <div class="text-xs font-medium">夜间模式</div>
                      <div class="text-[11px] text-text-muted">曜石深色</div>
                    </div>
                  </button>
                </div>
              </section>

              <!-- Density -->
              <section class="space-y-2">
                <span class="text-xs font-medium text-text-main block">会话密度</span>
                <div class="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    @click="preferencesStore.setChatDensity('comfortable')"
                    class="btn-pressable p-3 rounded-lg border text-left cursor-pointer"
                    :class="
                      preferencesStore.chatDensity === 'comfortable'
                        ? 'bg-bg-surface border-border-strong text-text-main'
                        : 'bg-bg-card border-border-subtle text-text-secondary hover:text-text-main hover:border-border-card'
                    "
                  >
                    <div class="text-xs font-medium">舒适</div>
                    <div class="text-[11px] text-text-muted mt-0.5">标准留白间距</div>
                  </button>

                  <button
                    type="button"
                    @click="preferencesStore.setChatDensity('compact')"
                    class="btn-pressable p-3 rounded-lg border text-left cursor-pointer"
                    :class="
                      preferencesStore.chatDensity === 'compact'
                        ? 'bg-bg-surface border-border-strong text-text-main'
                        : 'bg-bg-card border-border-subtle text-text-secondary hover:text-text-main hover:border-border-card'
                    "
                  >
                    <div class="text-xs font-medium">紧凑</div>
                    <div class="text-[11px] text-text-muted mt-0.5">高信息密度</div>
                  </button>
                </div>
              </section>

              <!-- Auto Collapse -->
              <section class="p-3.5 rounded-lg bg-bg-surface border border-border-subtle flex items-center justify-between gap-3">
                <div class="min-w-0">
                  <div class="text-xs font-medium text-text-main">自动收起推理过程</div>
                  <div class="text-[11px] text-text-muted mt-0.5">生成完成后折叠检索步骤</div>
                </div>

                <button
                  type="button"
                  role="switch"
                  :aria-checked="preferencesStore.autoCollapseThought"
                  @click="preferencesStore.setAutoCollapseThought(!preferencesStore.autoCollapseThought)"
                  class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border border-transparent transition-colors duration-180 focus:outline-none"
                  :class="preferencesStore.autoCollapseThought ? 'bg-action-primary' : 'bg-border-strong'"
                >
                  <span
                    class="pointer-events-none inline-block h-4 w-4 rounded-full transition-transform duration-180 ease-snappy"
                    :class="[
                      preferencesStore.autoCollapseThought ? 'translate-x-4 bg-action-primary-fg' : 'translate-x-0 bg-bg-card'
                    ]"
                  ></span>
                </button>
              </section>

              <!-- Role-Layered Admin Shortcut -->
              <section
                v-if="authStore.isAdmin"
                class="p-3.5 rounded-lg bg-bg-surface border border-border-card flex items-center justify-between gap-3"
              >
                <div class="min-w-0">
                  <div class="text-xs font-medium text-text-main">管理员参数配置</div>
                  <div class="text-[11px] text-text-muted mt-0.5">模型路由、采样参数与检索阈值</div>
                </div>

                <button
                  type="button"
                  @click="goToAdminSettings"
                  class="btn-secondary px-3 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1 shrink-0 cursor-pointer"
                >
                  <span>前往配置</span>
                  <ArrowRight class="w-3.5 h-3.5" />
                </button>
              </section>
            </div>

            <!-- Footer -->
            <div class="px-5 py-3 border-t border-border-subtle flex justify-end">
              <button
                type="button"
                @click="preferencesStore.closePreferencesModal()"
                class="btn-primary px-4 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
              >
                完成
              </button>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { X, Sun, Moon, ArrowRight } from 'lucide-vue-next';
import { usePreferencesStore } from '../../stores/preferencesStore';
import { useAuthStore } from '../../stores/authStore';

const router = useRouter();
const preferencesStore = usePreferencesStore();
const authStore = useAuthStore();

const goToAdminSettings = () => {
  preferencesStore.closePreferencesModal();
  router.push('/admin/settings');
};

const handleKeydown = (e) => {
  if (e.key === 'Escape' && preferencesStore.isPreferencesOpen) {
    preferencesStore.closePreferencesModal();
  }
};

onMounted(() => {
  document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
});
</script>
