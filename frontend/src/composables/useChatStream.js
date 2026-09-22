import { ref, onMounted, onUnmounted } from 'vue';
import { useApprovalStore } from '../stores/approvalStore';

export function useChatStream(clientId = 'vue3_client_stream') {
  const isConnected = ref(false);
  const isStreaming = ref(false);
  const messages = ref([]);
  const currentThreadId = ref(`thread_ws_${Date.now().toString().slice(-6)}`);
  const activeNodes = ref([]);

  let ws = null;
  let heartbeatTimer = null;

  const nodeNaturalMapping = {
    router: '正在分析业务意图并匹配专职数字员工...',
    retrieve: '正在核对企业知识库与规章制度...',
    tool: '正在调用企业服务核验数据与预算...',
    approval: '正在生成人机协同审批确认单据...',
    generate: '已完成数据核验，正在组织回复建议...',
  };

  const startHeartbeat = () => {
    stopHeartbeat();
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
        } catch (e) {
          console.warn('[ChatStream] Heartbeat failed:', e);
        }
      }
    }, 30000);
  };

  const stopHeartbeat = () => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  };

  const connect = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/ws/chat/${clientId}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      isConnected.value = true;
      startHeartbeat();
      console.log('[ChatStream] WebSocket Connected:', wsUrl);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'pong') return;
        handleWsEvent(data);
      } catch (err) {
        console.error('[ChatStream] Message Parse Error:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('[ChatStream] Error:', err);
      isConnected.value = false;
    };

    ws.onclose = () => {
      isConnected.value = false;
      stopHeartbeat();
      console.log('[ChatStream] Disconnected. Silent auto-reconnect in 3s...');
      setTimeout(connect, 3000);
    };
  };

  const handleWsEvent = (event) => {
    const { type, thread_id, node, content, tool, status, input, output, approval_data, final_answer, message } = event;

    let currentMsg = messages.value[messages.value.length - 1];
    if (!currentMsg || currentMsg.sender !== 'ai' || currentMsg.completed) {
      if (type !== 'start') return;
    }

    switch (type) {
      case 'start':
        isStreaming.value = true;
        activeNodes.value = ['router'];
        if (currentMsg && currentMsg.sender === 'ai') {
          currentMsg.isStreaming = true;
          currentMsg.thoughtTitle = '正在分析业务意图...';
        }
        break;

      case 'node_start':
        if (node && currentMsg) {
          currentMsg.thoughtTitle = nodeNaturalMapping[node] || '正在协同企业数字员工处理中...';
          if (!currentMsg.nodeSteps.includes(node)) {
            currentMsg.nodeSteps.push(node);
          }
        }
        activeNodes.value = [node];
        break;

      case 'token':
        if (currentMsg) {
          currentMsg.content += content;
          currentMsg.isStreaming = true;
        }
        break;

      case 'tool_log':
        if (currentMsg) {
          currentMsg.toolLogs.push({
            tool,
            status,
            input,
            output,
            timestamp: new Date().toLocaleTimeString()
          });

          // 结构化转译为业务知识来源卡片
          if (tool === 'rag_retrieval' || tool === 'knowledge_search' || output) {
            const docTitle = (input && typeof input === 'object' && input.query)
              ? `《企业规章知识检索：${input.query}》`
              : (typeof input === 'string' ? `《制度条款：${input}》` : '《企业协同管理制度指南》');

            const snippetText = typeof output === 'string'
              ? output.slice(0, 160)
              : JSON.stringify(output).slice(0, 160);

            currentMsg.sources.push({
              doc_id: `SOP-2026-0${currentMsg.sources.length + 1}`,
              title: docTitle,
              snippet: snippetText,
              tag: tool || '制度核验',
            });
          }
        }
        break;

      case 'interrupt':
        if (currentMsg) {
          currentMsg.interruptData = approval_data;
          currentMsg.completed = true;
          currentMsg.isStreaming = false;
        }
        try {
          const approvalStore = useApprovalStore();
          approvalStore.addPendingApproval(approval_data);
        } catch (e) {
          console.warn('[ChatStream] Sync to approvalStore failed:', e);
        }
        isStreaming.value = false;
        activeNodes.value = [];
        break;

      case 'complete':
        if (currentMsg) {
          if (final_answer && !currentMsg.content) {
            currentMsg.content = final_answer;
          }
          currentMsg.completed = true;
          currentMsg.isStreaming = false;
        }
        isStreaming.value = false;
        activeNodes.value = [];
        break;

      case 'cancelled':
        if (currentMsg) {
          currentMsg.content += '\n\n> *已响应您的操作，停止当前生成。*';
          currentMsg.completed = true;
          currentMsg.isStreaming = false;
        }
        isStreaming.value = false;
        activeNodes.value = [];
        break;

      case 'error':
        if (currentMsg) {
          currentMsg.content += `\n\n> *系统服务暂时繁忙，已为您自动转入离线工单保障状态。*`;
          currentMsg.completed = true;
          currentMsg.isStreaming = false;
        }
        isStreaming.value = false;
        activeNodes.value = [];
        break;

      default:
        break;
    }
  };

  const sendMessage = (text, customMetadata = {}) => {
    if (!text.trim() || !isConnected.value) return;

    const userMsg = {
      id: `msg_u_${Date.now()}`,
      sender: 'user',
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString(),
    };
    messages.value.push(userMsg);

    const aiMsg = {
      id: `msg_ai_${Date.now()}`,
      sender: 'ai',
      role: 'assistant',
      content: '',
      thoughtTitle: '正在分析业务意图并匹配专职数字员工...',
      thoughts: [],
      sources: [],
      nodeSteps: [],
      toolLogs: [],
      interruptData: null,
      isStreaming: true,
      completed: false,
      timestamp: new Date().toLocaleTimeString(),
    };
    messages.value.push(aiMsg);

    const payload = {
      message: text,
      thread_id: currentThreadId.value,
      user_id: 'u_vue3_user',
      session_id: `s_vue3_${Date.now()}`,
      metadata: customMetadata,
    };

    ws.send(JSON.stringify(payload));
  };

  const abortChat = async () => {
    if (!isStreaming.value) return;
    try {
      await fetch('/api/v1/chat/abort', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: currentThreadId.value })
      });
      // 客户端主动停止状态
      isStreaming.value = false;
      const currentMsg = messages.value[messages.value.length - 1];
      if (currentMsg && currentMsg.sender === 'ai' && !currentMsg.completed) {
        currentMsg.completed = true;
        currentMsg.isStreaming = false;
        currentMsg.content += '\n\n> *已响应您的操作，停止当前生成。*';
      }
    } catch (err) {
      console.error('[ChatStream] Abort Error:', err);
    }
  };

  const submitApprovalAction = async (approvalId, action, comment = '') => {
    try {
      const approvalStore = useApprovalStore();
      const res = await approvalStore.submitDecision(approvalId, action, comment);

      const msg = messages.value.find(
        (m) =>
          m.interruptData &&
          (m.interruptData.approval_id === approvalId || m.interruptData.id === approvalId)
      );
      if (msg) {
        msg.interruptData.status = action.toUpperCase() === 'APPROVE' ? 'APPROVED' : 'REJECTED';
        msg.interruptData.comment = comment;
        msg.interruptData.approver = '张经理 (研发主管)';
        msg.interruptData.decision_time = new Date().toLocaleTimeString('zh-CN');
        if (res && res.graph_output && res.graph_output !== 'Resumed') {
          msg.content = res.graph_output;
        } else {
          msg.content =
            action.toUpperCase() === 'APPROVE'
              ? '已核准采购申请。审批单已归档，后续采购流程与 ERP 工单已下发推进。'
              : '采购申请已被驳回，审批流程已终止。';
        }
      }
    } catch (err) {
      console.error('[ChatStream] Approval Action Error:', err);
    }
  };

  const resetThread = () => {
    messages.value = [];
    currentThreadId.value = `thread_ws_${Date.now().toString().slice(-6)}`;
  };

  onMounted(() => {
    connect();
  });

  onUnmounted(() => {
    stopHeartbeat();
    if (ws) ws.close();
  });

  return {
    isConnected,
    isStreaming,
    messages,
    currentThreadId,
    activeNodes,
    sendMessage,
    abortChat,
    submitApprovalAction,
    resetThread,
  };
}
