<template>
  <teleport to="body">
    <!-- Backdrop & Off-Canvas Drawer Root -->
    <div
      v-show="modelValue || isAnimating"
      class="fixed inset-0 z-50 select-none overflow-hidden"
    >
      <!-- Dark Frosted Backdrop -->
      <transition
        enter-active-class="transition-opacity duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-200 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
        @before-enter="isAnimating = true"
        @after-leave="isAnimating = false"
      >
        <div
          v-if="modelValue"
          @click="closeDrawer"
          class="fixed inset-0 bg-black/70 backdrop-blur-sm"
          aria-hidden="true"
        ></div>
      </transition>

      <!-- Off-Canvas Drawer Panel -->
      <transition
        enter-active-class="transition-transform duration-200 ease-out"
        enter-from-class="-translate-x-full"
        enter-to-class="translate-x-0"
        leave-active-class="transition-transform duration-200 ease-in"
        leave-from-class="translate-x-0"
        leave-to-class="-translate-x-full"
      >
        <aside
          v-if="modelValue"
          class="fixed inset-y-0 left-0 w-72 max-w-[85vw] bg-bg-sidebar border-r border-border-card shadow-2xl flex flex-col justify-between z-10"
          style="padding-bottom: env(safe-area-inset-bottom, 12px); padding-top: env(safe-area-inset-top, 0px);"
        >
          <!-- Top Header: Brand & Close Button -->
          <div class="p-3.5 flex items-center justify-between border-b border-border-subtle/80 shrink-0">
            <div class="flex items-center space-x-2.5 overflow-hidden">
              <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center shadow-md shadow-blue-500/20 shrink-0">
                <Sparkles class="w-4 h-4 text-white" />
              </div>
              <div class="truncate">
                <h2 class="text-sm font-bold text-text-main leading-tight truncate">企业数字员工</h2>
                <p class="text-[10px] text-text-muted leading-tight">AI Copilot 移动端</p>
              </div>
            </div>

            <!-- Close Drawer Button (44x44px touch target) -->
            <button
              @click="closeDrawer"
              title="关闭导航抽屉"
              class="w-11 h-11 -mr-2 rounded-xl flex items-center justify-center text-text-secondary hover:text-text-main hover:bg-slate-800/80 transition-colors duration-150 cursor-pointer"
            >
              <X class="w-5 h-5" />
            </button>
          </div>

          <!-- [+ 新建对话] Action Section -->
          <div class="p-3 shrink-0">
            <button
              @click="handleNewChat"
              class="w-full h-11 px-3.5 rounded-xl bg-brand-primary/10 hover:bg-brand-primary/20 text-brand-primary border border-brand-primary/30 flex items-center justify-center space-x-2 text-xs font-semibold shadow-sm transition-all duration-150 cursor-pointer group active:scale-[0.98]"
            >
              <Plus class="w-4 h-4 transition-transform duration-150 group-hover:rotate-90" />
              <span>新建对话</span>
            </button>
          </div>

          <!-- Middle: Scrollable Sessions History List -->
          <div class="flex-1 overflow-y-auto px-2.5 py-1 space-y-3 overscroll-contain">
            <!-- Group: 今天 -->
            <div v-if="chatStore.todaySessions.length > 0">
              <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">今天</div>
              <div class="space-y-1">
                <div
                  v-for="s in chatStore.todaySessions"
                  :key="s.id"
                  @click="handleSelect(s.id)"
                  class="group px-3 py-2.5 min-h-[44px] rounded-xl text-xs flex items-center justify-between cursor-pointer transition-colors duration-150"
                  :class="s.id === chatStore.activeSessionId ? 'bg-slate-800 text-text-main font-medium border border-border-card shadow-sm' : 'text-text-secondary hover:text-text-main hover:bg-slate-900/60'"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <MessageSquare class="w-4 h-4 shrink-0 text-brand-primary/80" />
                    <span class="truncate">{{ s.title }}</span>
                  </div>
                  <button
                    @click.stop="chatStore.deleteSession(s.id)"
                    title="删除会话"
                    class="p-2 text-text-muted hover:text-status-danger rounded transition-colors duration-150"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Group: 昨天 -->
            <div v-if="chatStore.yesterdaySessions.length > 0">
              <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">昨天</div>
              <div class="space-y-1">
                <div
                  v-for="s in chatStore.yesterdaySessions"
                  :key="s.id"
                  @click="handleSelect(s.id)"
                  class="group px-3 py-2.5 min-h-[44px] rounded-xl text-xs flex items-center justify-between cursor-pointer transition-colors duration-150"
                  :class="s.id === chatStore.activeSessionId ? 'bg-slate-800 text-text-main font-medium border border-border-card shadow-sm' : 'text-text-secondary hover:text-text-main hover:bg-slate-900/60'"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <MessageSquare class="w-4 h-4 shrink-0 text-brand-primary/80" />
                    <span class="truncate">{{ s.title }}</span>
                  </div>
                  <button
                    @click.stop="chatStore.deleteSession(s.id)"
                    title="删除会话"
                    class="p-2 text-text-muted hover:text-status-danger rounded transition-colors duration-150"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Group: 前 7 天 -->
            <div v-if="chatStore.previous7DaysSessions.length > 0">
              <div class="px-2 py-1 text-[11px] font-semibold text-text-muted tracking-wider">前 7 天</div>
              <div class="space-y-1">
                <div
                  v-for="s in chatStore.previous7DaysSessions"
                  :key="s.id"
                  @click="handleSelect(s.id)"
                  class="group px-3 py-2.5 min-h-[44px] rounded-xl text-xs flex items-center justify-between cursor-pointer transition-colors duration-150"
                  :class="s.id === chatStore.activeSessionId ? 'bg-slate-800 text-text-main font-medium border border-border-card shadow-sm' : 'text-text-secondary hover:text-text-main hover:bg-slate-900/60'"
                >
                  <div class="flex items-center space-x-2.5 truncate">
                    <MessageSquare class="w-4 h-4 shrink-0 text-brand-primary/80" />
                    <span class="truncate">{{ s.title }}</span>
                  </div>
                  <button
                    @click.stop="chatStore.deleteSession(s.id)"
                    title="删除会话"
                    class="p-2 text-text-muted hover:text-status-danger rounded transition-colors duration-150"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Lower: Business Workspaces Navigation -->
          <div class="p-3 border-t border-border-subtle bg-slate-950/60 shrink-0">
            <div class="px-1 pb-1.5 text-[11px] font-semibold text-text-muted tracking-wider">
              企业业务协同
            </div>

            <nav class="space-y-1.5">
              <!-- 待我审批入口 -->
              <router-link
                to="/approvals"
                @click="closeDrawer"
                class="flex items-center justify-between p-2.5 min-h-[44px] rounded-xl text-xs transition-colors duration-150 cursor-pointer active:bg-slate-800"
                active-class="bg-slate-800 text-status-approval font-medium"
              >
                <div class="flex items-center space-x-2.5 truncate">
                  <ClipboardList class="w-4 h-4 text-status-approval shrink-0" />
                  <span class="text-text-secondary hover:text-text-main truncate">待我审批中心</span>
                </div>
                <div class="flex items-center space-x-1.5">
                  <span
                    v-if="pendingApprovalsCount > 0"
                    class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-status-approval border border-amber-500/30 font-mono"
                  >
                    {{ pendingApprovalsCount }} 项
                  </span>
                  <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
                </div>
              </router-link>

              <!-- 规章制度知识库入口 -->
              <router-link
                to="/knowledge"
                @click="closeDrawer"
                class="flex items-center justify-between p-2.5 min-h-[44px] rounded-xl text-xs transition-colors duration-150 cursor-pointer active:bg-slate-800"
                active-class="bg-slate-800 text-brand-primary font-medium"
              >
                <div class="flex items-center space-x-2.5 truncate">
                  <BookOpen class="w-4 h-4 text-brand-primary shrink-0" />
                  <span class="text-text-secondary hover:text-text-main truncate">规章制度知识库</span>
                </div>
                <ChevronRight class="w-3.5 h-3.5 text-text-muted" />
              </router-link>
            </nav>
          </div>

          <!-- Bottom: User Profile Card -->
          <div class="p-3 border-t border-border-subtle bg-slate-950/80 flex items-center justify-between shrink-0">
            <div class="flex items-center space-x-2.5 overflow-hidden">
              <div class="w-9 h-9 rounded-full bg-slate-800 border border-border-card flex items-center justify-center text-text-secondary shrink-0">
                <User class="w-4 h-4 text-slate-300" />
              </div>
              <div class="truncate">
                <div class="text-xs font-semibold text-text-main truncate">张经理</div>
                <div class="text-[10px] text-text-muted truncate">研发部 · 业务审批人</div>
              </div>
            </div>

            <button
              title="设置"
              class="w-10 h-10 rounded-xl flex items-center justify-center text-text-muted hover:text-text-main hover:bg-slate-800 transition-colors duration-150 cursor-pointer"
            >
              <Settings class="w-4 h-4" />
            </button>
          </div>
        </aside>
      </transition>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue';
