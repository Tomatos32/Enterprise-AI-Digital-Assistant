<template>
  <div
    class="my-3 rounded-2xl glass-card border transition-all duration-200 overflow-hidden shadow-xl"
    :class="cardBorderClass"
  >
    <!-- Card Header -->
    <div
      class="px-4 py-3 flex items-center justify-between border-b"
      :class="headerBorderClass"
    >
      <div class="flex items-center space-x-2.5">
        <div
          class="w-7 h-7 rounded-xl flex items-center justify-center shrink-0 shadow-sm"
          :class="headerIconBgClass"
        >
          <component :is="statusIcon" class="w-4 h-4" :class="headerIconColorClass" />
        </div>
        <div>
          <h4 class="text-xs sm:text-sm font-semibold text-text-main flex items-center space-x-2">
            <span>{{ displayData.title || '企业大额采购审批确认单' }}</span>
          </h4>
          <span class="text-[10px] text-text-muted flex items-center space-x-1 mt-0.5">
            <ShieldCheck class="w-3 h-3 text-brand-primary" />
            <span>合规风控门禁 · 财务核验通过</span>
          </span>
        </div>
      </div>

      <!-- Order ID Badge -->
      <div class="flex items-center space-x-1.5">
        <span class="font-mono text-[11px] px-2.5 py-1 rounded-lg bg-slate-900/90 text-amber-300 border border-amber-500/30 font-medium tracking-tight">
          {{ displayData.approval_id || displayData.id || 'PR-2026-0922' }}
        </span>
      </div>
    </div>

    <!-- Card Content / Specification Grid -->
    <div class="p-4 space-y-3">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
        <!-- Item Name -->
        <div class="bg-slate-900/80 p-3 rounded-xl border border-border-subtle flex flex-col justify-between">
          <span class="text-[11px] text-text-muted mb-1 flex items-center space-x-1">
            <span>申请物品品名</span>
          </span>
          <span class="font-medium text-slate-100 text-xs sm:text-sm truncate" :title="displayData.item_name">
            {{ displayData.item_name || 'MacBook Pro 16 (高配开发机)' }}
          </span>
        </div>

        <!-- Total Price (Amber-400 High Contrast) -->
        <div class="bg-slate-900/80 p-3 rounded-xl border border-amber-500/20 flex flex-col justify-between">
          <span class="text-[11px] text-amber-200/80 mb-1 flex items-center justify-between">
            <span>采购总金额</span>
            <span class="text-[10px] text-amber-400/90 font-sans">超 ￥5,000 需主管复核</span>
          </span>
          <span class="font-bold text-amber-400 font-mono text-base tracking-tight">
            ￥{{ formatCurrency(displayData.total_price || displayData.amount) }}
          </span>
        </div>

        <!-- Department & Applicant -->
        <div class="bg-slate-900/80 p-3 rounded-xl border border-border-subtle flex flex-col justify-between">
          <span class="text-[11px] text-text-muted mb-1">申请部门与负责人</span>
          <span class="text-text-main font-medium truncate">
            {{ displayData.department || '研发部 (AI 工程组)' }} · {{ displayData.applicant || '李工' }}
          </span>
        </div>

        <!-- Reason -->
        <div class="bg-slate-900/80 p-3 rounded-xl border border-border-subtle flex flex-col justify-between">
          <span class="text-[11px] text-text-muted mb-1">采购申请事由</span>
          <span class="text-text-secondary truncate block" :title="displayData.reason">
            {{ displayData.reason || '本地大模型量化调试与高并发端侧推理测试算力需求' }}
          </span>
        </div>
      </div>

      <!-- Policy Citation Pill -->
      <div class="px-3 py-2 rounded-xl bg-slate-900/60 border border-border-subtle text-[11px] text-text-secondary flex items-center justify-between">
        <span class="flex items-center space-x-1.5 truncate">
          <AlertCircle class="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span class="truncate">制度依据：{{ displayData.policy_ref || '《企业IT资产采购与固定资产管理制度》第三章第十二条' }}</span>
        </span>
        <span class="text-[10px] text-text-muted font-mono shrink-0 ml-2">已触发主管复核机制</span>
      </div>

      <!-- Action Section (Pending State) -->
      <div v-if="currentStatus === 'PENDING'" class="pt-2 space-y-3 border-t border-border-subtle">
        <!-- Comment Input -->
        <div class="relative">
          <input
            v-model="commentText"
            type="text"
            placeholder="填写审批批注意见（可选）..."
            class="w-full px-3.5 py-2 text-xs bg-slate-900/90 border border-border-subtle rounded-xl text-text-main placeholder-text-muted focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary/30 transition-colors duration-150"
            :disabled="isSubmitting"
          />
        </div>

        <!-- Primary Action Buttons -->
        <div class="flex items-center space-x-2.5">
          <!-- Emerald Approve Button -->
          <button
            @click="handleDecision('approve')"
            :disabled="isSubmitting"
            class="interactive-action flex-1 py-2 px-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-medium text-xs shadow-md shadow-emerald-600/20 hover:shadow-emerald-600/30 transition-colors duration-150 flex items-center justify-center space-x-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Check class="w-3.5 h-3.5 stroke-[2.5]" />
            <span>{{ isSubmitting && lastAction === 'approve' ? '正在提交...' : '同意并提交采购' }}</span>
          </button>

          <!-- Rose Reject Button -->
          <button
            @click="handleDecision('reject')"
            :disabled="isSubmitting"
            class="interactive-action py-2 px-3.5 rounded-xl bg-slate-900/90 hover:bg-rose-950/60 active:bg-rose-950 text-rose-400 hover:text-rose-300 border border-rose-500/30 hover:border-rose-500/50 font-medium text-xs transition-colors duration-150 flex items-center justify-center space-x-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X class="w-3.5 h-3.5 stroke-[2.5]" />
            <span>{{ isSubmitting && lastAction === 'reject' ? '正在驳回...' : '驳回申请' }}</span>
          </button>
        </div>
      </div>

      <!-- Finalized Result State (Approved or Rejected) -->
      <div
        v-else
        class="pt-2 border-t border-border-subtle"
      >
        <div
          class="p-3 rounded-xl flex items-center justify-between text-xs"
          :class="currentStatus === 'APPROVED' ? 'bg-emerald-950/40 border border-emerald-500/30 text-emerald-300' : 'bg-rose-950/40 border border-rose-500/30 text-rose-300'"
        >
          <div class="flex items-center space-x-2">
            <div
              class="w-5 h-5 rounded-full flex items-center justify-center"
              :class="currentStatus === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'"
            >
              <component :is="currentStatus === 'APPROVED' ? Check : X" class="w-3 h-3 stroke-[2.5]" />
            </div>
            <div>
              <span class="font-semibold">
                {{ currentStatus === 'APPROVED' ? '已批准并流转至 ERP 采购执行系统' : '已驳回采购申请' }}
              </span>
              <div class="text-[10px] opacity-80 mt-0.5 flex items-center space-x-1.5">
                <UserCheck class="w-3 h-3" />
                <span>审批人：{{ displayData.approver || '张经理 (研发主管)' }}</span>
                <span v-if="displayData.decision_time || finalizedTime">· {{ displayData.decision_time || finalizedTime }}</span>
              </div>
            </div>
          </div>

          <div v-if="displayComment" class="text-right text-[11px] max-w-[200px] truncate opacity-90">
            <span>批注: {{ displayComment }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import {
  FileCheck,
  Check,
  X,
  AlertCircle,
  ShieldCheck,
  UserCheck
} from 'lucide-vue-next';

const props = defineProps({
  approval: {
    type: Object,
    default: null
  },
  approvalData: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['decision', 'action']);

const commentText = ref('');
const isSubmitting = ref(false);
const lastAction = ref('');
const localStatus = ref(null);
const finalizedComment = ref('');
const finalizedTime = ref('');

const displayData = computed(() => {
  return props.approval || props.approvalData || {};
});

const currentStatus = computed(() => {
  if (localStatus.value) return localStatus.value;
  return displayData.value.status || 'PENDING';
});

const displayComment = computed(() => {
  return finalizedComment.value || displayData.value.comment || '';
});

const formatCurrency = (val) => {
  if (val === undefined || val === null || isNaN(Number(val))) return '22,999.00';
  return Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 2 });
};

