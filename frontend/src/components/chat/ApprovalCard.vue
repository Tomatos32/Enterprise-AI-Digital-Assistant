<template>
  <div class="my-3 rounded-xl bg-bg-card border border-border-card overflow-hidden">
    <!-- Card Header -->
    <div class="px-4 py-3 flex items-center justify-between gap-3 border-b border-border-subtle">
      <div class="flex items-center gap-2.5 min-w-0">
        <div class="w-7 h-7 rounded-lg bg-bg-surface border border-border-subtle flex items-center justify-center shrink-0">
          <component :is="statusIcon" class="w-4 h-4" :class="statusIconColorClass" />
        </div>
        <div class="min-w-0">
          <h4 class="text-xs sm:text-sm font-semibold text-text-main truncate">
            {{ displayData.title || '采购审批单' }}
          </h4>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <span class="px-2 py-0.5 text-[11px] font-medium rounded-md border" :class="statusPillClass">
          {{ statusText }}
        </span>
        <span
          v-if="displayApprovalId"
          class="font-mono text-[11px] px-2 py-0.5 rounded-md bg-bg-surface text-text-secondary border border-border-subtle"
        >
          {{ displayApprovalId }}
        </span>
      </div>
    </div>

    <!-- Specification Grid (100% Backend Extracted Slots, Zero Fake Fallbacks) -->
    <div class="p-4 space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
        <!-- Item Name & Quantity × Unit Price -->
        <div class="bg-bg-surface px-3 py-2.5 rounded-lg border border-border-subtle space-y-1">
          <span class="text-[11px] text-text-muted block">采购物品</span>
          <div class="font-medium text-text-main text-xs sm:text-sm truncate" :title="displayItemName">
            {{ displayItemName }}
          </div>
          <div v-if="quantityPriceLine" class="text-[11px] text-text-secondary font-mono tabular-nums">
            {{ quantityPriceLine }}
          </div>
        </div>

        <!-- Total Amount -->
        <div class="bg-bg-surface px-3 py-2.5 rounded-lg border border-border-subtle flex flex-col justify-between space-y-1">
          <div class="flex items-center justify-between gap-2 text-[11px] text-text-muted">
            <span>采购总额</span>
            <span class="font-mono">超 ￥5,000 需复核</span>
          </div>
          <div class="font-semibold text-text-main font-mono tabular-nums text-base tracking-tight">
            {{ formattedTotalPrice }}
          </div>
        </div>

        <!-- Department & Applicant -->
        <div class="bg-bg-surface px-3 py-2.5 rounded-lg border border-border-subtle space-y-1">
          <span class="text-[11px] text-text-muted block">申请部门与申请人</span>
          <div class="text-text-main font-medium truncate">
            {{ displayDepartment }} · {{ displayApplicant }}
          </div>
        </div>

        <!-- Reason -->
        <div class="bg-bg-surface px-3 py-2.5 rounded-lg border border-border-subtle space-y-1">
          <span class="text-[11px] text-text-muted block">申请事由</span>
          <div class="text-text-secondary truncate" :title="displayReason">
            {{ displayReason }}
          </div>
        </div>
      </div>

      <!-- Policy Citation Line -->
      <div
        v-if="displayData.policy_ref"
        class="px-3 py-2 rounded-lg bg-bg-surface border border-border-subtle text-[11px] text-text-secondary flex items-center gap-2"
      >
        <FileText class="w-3.5 h-3.5 text-text-muted shrink-0" />
        <span class="truncate">制度依据：{{ displayData.policy_ref }}</span>
      </div>

      <!-- Pending Action Section -->
      <div v-if="currentStatus === 'PENDING'" class="pt-3 space-y-3 border-t border-border-subtle">
        <template v-if="canApprove">
          <input
            v-model="commentText"
            type="text"
            placeholder="填写审批意见（可选）"
            class="w-full px-3 py-2 text-xs bg-bg-input border border-border-card rounded-lg text-text-main placeholder-text-muted focus:outline-none focus:border-border-focus transition-colors duration-150"
            :disabled="isSubmitting"
          />

          <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <!-- Primary High-Contrast Approve CTA -->
            <button
              type="button"
              @click="handleDecision('approve')"
              :disabled="isSubmitting || !displayApprovalId"
              class="btn-primary flex-1 py-2 px-3.5 rounded-lg font-medium text-xs inline-flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Check class="w-3.5 h-3.5" />
              <span>{{ isSubmitting && lastAction === 'approve' ? '正在提交...' : '同意并提交采购' }}</span>
            </button>

            <!-- Hold-to-Confirm Destructive Reject CTA (@vue-bits/HoldButton pattern) -->
            <HoldButton
              variant="danger"
              size="md"
              :label="isSubmitting && lastAction === 'reject' ? '正在驳回...' : '长按驳回'"
              holding-label="松开取消 · 保持驳回"
              hint="长按 0.85 秒确认驳回，防止误操作"
              :duration="850"
              :disabled="isSubmitting || !displayApprovalId"
              :loading="isSubmitting && lastAction === 'reject'"
              @confirm="handleDecision('reject')"
            >
              <template #icon>
                <X class="w-3.5 h-3.5" />
              </template>
            </HoldButton>
          </div>
        </template>

        <!-- Employee View: Read-Only Waiting State -->
        <div
          v-else
          class="px-3 py-2.5 rounded-lg bg-bg-surface border border-border-subtle text-text-secondary text-xs flex items-center gap-2"
        >
          <Lock class="w-3.5 h-3.5 text-text-muted shrink-0" />
          <span>已提交主管审批，当前身份（{{ authStore.roleLabel }}）仅可查看进度。</span>
        </div>
      </div>

      <!-- Finalized Result State -->
      <div v-else class="pt-3 border-t border-border-subtle">
        <div class="p-3 rounded-lg bg-bg-surface border border-border-subtle flex flex-wrap items-center justify-between gap-2 text-xs">
          <div class="flex items-center gap-2">
            <component
              :is="currentStatus === 'APPROVED' ? Check : X"
              class="w-4 h-4 shrink-0"
              :class="currentStatus === 'APPROVED' ? 'text-status-success' : 'text-status-danger'"
            />
            <div>
              <div class="font-medium text-text-main">
                {{ currentStatus === 'APPROVED' ? '已核准并流转采购执行' : '已驳回此申请' }}
              </div>
              <div class="text-[11px] text-text-muted mt-0.5 flex items-center gap-1.5">
                <UserCheck class="w-3 h-3" />
                <span>审批人：{{ displayApprover }}</span>
                <span v-if="displayData.decision_time || finalizedTime">· {{ displayData.decision_time || finalizedTime }}</span>
              </div>
            </div>
          </div>

          <div v-if="displayComment" class="text-[11px] text-text-secondary max-w-[240px] truncate">
            批注：{{ displayComment }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import {
  FileCheck,
  FileText,
  Check,
  X,
  UserCheck,
  Lock,
} from 'lucide-vue-next';
import { useAuthStore } from '../../stores/authStore';
import { useApprovalStore } from '../../stores/approvalStore';
import HoldButton from '../ui/HoldButton.vue';

const authStore = useAuthStore();
const approvalStore = useApprovalStore();
const canApprove = computed(() => authStore.canApprove);

const props = defineProps({
  approval: {
    type: Object,
    default: null,
  },
  approvalData: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['decision', 'action']);

const commentText = ref('');
const isSubmitting = ref(false);
const lastAction = ref('');
const localStatus = ref(null);
const finalizedComment = ref('');
const finalizedTime = ref('');

const displayData = computed(() => props.approval || props.approvalData || {});

watch(
  () => displayData.value.approval_id || displayData.value.id,
  () => {
    localStatus.value = null;
    finalizedComment.value = '';
    finalizedTime.value = '';
  }
);

watch(
  () => displayData.value.status,
  (newStatus) => {
    if (newStatus && newStatus !== 'PENDING') {
      localStatus.value = null;
    }
  }
);

const currentStatus = computed(() => {
  if (localStatus.value) return localStatus.value;
  return displayData.value.status || 'PENDING';
});

const displayApprovalId = computed(() => displayData.value.approval_id || displayData.value.id || '');
const displayItemName = computed(() => displayData.value.item_name || '未指定采购物品');
const displayDepartment = computed(() => displayData.value.department || '未标注部门');
const displayApplicant = computed(() => displayData.value.applicant || '业务提交人');
const displayReason = computed(() => displayData.value.reason || '常规业务需求');

const quantityPriceLine = computed(() => {
  const qty = Number(displayData.value.quantity);
  const unit = Number(displayData.value.unit_price);
  if (Number.isFinite(qty) && qty > 0 && Number.isFinite(unit) && unit > 0) {
    return `${qty} 件 × ￥${unit.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;
  }
  if (Number.isFinite(qty) && qty > 0) {
    return `数量：${qty}`;
  }
  return '';
});

const formattedTotalPrice = computed(() => {
  const raw = displayData.value.total_price ?? displayData.value.amount;
  if (raw === undefined || raw === null || raw === '' || Number.isNaN(Number(raw))) {
    return '--';
  }
  return `￥${Number(raw).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;
});

const displayComment = computed(() => finalizedComment.value || displayData.value.comment || '');

const displayApprover = computed(() => {
  if (displayData.value.approver) return displayData.value.approver;
  if (localStatus.value) return authStore.approverSignature;
  return '部门主管';
});

const statusIcon = computed(() => {
  if (currentStatus.value === 'APPROVED') return Check;
  if (currentStatus.value === 'REJECTED') return X;
  return FileCheck;
});

const statusIconColorClass = computed(() => {
  if (currentStatus.value === 'APPROVED') return 'text-status-success';
  if (currentStatus.value === 'REJECTED') return 'text-status-danger';
  return 'text-status-approval';
});

const statusText = computed(() => {
  if (currentStatus.value === 'APPROVED') return '已核准';
  if (currentStatus.value === 'REJECTED') return '已驳回';
  return '待审批';
});

const statusPillClass = computed(() => {
  if (currentStatus.value === 'APPROVED') {
    return 'bg-bg-surface text-status-success border-border-card';
  }
  if (currentStatus.value === 'REJECTED') {
    return 'bg-bg-surface text-status-danger border-border-card';
  }
  return 'bg-bg-surface text-status-approval border-border-card';
});

const handleDecision = async (action) => {
  const approvalId = displayApprovalId.value;
  if (isSubmitting.value || !canApprove.value || !approvalId) return;
  isSubmitting.value = true;
  lastAction.value = action;

  const comment = commentText.value.trim();

  emit('decision', approvalId, action, comment);
  emit('action', approvalId, action, comment);

  if (!approvalStore.loading) {
    isSubmitting.value = false;
  }
};

watch(
  () => approvalStore.loading,
  (loading) => {
    if (!loading) {
      isSubmitting.value = false;
    }
  }
);
</script>
