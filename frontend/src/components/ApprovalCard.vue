<template>
  <div class="mt-3 p-4 rounded-xl glass-card border border-amber-500/30 bg-amber-950/20 shadow-lg transition-all duration-300">
    <!-- Card Header -->
    <div class="flex items-center justify-between pb-3 border-b border-amber-500/20">
      <div class="flex items-center space-x-2">
        <span class="p-1.5 rounded-lg bg-amber-500/20 text-amber-400">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </span>
        <h4 class="font-semibold text-amber-300 text-sm">人机协同审批拦截中心</h4>
      </div>
      <span class="px-2.5 py-0.5 text-xs font-medium rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
        {{ approvalData.approval_id || 'PENDING-APPROVAL' }}
      </span>
    </div>

    <!-- Purchase Item Info Grid -->
    <div class="grid grid-cols-2 gap-3 my-3 text-xs">
      <div class="bg-slate-900/50 p-2.5 rounded-lg border border-slate-800">
        <span class="text-slate-400 block mb-1">采购商品品名</span>
        <span class="font-semibold text-slate-100 text-sm">{{ approvalData.item_name || '大额硬件设备' }}</span>
      </div>
      <div class="bg-slate-900/50 p-2.5 rounded-lg border border-slate-800">
        <span class="text-slate-400 block mb-1">预估采购总金额</span>
        <span class="font-bold text-amber-400 text-sm">￥{{ formatCurrency(approvalData.total_price) }}</span>
      </div>
      <div class="bg-slate-900/50 p-2.5 rounded-lg border border-slate-800">
        <span class="text-slate-400 block mb-1">申请部门</span>
        <span class="text-slate-200">{{ approvalData.department || '研发部' }}</span>
      </div>
      <div class="bg-slate-900/50 p-2.5 rounded-lg border border-slate-800">
        <span class="text-slate-400 block mb-1">申请事由</span>
        <span class="text-slate-200 truncate block">{{ approvalData.reason || '硬件设施升级' }}</span>
      </div>
    </div>

    <!-- Warning Prompt -->
    <div class="p-2.5 mb-3 bg-amber-500/10 rounded-lg text-xs text-amber-200/90 leading-relaxed border border-amber-500/20">
      ⚠️ 触发门禁拦截：采购总金额超过 <strong class="text-amber-400">￥5,000.00</strong> 阈值，LangGraph 状态机已挂起，等待主管确认。
    </div>

    <!-- Actions (If Pending) -->
    <div v-if="approvalData.status === 'PENDING'" class="space-y-2">
      <input
        v-model="comment"
        type="text"
        placeholder="输入审批意见（可选）..."
        class="w-full px-3 py-1.5 text-xs bg-slate-900/80 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
      />
      <div class="flex items-center space-x-2 pt-1">
        <button
          @click="onAction('approve')"
          :disabled="loading"
          class="flex-1 py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium text-xs shadow-md hover:shadow-emerald-600/20 transition-all flex items-center justify-center space-x-1 cursor-pointer"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <span>同意采购 (Resume)</span>
        </button>
        <button
          @click="onAction('reject')"
          :disabled="loading"
          class="flex-1 py-2 px-3 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-medium text-xs shadow-md hover:shadow-rose-600/20 transition-all flex items-center justify-center space-x-1 cursor-pointer"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
          <span>拒绝请求</span>
        </button>
      </div>
    </div>

    <!-- Result Banner (If Approved or Rejected) -->
    <div v-else class="mt-2 p-2.5 rounded-lg text-xs font-semibold flex items-center justify-between"
      :class="approvalData.status === 'APPROVED' ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-500/30' : 'bg-rose-950/40 text-rose-300 border border-rose-500/30'"
    >
      <span>审批状态: {{ approvalData.status === 'APPROVED' ? '已批准 (APPROVED)' : '已拒绝 (REJECTED)' }}</span>
      <span v-if="approvalData.comment" class="text-slate-400 font-normal">意见: {{ approvalData.comment }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  approvalData: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['action']);

const comment = ref('');
const loading = ref(false);

const formatCurrency = (val) => {
  if (!val) return '0.00';
  return Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 2 });
};

const onAction = async (action) => {
  loading.value = true;
  await emit('action', props.approvalData.approval_id, action, comment.value);
  loading.value = false;
};
</script>
