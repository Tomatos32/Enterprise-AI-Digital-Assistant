<template>
  <div class="h-full flex-1 flex flex-col bg-bg-main overflow-y-auto select-none p-4 sm:p-6 lg:p-8 transition-colors duration-180">
    <div class="max-w-5xl w-full mx-auto space-y-6 pb-8">
      <!-- Top Header -->
      <header class="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-border-subtle gap-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-bg-surface border border-border-card flex items-center justify-center text-text-main shrink-0">
            <ClipboardList class="w-5 h-5" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-base sm:text-lg font-semibold text-text-main tracking-tight">审批工作台</h1>
              <span class="px-2 py-0.5 rounded-md text-[11px] font-medium bg-bg-surface text-text-secondary border border-border-subtle tabular-nums">
                {{ approvalStore.pendingCount }} 项待办
              </span>
            </div>
            <p class="text-xs text-text-muted mt-0.5">
              集中处理大额采购及业务单据审批
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <router-link
            to="/"
            class="btn-secondary px-3 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer"
          >
            <MessageSquare class="w-3.5 h-3.5 text-text-secondary" />
            <span>返回对话</span>
          </router-link>

          <button
            v-if="approvalStore.pendingCount > 0"
            type="button"
            @click="handleBatchApprove"
            :disabled="isBatchProcessing"
            class="btn-primary px-3.5 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <CheckCheck class="w-3.5 h-3.5" />
            <span>{{ isBatchProcessing ? '处理中...' : '批量同意' }}</span>
          </button>
        </div>
      </header>

      <!-- Stats Summary Cards -->
      <section class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="p-4 rounded-xl bg-bg-card border border-border-card flex items-center justify-between">
          <div>
            <div class="flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-status-approval"></span>
              <span class="text-[11px] text-text-muted">待我审批</span>
            </div>
            <span class="text-2xl font-semibold font-mono tabular-nums text-text-main mt-1.5 block">
              {{ approvalStore.pendingCount }}
            </span>
          </div>
          <Clock class="w-4 h-4 text-text-muted shrink-0" />
        </div>

        <div class="p-4 rounded-xl bg-bg-card border border-border-card flex items-center justify-between">
          <div>
            <div class="flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-status-success"></span>
              <span class="text-[11px] text-text-muted">已核准</span>
            </div>
            <span class="text-2xl font-semibold font-mono tabular-nums text-text-main mt-1.5 block">
              {{ approvedCount }}
            </span>
          </div>
          <CheckCircle2 class="w-4 h-4 text-text-muted shrink-0" />
        </div>

        <div class="p-4 rounded-xl bg-bg-card border border-border-card flex items-center justify-between">
          <div>
            <div class="flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-status-danger"></span>
              <span class="text-[11px] text-text-muted">已驳回</span>
            </div>
            <span class="text-2xl font-semibold font-mono tabular-nums text-text-main mt-1.5 block">
              {{ rejectedCount }}
            </span>
          </div>
          <XCircle class="w-4 h-4 text-text-muted shrink-0" />
        </div>

        <div class="p-4 rounded-xl bg-bg-card border border-border-card flex items-center justify-between">
          <div>
            <span class="text-[11px] text-text-muted block">合规响应率</span>
            <span class="text-2xl font-semibold font-mono tabular-nums text-text-main mt-1.5 block">
              100%
            </span>
          </div>
          <ShieldCheck class="w-4 h-4 text-text-muted shrink-0" />
        </div>
      </section>

      <!-- Filters & Search Toolbar -->
      <section class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-bg-card p-2 rounded-xl border border-border-card">
        <!-- Status Tabs -->
        <div class="flex items-center gap-1 overflow-x-auto bg-bg-surface p-0.5 rounded-lg border border-border-subtle">
          <button
            v-for="tab in statusTabs"
            :key="tab.key"
            type="button"
            @click="activeStatusTab = tab.key"
            class="btn-pressable px-3 py-1.5 rounded-md text-xs font-medium cursor-pointer shrink-0 flex items-center gap-1.5 border"
            :class="
              activeStatusTab === tab.key
                ? 'bg-bg-card text-text-main border-border-card font-semibold'
                : 'border-transparent text-text-secondary hover:text-text-main'
            "
          >
            <span>{{ tab.label }}</span>
            <span
              v-if="tab.count !== undefined"
              class="text-[10px] font-mono tabular-nums text-text-muted"
            >
              {{ tab.count }}
            </span>
          </button>
        </div>

        <!-- Right Search & Department Filter -->
        <div class="flex items-center gap-2">
          <select
            v-model="selectedDepartment"
            class="bg-bg-input border border-border-card text-text-secondary text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-border-focus transition-colors duration-150"
          >
            <option value="ALL">全部部门</option>
            <option v-for="dept in departmentOptions" :key="dept" :value="dept">
              {{ dept }}
            </option>
          </select>

          <div class="relative w-44 sm:w-56">
            <Search class="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索单号、品名或申请人..."
              class="w-full pl-8 pr-3 py-1.5 bg-bg-input border border-border-card text-text-main placeholder-text-muted text-xs rounded-lg focus:outline-none focus:border-border-focus transition-colors duration-150"
            />
          </div>
        </div>
      </section>

      <!-- Error Feedback Banner -->
      <transition name="banner-slide">
        <div
          v-if="approvalStore.error"
          role="alert"
          class="px-4 py-2.5 rounded-xl bg-bg-surface border border-status-danger/40 text-status-danger text-xs flex items-center justify-between gap-3"
        >
          <div class="flex items-center gap-2">
            <span class="w-1.5 h-1.5 rounded-full bg-status-danger shrink-0"></span>
            <span>{{ approvalStore.error }}</span>
          </div>
          <button
            type="button"
            @click="approvalStore.error = null"
            class="text-text-secondary hover:text-text-main cursor-pointer"
          >
            关闭
          </button>
        </div>
      </transition>

      <!-- Approvals List Section -->
      <section class="space-y-4">
        <div v-if="filteredApprovals.length > 0" class="space-y-3">
          <div
            v-for="item in filteredApprovals"
            :key="item.id || item.approval_id"
            class="max-w-4xl"
          >
            <ApprovalCard
              :approval="item"
              :approvalData="item"
              @decision="handleSingleDecision"
            />
          </div>
        </div>

        <!-- Empty State -->
        <div
          v-else
          class="py-16 px-4 rounded-xl bg-bg-card border border-border-subtle flex flex-col items-center justify-center text-center gap-3"
        >
          <div class="w-11 h-11 rounded-xl bg-bg-surface border border-border-subtle flex items-center justify-center text-text-secondary">
            <CheckCircle2 class="w-5 h-5" />
          </div>
          <h3 class="text-sm font-semibold text-text-main">暂无匹配的审批单据</h3>
          <p class="text-xs text-text-muted max-w-sm">
            {{ searchQuery ? '未查询到符合条件的单据，请调整筛选条件。' : '当前无待处理审批项。' }}
          </p>
          <router-link
            to="/"
            class="mt-1 btn-secondary px-4 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
          >
            返回对话工作台
          </router-link>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import {
  ClipboardList,
  Clock,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Search,
  MessageSquare,
  CheckCheck,
} from 'lucide-vue-next';
import { useApprovalStore } from '../stores/approvalStore';
import { useAuthStore } from '../stores/authStore';
import ApprovalCard from '../components/chat/ApprovalCard.vue';

