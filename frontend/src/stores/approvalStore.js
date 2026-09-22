import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useChatStore } from './chatStore';

export const useApprovalStore = defineStore('approval', () => {
  const chatStore = useChatStore();

  const pendingApprovals = ref([
    {
      id: 'APR-2026-0922-01',
      approval_id: 'APR-2026-0922-01',
      title: '大额研发设备采购审批确认单',
      item_name: 'MacBook Pro 16 (M3 Max / 64G / 1TB)',
      total_price: 22999.0,
      amount: 22999.0,
      quantity: 1,
      department: '研发部 (AI 工程组)',
      applicant: '李工 (高级算法工程师)',
      reason: '本地大模型量化调试与高并发端侧推理测试算力需求',
      status: 'PENDING',
      created_at: new Date().toLocaleDateString('zh-CN'),
      policy_ref: '《企业IT资产采购与固定资产管理制度》第三章第十二条',
    }
  ]);

  const approvalHistory = ref([]);
  const loading = ref(false);
  const error = ref(null);

  const pendingCount = computed(() => pendingApprovals.value.length);

  // 同步侧边栏徽标数量
  const syncSidebarBadge = () => {
    if (chatStore) {
      chatStore.pendingApprovalsCount = pendingCount.value;
    }
  };

  syncSidebarBadge();

  const fetchPendingApprovals = async () => {
    try {
      const resp = await fetch('/api/v1/approval/pending');
      if (resp.ok) {
        const json = await resp.json();
        if (json.data && Array.isArray(json.data) && json.data.length > 0) {
          pendingApprovals.value = json.data.map(item => ({
            id: item.approval_id,
            approval_id: item.approval_id,
            thread_id: item.thread_id,
            title: '企业大额采购审批确认单',
            item_name: item.item_name,
            total_price: Number(item.total_price),
            amount: Number(item.total_price),
            quantity: item.quantity,
            department: item.department,
            applicant: '李工 (研发部申请人)',
            reason: item.reason,
            status: item.status || 'PENDING',
            created_at: item.created_at,
            policy_ref: '《企业IT资产采购与固定资产管理制度》第三章第十二条',
          }));
          syncSidebarBadge();
        }
      }
    } catch (err) {
      // 离线/开发环境保持初始兜底单据
      console.warn('[ApprovalStore] fetchPendingApprovals fallback:', err);
    }
  };

  const addPendingApproval = (data) => {
    if (!data) return;
    const approvalId = data.approval_id || data.id || `APR-${Date.now().toString().slice(-6)}`;
    const existing = pendingApprovals.value.find(a => (a.approval_id === approvalId || a.id === approvalId));
    if (!existing) {
      const newApproval = {
        id: approvalId,
        approval_id: approvalId,
        title: data.title || '企业大额采购审批确认单',
        item_name: data.item_name || '企业办公与研发物资',
        total_price: Number(data.total_price || data.amount || 0),
        amount: Number(data.total_price || data.amount || 0),
        quantity: data.quantity || 1,
        department: data.department || '业务部门',
        applicant: data.applicant || '申请人',
        reason: data.reason || '业务必需物资采购',
        status: data.status || 'PENDING',
        created_at: new Date().toLocaleDateString('zh-CN'),
        policy_ref: data.policy_ref || '《企业固定资产管理制度》',
      };
      pendingApprovals.value.unshift(newApproval);
      syncSidebarBadge();
    }
  };

  const submitDecision = async (approvalId, action, comment = '') => {
    loading.value = true;
    error.value = null;

    try {
      const resp = await fetch('/api/v1/approval/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approval_id: approvalId,
          action,
          comment: comment.trim() || (action.toLowerCase() === 'approve' ? '同意采购申请' : '暂不满足采购条件')
        })
      });

      const data = await resp.json();

      // 本地状态跃迁
      const idx = pendingApprovals.value.findIndex(a => (a.approval_id === approvalId || a.id === approvalId));
      if (idx !== -1) {
        const item = pendingApprovals.value[idx];
        item.status = action.toUpperCase() === 'APPROVE' ? 'APPROVED' : 'REJECTED';
        item.comment = comment.trim();
        item.approver = '张经理 (研发部审批人)';
        item.decision_time = new Date().toLocaleTimeString('zh-CN');

        // 移入历史记录
        approvalHistory.value.unshift({ ...item });
        pendingApprovals.value.splice(idx, 1);
        syncSidebarBadge();
      }

      return {
        success: true,
        status: action.toUpperCase() === 'APPROVE' ? 'APPROVED' : 'REJECTED',
        graph_output: data.graph_output
      };
    } catch (err) {
      console.error('[ApprovalStore] Action Error:', err);
      error.value = err.message || '审批决策提交失败';
      return { success: false, error: error.value };
    } finally {
      loading.value = false;
    }
  };

  return {
    pendingApprovals,
    approvalHistory,
    pendingCount,
    loading,
    error,
    fetchPendingApprovals,
    addPendingApproval,
    submitDecision,
    syncSidebarBadge,
  };
});
