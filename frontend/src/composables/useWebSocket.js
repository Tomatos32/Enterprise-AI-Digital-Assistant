import { ref, onMounted, onUnmounted } from 'vue';

export function useWebSocket(clientId = 'vue3_client_001') {
  const isConnected = ref(false);
  const isStreaming = ref(false);
  const messages = ref([]);
  const currentThreadId = ref(`thread_ws_${Date.now().toString().slice(-6)}`);
  const activeNodes = ref([]);

  let ws = null;

  const connect = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/ws/chat/${clientId}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      isConnected.value = true;
      console.log('[WebSocket] Connected to', wsUrl);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWsEvent(data);
      } catch (err) {
        console.error('[WebSocket] JSON Parse Error:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('[WebSocket] Error:', err);
      isConnected.value = false;
    };

    ws.onclose = () => {
      isConnected.value = false;
      console.log('[WebSocket] Disconnected. Reconnecting in 3s...');
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
        break;

      case 'node_start':
        if (!currentMsg.nodeSteps.includes(node)) {
          currentMsg.nodeSteps.push(node);
        }
        activeNodes.value = [node];
        break;

      case 'token':
        currentMsg.content += content;
        break;

      case 'tool_log':
        currentMsg.toolLogs.push({
          tool,
          status,
          input,
          output,
          timestamp: new Date().toLocaleTimeString()
        });
        break;

      case 'interrupt':
        currentMsg.interruptData = approval_data;
        currentMsg.completed = true;
        isStreaming.value = false;
        activeNodes.value = [];
        break;

      case 'complete':
        if (final_answer && !currentMsg.content) {
          currentMsg.content = final_answer;
        }
        currentMsg.completed = true;
        isStreaming.value = false;
        activeNodes.value = [];
        break;

      case 'cancelled':
        currentMsg.content += '\n\n⚠️ *[用户已主动中断输出]*';
        currentMsg.completed = true;
        isStreaming.value = false;
        activeNodes.value = [];
        break;

      case 'error':
        currentMsg.content += `\n\n❌ [系统错误]: ${message}`;
        currentMsg.completed = true;
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
      content: text,
      timestamp: new Date().toLocaleTimeString(),
    };
    messages.value.push(userMsg);

    const aiMsg = {
      id: `msg_ai_${Date.now()}`,
      sender: 'ai',
      content: '',
      nodeSteps: [],
      toolLogs: [],
      interruptData: null,
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
    } catch (err) {
      console.error('[Abort Error]:', err);
    }
  };

  const submitApprovalAction = async (approvalId, action, comment = '') => {
    try {
      const resp = await fetch('/api/v1/approval/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approval_id: approvalId,
          action,
          comment
        })
      });
      const data = await resp.json();

      // Update current message state to reflect decision
      const msg = messages.value.find(m => m.interruptData && m.interruptData.approval_id === approvalId);
      if (msg) {
        msg.interruptData.status = action.toUpperCase() === 'APPROVE' ? 'APPROVED' : 'REJECTED';
        msg.interruptData.comment = comment;
        msg.content = data.graph_output || `[审批操作已完成] 决策: ${action.toUpperCase()}`;
      }
    } catch (err) {
      console.error('[Approval Action Error]:', err);
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