const approvalStore = useApprovalStore();
const authStore = useAuthStore();

const activeStatusTab = ref('PENDING');
const selectedDepartment = ref('ALL');
const searchQuery = ref('');
const isBatchProcessing = ref(false);

const departmentOptions = computed(() => {
  const defaults = ['采购管理部', '人力资源部', 'IT 系统管理部', '研发部', '财务部', '行政后勤部'];
  const dynamicDepts = approvalStore.approvals
    .map((item) => item.department)
    .filter(Boolean);
  return Array.from(new Set([...defaults, ...dynamicDepts]));
});

onMounted(async () => {
  await approvalStore.fetchApprovals();
});

const approvedCount = computed(() => {
  return approvalStore.approvals.filter((a) => a.status === 'APPROVED').length;
});

const rejectedCount = computed(() => {
  return approvalStore.approvals.filter((a) => a.status === 'REJECTED').length;
});

const statusTabs = computed(() => [
  { key: 'PENDING', label: '待审批', count: approvalStore.pendingCount },
  { key: 'APPROVED', label: '已核准', count: approvedCount.value },
  { key: 'REJECTED', label: '已驳回', count: rejectedCount.value },
  { key: 'ALL', label: '全部', count: approvalStore.approvals.length },
]);

const filteredApprovals = computed(() => {
  return approvalStore.approvals.filter((item) => {
    if (activeStatusTab.value !== 'ALL' && item.status !== activeStatusTab.value) {
      return false;
    }

    if (selectedDepartment.value !== 'ALL' && item.department !== selectedDepartment.value) {
      return false;
    }

    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase();
      const matchId = (item.id || item.approval_id || '').toLowerCase().includes(q);
      const matchItem = (item.item_name || '').toLowerCase().includes(q);
      const matchApplicant = (item.applicant || '').toLowerCase().includes(q);
      const matchReason = (item.reason || '').toLowerCase().includes(q);
      return matchId || matchItem || matchApplicant || matchReason;
    }

    return true;
  });
});

const handleSingleDecision = async (approvalId, decision, reason) => {
  await approvalStore.submitDecision(approvalId, decision, reason);
};

const handleBatchApprove = async () => {
  isBatchProcessing.value = true;
  await approvalStore.batchApproveAll(`${authStore.displayName} (${authStore.roleLabel}) 批量同意核准`);
  isBatchProcessing.value = false;
};
</script>
