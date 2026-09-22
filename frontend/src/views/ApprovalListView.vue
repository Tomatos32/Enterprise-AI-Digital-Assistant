<template>
  <div class="h-full flex-1 flex flex-col bg-bg-main overflow-y-auto select-none p-3 sm:p-6 lg:p-8 space-y-4 sm:space-y-6">
    <!-- Top Header -->
    <header class="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-border-subtle gap-4">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-status-approval shadow-sm shrink-0">
          <ClipboardList class="w-5 h-5" />
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-base sm:text-lg font-bold text-text-main">企业待办与协同审批中心</h1>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-status-approval border border-amber-500/30 font-mono">
              {{ approvalStore.pendingCount }} 项待办
            </span>
          </div>
          <p class="text-xs text-text-secondary mt-0.5">
            集中处理企业数字员工与人机协同流程中的大额采购、特批申请及业务单据审批
          </p>
        </div>
      </div>

      <!-- Quick Action Back to Chat -->
      <div class="flex items-center space-x-2.5">
        <router-link
          to="/"
          class="interactive-action px-3.5 py-1.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-xs text-text-secondary hover:text-text-main border border-border-subtle flex items-center space-x-1.5 transition-colors duration-150 cursor-pointer shadow-sm"
        >
          <MessageSquare class="w-3.5 h-3.5 text-brand-primary" />
          <span>返回对话工作台</span>
        </router-link>

        <button
          v-if="approvalStore.pendingCount > 0"
          @click="handleBatchApprove"
          :disabled="isBatchProcessing"
          class="interactive-action px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs text-white font-medium shadow-md shadow-emerald-600/20 flex items-center space-x-1.5 transition-colors duration-150 cursor-pointer disabled:opacity-50"
        >
          <CheckCheck class="w-3.5 h-3.5" />
          <span>{{ isBatchProcessing ? '正在批量处理...' : '一键批量同意' }}</span>
        </button>
      </div>
    </header>

    <!-- Stats Summary Cards -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <!-- 待处理 -->
      <div class="p-3.5 rounded-2xl glass-card border border-amber-500/20 bg-amber-950/10 shadow-sm flex items-center justify-between">
        <div>
          <span class="text-[11px] text-text-muted block">待我审批</span>
          <span class="text-xl font-bold font-mono text-amber-400 mt-1 block">
            {{ approvalStore.pendingCount }}
          </span>
        </div>
        <div class="w-8 h-8 rounded-xl bg-amber-500/20 flex items-center justify-center text-amber-400">
          <Clock class="w-4 h-4" />
        </div>
      </div>

      <!-- 已批准 -->
      <div class="p-3.5 rounded-2xl glass-card border border-emerald-500/20 bg-emerald-950/10 shadow-sm flex items-center justify-between">
        <div>
          <span class="text-[11px] text-text-muted block">已核准单据</span>
          <span class="text-xl font-bold font-mono text-emerald-400 mt-1 block">
            {{ approvedCount }}
          </span>
        </div>
        <div class="w-8 h-8 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-400">
          <CheckCircle2 class="w-4 h-4" />
        </div>
      </div>

      <!-- 已驳回 -->
      <div class="p-3.5 rounded-2xl glass-card border border-rose-500/20 bg-rose-950/10 shadow-sm flex items-center justify-between">
        <div>
          <span class="text-[11px] text-text-muted block">已驳回申请</span>
          <span class="text-xl font-bold font-mono text-rose-400 mt-1 block">
            {{ rejectedCount }}
          </span>
        </div>
        <div class="w-8 h-8 rounded-xl bg-rose-500/20 flex items-center justify-center text-rose-400">
          <XCircle class="w-4 h-4" />
        </div>
      </div>

      <!-- 履约合规率 -->
      <div class="p-3.5 rounded-2xl glass-card border border-border-subtle bg-slate-900/60 shadow-sm flex items-center justify-between">
        <div>
          <span class="text-[11px] text-text-muted block">合规审批响应率</span>
          <span class="text-xl font-bold font-mono text-cyan-400 mt-1 block">100%</span>
        </div>
        <div class="w-8 h-8 rounded-xl bg-cyan-500/20 flex items-center justify-center text-cyan-400">
          <ShieldCheck class="w-4 h-4" />
        </div>
      </div>
    </div>

    <!-- Filters & Search Toolbar -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/60 p-2.5 rounded-2xl border border-border-subtle">
      <!-- Status Tabs -->
      <div class="flex items-center space-x-1 overflow-x-auto">
        <button
          v-for="tab in statusTabs"
          :key="tab.key"
          @click="activeStatusTab = tab.key"
          class="interactive-action px-3 py-1.5 rounded-xl text-xs font-medium transition-colors duration-150 cursor-pointer shrink-0 flex items-center space-x-1.5"
          :class="activeStatusTab === tab.key ? 'bg-slate-800 text-text-main shadow-sm border border-border-card' : 'text-text-secondary hover:text-text-main hover:bg-slate-800/50'"
        >
          <span>{{ tab.label }}</span>
          <span
            v-if="tab.count !== undefined"
            class="px-1.5 py-0.2 rounded-full text-[10px] font-mono"
            :class="activeStatusTab === tab.key ? 'bg-slate-700 text-text-main' : 'bg-slate-900 text-text-muted'"
          >
            {{ tab.count }}
          </span>
        </button>
      </div>

      <!-- Right Search & Department Filter -->
      <div class="flex items-center space-x-2">
        <!-- Department Selector -->
        <select
          v-model="selectedDepartment"
          class="bg-slate-900/90 border border-border-subtle text-text-secondary text-xs rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-brand-primary"
        >
          <option value="ALL">全部申请部门</option>
          <option value="研发部">研发部</option>
          <option value="行政后勤部">行政后勤部</option>
          <option value="财务部">财务部</option>
          <option value="市场营销部">市场营销部</option>
        </select>

        <!-- Search Input -->
        <div class="relative w-44 sm:w-56">
          <Search class="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索单号、品名或申请人..."
            class="w-full pl-8 pr-3 py-1.5 bg-slate-900/90 border border-border-subtle text-text-main placeholder-text-muted text-xs rounded-xl focus:outline-none focus:border-brand-primary transition-colors duration-150"
          />
        </div>
      </div>
    </div>

    <!-- Approvals List Section -->
    <div class="space-y-4">
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
        class="py-16 px-4 rounded-3xl glass-card border border-border-subtle flex flex-col items-center justify-center text-center space-y-3"
      >
        <div class="w-12 h-12 rounded-2xl bg-slate-900/90 border border-border-subtle flex items-center justify-center text-emerald-400 shadow-sm">
          <CheckCircle2 class="w-6 h-6" />
        </div>
        <h3 class="text-sm font-semibold text-text-main">当前暂无匹配的审批单据</h3>
        <p class="text-xs text-text-muted max-w-sm leading-relaxed">
          {{ searchQuery ? '未查询到符合关键词的单据，请尝试更换搜索条件。' : '当前所有协同采购流程均已高效闭环或暂无待处理项。' }}
        </p>
        <router-link
          to="/"
          class="mt-2 interactive-action px-4 py-2 rounded-xl bg-brand-primary/10 hover:bg-brand-primary/20 text-brand-primary border border-brand-primary/30 text-xs font-medium transition-colors duration-150 cursor-pointer"
        >
          返回对话工作台
        </router-link>
      </div>
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
  CheckCheck
} from 'lucide-vue-next';
import { useApprovalStore } from '../stores/approvalStore';
import ApprovalCard from '../components/chat/ApprovalCard.vue';

