import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

const STORAGE_KEY = 'enterprise_ai_sessions_v1';

export const useChatStore = defineStore('chat', () => {
  const sessions = ref([]);
  const activeSessionId = ref('');
  const isOnline = ref(true);
  const selectedMode = ref('general'); // 'general' | 'it' | 'finance' | 'hr'

  // 时间维度基准计算
  const getStartOfDay = (d) => {
    const date = new Date(d);
    date.setHours(0, 0, 0, 0);
    return date.getTime();
  };

  const now = Date.now();
  const startOfToday = getStartOfDay(now);
  const startOfYesterday = startOfToday - 86400000;
  const startOf7DaysAgo = startOfToday - 7 * 86400000;

  // 活跃会话对象
  const activeSession = computed(() => {
    return sessions.value.find((s) => s.id === activeSessionId.value) || sessions.value[0] || null;
  });

  // 按时间维度计算分组
  const todaySessions = computed(() => {
    return sessions.value.filter((s) => (s.updatedAt || s.createdAt) >= startOfToday);
  });

  const yesterdaySessions = computed(() => {
    return sessions.value.filter((s) => {
      const time = s.updatedAt || s.createdAt;
      return time >= startOfYesterday && time < startOfToday;
    });
  });

  const previous7DaysSessions = computed(() => {
    return sessions.value.filter((s) => {
      const time = s.updatedAt || s.createdAt;
      return time >= startOf7DaysAgo && time < startOfYesterday;
    });
  });

  const olderSessions = computed(() => {
    return sessions.value.filter((s) => {
      const time = s.updatedAt || s.createdAt;
      return time < startOf7DaysAgo;
    });
  });

  // 待办审批未读数量计数
  const pendingApprovalsCount = ref(1);

  // 本地存储同步
  const saveToStorage = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        sessions: sessions.value,
        activeSessionId: activeSessionId.value,
        selectedMode: selectedMode.value,
      }));
    } catch (e) {
      console.warn('[ChatStore] localStorage write failed:', e);
    }
  };

  // 创建新会话 (支持异步向后端注册)
  const createSession = async (initialTitle = '新对话') => {
    let newSessionId = `s_vue3_${Date.now()}`;
    try {
      const res = await fetch('/api/v1/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: initialTitle, user_id: 'u_vue3_user' })
      });
      if (res.ok) {
        const s = await res.json();
        if (s && s.session_id) {
          newSessionId = s.session_id;
        }
      }
    } catch (e) {
      console.warn('[ChatStore] createSession API failed, fallback to local ID:', e);
    }

    const newSession = {
      id: newSessionId,
      title: initialTitle,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      messages: [],
    };
    sessions.value.unshift(newSession);
    activeSessionId.value = newSession.id;
    saveToStorage();
    return newSession;
  };

  // 切换会话
  const switchSession = (sessionId) => {
    if (activeSessionId.value === sessionId) return;
    const target = sessions.value.find((s) => s.id === sessionId);
    if (target) {
      activeSessionId.value = sessionId;
      saveToStorage();
    }
  };

  // 删除会话
  const deleteSession = async (sessionId) => {
    const idx = sessions.value.findIndex((s) => s.id === sessionId);
    if (idx === -1) return;

    try {
      await fetch(`/api/v1/chat/sessions/${sessionId}`, { method: 'DELETE' });
    } catch (e) {
      console.warn('[ChatStore] deleteSession API error:', e);
    }

    sessions.value.splice(idx, 1);
    if (activeSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        activeSessionId.value = sessions.value[0].id;
      } else {
        await createSession('新对话');
      }
    }
    saveToStorage();
  };

  // 重命名会话
  const renameSession = async (sessionId, newTitle) => {
    const session = sessions.value.find((s) => s.id === sessionId);
    if (session && newTitle.trim()) {
      session.title = newTitle.trim();
      session.updatedAt = Date.now();
      saveToStorage();
      try {
        await fetch(`/api/v1/chat/sessions/${sessionId}/title`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: newTitle.trim() })
        });
      } catch (e) {
        console.warn('[ChatStore] renameSession API error:', e);
      }
    }
  };

  // 从后端异步加载指定会话的历史消息
  const loadSessionMessages = async (sessionId) => {
    if (!sessionId) return [];
    const targetSession = sessions.value.find((s) => s.id === sessionId);
    try {
      const res = await fetch(`/api/v1/chat/sessions/${sessionId}/messages`);
      if (res.ok) {
        const dbMessages = await res.json();
        if (Array.isArray(dbMessages)) {
          const formatted = dbMessages.map((m) => {
            let parsedSources = [];
            if (m.sources) {
              try {
                const arr = JSON.parse(m.sources);
                if (Array.isArray(arr)) {
                  parsedSources = arr.map((src, idx) => ({
                    doc_id: `DOC-DB-${idx + 1}`,
                    title: typeof src === 'string' ? (src.startsWith('《') ? src : `《${src}》`) : '参考制度',
                    snippet: '',
                    tag: '制度依据'
                  }));
                }
              } catch {}
            }
            return {
              id: `msg_db_${m.id}`,
              sender: m.role === 'user' ? 'user' : 'ai',
              role: m.role,
              content: m.content,
              sources: parsedSources,
              completed: true,
              isStreaming: false,
              timestamp: new Date(m.created_at).toLocaleTimeString()
            };
          });
          if (targetSession) {
            targetSession.messages = formatted;
          }
          return formatted;
        }
      } else if (res.status === 404) {
        // 自动容错旧前端缓存会话，静默在数据库注册
        try {
          await fetch('/api/v1/chat/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: targetSession?.title || '新对话', user_id: 'u_vue3_user' })
          });
        } catch {}
        return targetSession ? targetSession.messages : [];
      }
    } catch (e) {
      console.warn(`[ChatStore] loadSessionMessages failed for ${sessionId}:`, e);
    }
    return targetSession ? targetSession.messages : [];
  };

  // 从后端拉取真实会话列表
  const fetchSessions = async () => {
    try {
      const res = await fetch('/api/v1/chat/sessions?user_id=u_vue3_user');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          sessions.value = data.map((s) => ({
            id: s.session_id,
            title: s.title,
            createdAt: new Date(s.created_at).getTime(),
            updatedAt: new Date(s.updated_at).getTime(),
            messages: []
          }));
          if (!sessions.value.some((s) => s.id === activeSessionId.value)) {
            activeSessionId.value = sessions.value[0].id;
          }
          saveToStorage();
          return;
        }
      }
    } catch (e) {
      console.warn('[ChatStore] fetchSessions error, using cached sessions:', e);
    }
    initSessions();
  };

  // 为当前会话追加消息，并智能提炼首条消息作为会话标题
  const addMessageToActiveSession = (msg) => {
    if (!activeSession.value) {
      createSession();
    }
    const session = activeSession.value;
    session.messages.push(msg);
    session.updatedAt = Date.now();

    // 智能标题提炼
    if (msg.sender === 'user' && (session.title === '新对话' || !session.title)) {
      const summary = msg.content.trim().slice(0, 18);
      session.title = summary ? (summary.length >= 18 ? summary + '...' : summary) : '新对话';
    }

    saveToStorage();
  };

  // 初始化或从本地恢复
  const initSessions = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed.sessions) && parsed.sessions.length > 0) {
          sessions.value = parsed.sessions;
          activeSessionId.value = parsed.activeSessionId || parsed.sessions[0].id;
          if (parsed.selectedMode) selectedMode.value = parsed.selectedMode;
          return;
        }
      }
    } catch (e) {
      console.warn('[ChatStore] localStorage read failed:', e);
    }

    // 默认内置符合企业实际场景的会话模板
    const tNow = Date.now();
    sessions.value = [
      {
        id: `s_today_${tNow}`,
        title: '2026 Q3 研发设备采购咨询',
        createdAt: tNow - 1000 * 60 * 30, // 30分钟前
        updatedAt: tNow - 1000 * 60 * 30,
        messages: [],
      },
      {
        id: `s_yest_${tNow - 86400000}`,
        title: 'IT 运维网络故障排查与工单流转',
        createdAt: tNow - 86400000 - 1000 * 60 * 60 * 2, // 昨天
        updatedAt: tNow - 86400000 - 1000 * 60 * 60 * 2,
        messages: [],
      },
      {
        id: `s_prev_${tNow - 86400000 * 3}`,
        title: '新员工入职协同指引与规章查询',
        createdAt: tNow - 86400000 * 3, // 3天前
        updatedAt: tNow - 86400000 * 3,
        messages: [],
      },
    ];
    activeSessionId.value = sessions.value[0].id;
    saveToStorage();
  };

  // 初始化执行
  initSessions();

  return {
    sessions,
    activeSessionId,
    activeSession,
    isOnline,
    selectedMode,
    pendingApprovalsCount,
    todaySessions,
    yesterdaySessions,
    previous7DaysSessions,
    olderSessions,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
    addMessageToActiveSession,
    initSessions,
    loadSessionMessages,
    fetchSessions,
  };
});
