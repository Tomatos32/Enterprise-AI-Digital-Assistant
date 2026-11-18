import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useAuthStore } from './authStore';
import { useChatStore } from './chatStore';

export const useApprovalStore = defineStore('approval', () => {
  const authStore = useAuthStore();
  const chatStore = useChatStore();

  const approvals = ref([]);
  const loading = ref(false);
  const error = ref(null);

  const pendingApprovals = computed(() =>
    approvals.value.filter((item) => item.status === 'PENDING')
  );

  const approvalHistory = computed(() =>
    approvals.value.filter((item) => item.status !== 'PENDING')
  );

  const pendingCount = computed(() => pendingApprovals.value.length);

  const syncSidebarBadge = () => {
    if (chatStore) {
      chatStore.pendingApprovalsCount = pendingCount.value;
    }
  };

  const mapApprovalItem = (item) => ({
    id: item.approval_id || item.id,
    approval_id: item.approval_id || item.id,
    thread_id: item.thread_id,
    title: item.title || '企业大额采购审批确认单',
    item_name: item.item_name,
    total_price: Number(item.total_price || item.amount || 0),
    amount: Number(item.total_price || item.amount || 0),
    quantity: item.quantity || 1,
    department: item.department || '业务部门',
    applicant: item.applicant || `${item.department || '业务部门'}申请人`,
    reason: item.reason || '业务必需物资采购',
    status: item.status || 'PENDING',
    approver: item.approver || '',
    comment: item.comment || '',
    created_at: item.created_at || new Date().toLocaleDateString('zh-CN'),
    policy_ref: item.policy_ref || '《企业IT资产采购与固定资产管理制度》第三章第十二条',
  });

  const fetchApprovals = async () => {
    if (!authStore.isAuthenticated || !authStore.canApprove) {
      approvals.value = [];
      error.value = null;
      syncSidebarBadge();
      return;
    }

    loading.value = true;
    error.value = null;
    try {
      const resp = await fetch('/api/v1/approval/list', {
        headers: authStore.getAuthHeaders(),
      });
      if (resp.status === 403) {
        approvals.value = [];
        error.value = '当前身份无权访问审批列表';
        syncSidebarBadge();
        return;
      }
      if (resp.status === 401) {
        authStore.handleUnauthorized();
        return;
      }
      if (resp.ok) {
        const json = await resp.json();
        if (json.data && Array.isArray(json.data)) {
          approvals.value = json.data.map(mapApprovalItem);
          syncSidebarBadge();
        }
      }
    } catch (err) {
      console.warn('[ApprovalStore] fetchApprovals failed:', err);
    } finally {
      loading.value = false;
    }
  };

  const fetchPendingApprovals = async () => {
    await fetchApprovals();
  };

  const initPresetData = async () => {
    await fetchApprovals();
  };

  const addPendingApproval = (data) => {
    if (!data) return;
    const approvalId = data.approval_id || data.id || `APR-${Date.now().toString().slice(-6)}`;
    const existing = approvals.value.find(
      (a) => a.approval_id === approvalId || a.id === approvalId
    );
    if (!existing) {
      approvals.value.unshift(
        mapApprovalItem({
          ...data,
          approval_id: approvalId,
          status: data.status || 'PENDING',
        })
      );
      syncSidebarBadge();
    }
  };

  const submitDecision = async (approvalId, action, comment = '') => {
    if (!authStore.canApprove) {
      const denyMsg = '当前身份为普通员工，无权执行审批决策';
      error.value = denyMsg;
      return { success: false, error: denyMsg };
    }

    loading.value = true;
    error.value = null;
    const normalizedAction = action.toLowerCase();
    const resolvedComment =
      comment.trim() ||
      (normalizedAction === 'approve' ? '同意采购申请' : '暂不满足采购条件');

    try {
      const resp = await fetch('/api/v1/approval/action', {
        method: 'POST',
        headers: authStore.getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          approval_id: approvalId,
          action: normalizedAction,
          comment: resolvedComment,
        }),
      });

      const data = await resp.json();
      if (!resp.ok || data.code >= 400) {
        const errMsg = data.message || data.detail || '审批决策提交失败';
        error.value = errMsg;
        return { success: false, error: errMsg };
      }

      const nextStatus = normalizedAction === 'approve' ? 'APPROVED' : 'REJECTED';
      const approverName = data.approver || authStore.approverSignature;

      const idx = approvals.value.findIndex(
        (a) => a.approval_id === approvalId || a.id === approvalId
      );
      if (idx !== -1) {
        approvals.value[idx] = {
          ...approvals.value[idx],
          status: nextStatus,
          comment: resolvedComment,
          approver: approverName,
          decision_time: new Date().toLocaleTimeString('zh-CN'),
        };
        syncSidebarBadge();
      }

      return {
        success: true,
        status: nextStatus,
        approver: approverName,
        graph_output: data.graph_output,
      };
    } catch (err) {
      console.error('[ApprovalStore] Action Error:', err);
      error.value = err.message || '审批决策提交失败';
      return { success: false, error: error.value };
    } finally {
      loading.value = false;
    }
  };

  const batchApproveAll = async (customComment = '') => {
    if (!authStore.canApprove) return;
    const targets = [...pendingApprovals.value];
    const commentText =
      customComment.trim() || `${authStore.displayName} (${authStore.roleLabel}) 批量同意核准`;
    for (const item of targets) {
      await submitDecision(item.approval_id || item.id, 'approve', commentText);
    }
  };

  const handleIdentityChange = async () => {
    approvals.value = [];
    error.value = null;
    syncSidebarBadge();
    if (authStore.isAuthenticated && authStore.canApprove) {
      await fetchApprovals();
    }
  };

  return {
    approvals,
    pendingApprovals,
    approvalHistory,
    pendingCount,
    loading,
    error,
    fetchApprovals,
    fetchPendingApprovals,
    initPresetData,
    addPendingApproval,
    submitDecision,
    batchApproveAll,
    syncSidebarBadge,
    handleIdentityChange,
  };
});