import {
  X,
  Plus,
  MessageSquare,
  Trash2,
  ClipboardList,
  BookOpen,
  User,
  Settings,
  Sparkles,
  ChevronRight
} from 'lucide-vue-next';
import { useChatStore } from '../../stores/chatStore';
import { useApprovalStore } from '../../stores/approvalStore';
import { useRouter } from 'vue-router';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['update:modelValue', 'newSession', 'selectSession']);

const chatStore = useChatStore();
const approvalStore = useApprovalStore();
const router = useRouter();

const isAnimating = ref(false);

const pendingApprovalsCount = computed(() => {
  return approvalStore.pendingCount !== undefined ? approvalStore.pendingCount : chatStore.pendingApprovalsCount;
});

const closeDrawer = () => {
  emit('update:modelValue', false);
};

const handleNewChat = () => {
  const session = chatStore.createSession();
  emit('newSession', session);
  if (router.currentRoute.value.path !== '/') {
    router.push('/');
  }
  closeDrawer();
};

const handleSelect = (id) => {
  chatStore.switchSession(id);
  emit('selectSession', id);
  if (router.currentRoute.value.path !== '/') {
    router.push('/');
  }
  closeDrawer();
};

// 抽屉展开时锁住背景滚动，防止穿透
watch(
  () => props.modelValue,
  (isOpen) => {
    if (typeof document !== 'undefined') {
      if (isOpen) {
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = '';
      }
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  if (typeof document !== 'undefined') {
    document.body.style.overflow = '';
  }
});
</script>