const statusIcon = computed(() => {
  if (currentStatus.value === 'APPROVED') return Check;
  if (currentStatus.value === 'REJECTED') return X;
  return FileCheck;
});

const cardBorderClass = computed(() => {
  if (currentStatus.value === 'APPROVED') return 'border-emerald-500/30 bg-emerald-950/10';
  if (currentStatus.value === 'REJECTED') return 'border-rose-500/30 bg-rose-950/10';
  return 'border-amber-500/30 bg-amber-950/15';
});

const headerBorderClass = computed(() => {
  if (currentStatus.value === 'APPROVED') return 'border-emerald-500/20 bg-emerald-950/20';
  if (currentStatus.value === 'REJECTED') return 'border-rose-500/20 bg-rose-950/20';
  return 'border-amber-500/20 bg-amber-950/20';
});

const headerIconBgClass = computed(() => {
  if (currentStatus.value === 'APPROVED') return 'bg-emerald-500/20';
  if (currentStatus.value === 'REJECTED') return 'bg-rose-500/20';
  return 'bg-amber-500/20';
});

const headerIconColorClass = computed(() => {
  if (currentStatus.value === 'APPROVED') return 'text-emerald-400';
  if (currentStatus.value === 'REJECTED') return 'text-rose-400';
  return 'text-amber-400';
});

const handleDecision = async (action) => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  lastAction.value = action;

  const approvalId = displayData.value.approval_id || displayData.value.id || 'PR-2026-0922';
  const comment = commentText.value.trim();

  // Emits both events for backwards compatibility
  emit('decision', approvalId, action, comment);
  emit('action', approvalId, action, comment);

  localStatus.value = action.toUpperCase() === 'APPROVE' ? 'APPROVED' : 'REJECTED';
  finalizedComment.value = comment;
  finalizedTime.value = new Date().toLocaleTimeString('zh-CN');

  isSubmitting.value = false;
};
</script>