const approvalStore = useApprovalStore();

const activeStatusTab = ref('ALL');
const selectedDepartment = ref('ALL');
const searchQuery = ref('');
const isBatchProcessing = ref(false);

onMounted(() => {
  approvalStore.fetchPendingApprovals();
});

const allApprovals = computed(() => {
  return [...approvalStore.pendingApprovals, ...approvalStore.approvalHistory];
});

const approvedCount = computed(() => {
  return approvalStore.approvalHistory.filter(a => a.status === 'APPROVED').length;
});

const rejectedCount = computed(() => {
  return approvalStore.approvalHistory.filter(a => a.status === 'REJECTED').length;
});

const statusTabs = computed(() => [
  { key: 'ALL', label: '全部单据', count: allApprovals.value.length },
  { key: 'PENDING', label: '待我处理', count: approvalStore.pendingCount },
  { key: 'APPROVED', label: '已通过', count: approvedCount.value },
  { key: 'REJECTED', label: '已驳回', count: rejectedCount.value },
]);

const filteredApprovals = computed(() => {
  return allApprovals.value.filter(item => {
    // 状态过滤
    if (activeStatusTab.value !== 'ALL') {
      const itemStatus = item.status || 'PENDING';
      if (itemStatus !== activeStatusTab.value) return false;
    }

    // 部门过滤
    if (selectedDepartment.value !== 'ALL') {
      if (!item.department || !item.department.includes(selectedDepartment.value)) {
        return false;
      }
    }

    // 关键词搜索
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase();
      const matchId = (item.id || item.approval_id || '').toLowerCase().includes(q);
      const matchItem = (item.item_name || '').toLowerCase().includes(q);
      const matchDept = (item.department || '').toLowerCase().includes(q);
      const matchReason = (item.reason || '').toLowerCase().includes(q);
      const matchApplicant = (item.applicant || '').toLowerCase().includes(q);
      return matchId || matchItem || matchDept || matchReason || matchApplicant;
    }

    return true;
  });
});

const handleSingleDecision = async (approvalId, action, comment) => {
  await approvalStore.submitDecision(approvalId, action, comment);
};

const handleBatchApprove = async () => {
  if (isBatchProcessing.value || approvalStore.pendingApprovals.length === 0) return;
  isBatchProcessing.value = true;
  try {
    const pendings = [...approvalStore.pendingApprovals];
    for (const item of pendings) {
      const id = item.approval_id || item.id;
      await approvalStore.submitDecision(id, 'approve', '主管批量快速核准通过');
    }
  } catch (err) {
    console.error('Batch approve error:', err);
  } finally {
    isBatchProcessing.value = false;
  }
};
</script>
