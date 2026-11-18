import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useAuthStore } from './authStore';

const STORAGE_PREFIX = 'enterprise_ai_sessions_v2_';

export const useChatStore = defineStore('chat', () => {
  const authStore = useAuthStore();

  const sessions = ref([]);
  const activeSessionId = ref('');
  const isOnline = ref(true);
  const selectedMode = ref('general'); // 'general' | 'it' | 'finance' | 'hr'
  const pendingApprovalsCount = ref(0);
  let inFlightFetch = null;
  let inFlightOwner = '';

  const getStorageKey = () => `${STORAGE_PREFIX}${authStore.currentUsername || 'guest'}`;

  // 时间维度基准动态计算
  const getStartOfDay = (d) => {
    const date = new Date(d);
    date.setHours(0, 0, 0, 0);
    return date.getTime();
  };

  const getTime = (s) => {
    const t = s.updatedAt || s.createdAt;
    if (!t) return 0;
    return typeof t === 'number' ? t : new Date(t).getTime();
  };

  // 活跃会话对象
  const activeSession = computed(() => {
    return sessions.value.find((s) => s.id === activeSessionId.value) || sessions.value[0] || null;
  });

  // 按时间维度动态计算分组
  const todaySessions = computed(() => {
    const startOfToday = getStartOfDay(Date.now());
    return sessions.value.filter((s) => getTime(s) >= startOfToday);
  });

  const yesterdaySessions = computed(() => {
    const startOfToday = getStartOfDay(Date.now());
    const startOfYesterday = startOfToday - 86400000;
    return sessions.value.filter((s) => {
      const time = getTime(s);
      return time >= startOfYesterday && time < startOfToday;
    });
  });

  const previous7DaysSessions = computed(() => {
    const startOfToday = getStartOfDay(Date.now());
    const startOfYesterday = startOfToday - 86400000;
    const startOf7DaysAgo = startOfToday - 7 * 86400000;
    return sessions.value.filter((s) => {
      const time = getTime(s);
      return time >= startOf7DaysAgo && time < startOfYesterday;
    });
  });

  const olderSessions = computed(() => {
    const startOfToday = getStartOfDay(Date.now());
    const startOf7DaysAgo = startOfToday - 7 * 86400000;
    return sessions.value.filter((s) => {
      const time = getTime(s);
      return time > 0 && time < startOf7DaysAgo;
    });
  });

  const saveToStorage = () => {
    if (!authStore.currentUsername) return;
    try {
      localStorage.setItem(
        getStorageKey(),
        JSON.stringify({
          sessions: sessions.value,
          activeSessionId: activeSessionId.value,
          selectedMode: selectedMode.value,
        })
      );
    } catch (e) {
      console.warn('[ChatStore] localStorage write failed:', e);
    }
  };

  const createSession = async (initialTitle = '新对话') => {
    let newSessionId = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const ownerId = authStore.currentUsername;
    if (ownerId && authStore.token) {
      try {
        const res = await fetch('/api/v1/chat/sessions', {
          method: 'POST',
          headers: authStore.getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ title: initialTitle, user_id: ownerId }),
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

  const switchSession = (sessionId) => {
    if (activeSessionId.value === sessionId) return;
    const target = sessions.value.find((s) => s.id === sessionId);
    if (target) {
      activeSessionId.value = sessionId;
      saveToStorage();
    }
  };

  const deleteSession = async (sessionId) => {
    const idx = sessions.value.findIndex((s) => s.id === sessionId);
    if (idx === -1) return;

    if (authStore.token) {
      try {
        await fetch(`/api/v1/chat/sessions/${sessionId}`, {
          method: 'DELETE',
          headers: authStore.getAuthHeaders(),
        });
      } catch (e) {
        console.warn('[ChatStore] deleteSession API error:', e);
      }
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

  const renameSession = async (sessionId, newTitle) => {
    const target = sessions.value.find((s) => s.id === sessionId);
    if (!target || !newTitle.trim()) return;
    target.title = newTitle.trim();
    target.updatedAt = Date.now();
    saveToStorage();

    if (authStore.token) {
      try {
        await fetch(`/api/v1/chat/sessions/${sessionId}/title`, {
          method: 'PUT',
          headers: authStore.getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ title: newTitle.trim() }),
        });
      } catch (e) {
        console.warn('[ChatStore] renameSession API error:', e);
      }
    }
  };

  const loadSessionMessages = async (sessionId) => {
    if (!sessionId || !authStore.token) return [];
    const targetSession = sessions.value.find((s) => s.id === sessionId);
    try {
      const res = await fetch(`/api/v1/chat/sessions/${sessionId}/messages`, {
        headers: authStore.getAuthHeaders(),
      });
      if (res.ok) {
        const msgs = await res.json();
        if (Array.isArray(msgs)) {
          const formatted = msgs.map((m) => {
            let parsedSources = [];
            if (m.sources) {
              try {
                const raw = JSON.parse(m.sources);
                if (Array.isArray(raw)) {
                  parsedSources = raw.map((name, idx) =>
                    typeof name === 'string'
                      ? { doc_id: `DB-REF-${idx + 1}`, title: `《${name}》`, tag: '历史引用' }
                      : name
                  );
                }
              } catch {
                // ignore malformed sources JSON
              }
            }

            let parsedSteps = [];
            if (m.thought_steps) {
              try {
                const rawSteps = JSON.parse(m.thought_steps);
                if (Array.isArray(rawSteps)) parsedSteps = rawSteps;
              } catch {
                // ignore malformed thought steps JSON
              }
            }

            return {
              id: `db_msg_${m.id}`,
              sender: m.role === 'user' ? 'user' : 'ai',
              role: m.role,
              content: m.content,
              thought: m.thought || '',
              durationSeconds: m.duration_seconds !== null ? m.duration_seconds : undefined,
              nodeSteps: parsedSteps,
              sources: parsedSources,
              completed: true,
              isStreaming: false,
              timestamp: new Date(m.created_at).toLocaleTimeString(),
            };
          });
          if (targetSession) {
            targetSession.messages = formatted;
          }
          return formatted;
        }
      } else if (res.status === 401) {
        authStore.handleUnauthorized();
        return [];
      } else if (res.status === 403) {
        return [];
      } else if (res.status === 404 && authStore.currentUsername) {
        try {
          const created = await fetch('/api/v1/chat/sessions', {
            method: 'POST',
            headers: authStore.getAuthHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
              title: targetSession?.title || '新对话',
              user_id: authStore.currentUsername,
            }),
          });
          if (created.ok && targetSession) {
            const createdData = await created.json();
            if (createdData?.session_id) {
              targetSession.id = createdData.session_id;
              activeSessionId.value = createdData.session_id;
              saveToStorage();
            }
          }
        } catch {
          // ignore offline fallback
        }
        return targetSession ? targetSession.messages : [];
      }
    } catch (e) {
      console.warn(`[ChatStore] loadSessionMessages failed for ${sessionId}:`, e);
    }
    return targetSession ? targetSession.messages : [];
  };

  const initSessions = () => {
    if (!authStore.currentUsername) {
      sessions.value = [];
      activeSessionId.value = '';
      return;
    }
    try {
      const raw = localStorage.getItem(getStorageKey());
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

    sessions.value = [
      {
        id: `sess_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        title: '新对话',
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [],
      },
    ];
    activeSessionId.value = sessions.value[0].id;
    saveToStorage();
  };

  const fetchSessions = async () => {
    const ownerId = authStore.currentUsername;
    if (!ownerId || !authStore.token) {
      sessions.value = [];
      activeSessionId.value = '';
      return;
    }
    if (inFlightFetch && inFlightOwner === ownerId) {
      return inFlightFetch;
    }
    inFlightOwner = ownerId;
    inFlightFetch = (async () => {
      try {
        const res = await fetch(
          `/api/v1/chat/sessions?user_id=${encodeURIComponent(ownerId)}`,
          { headers: authStore.getAuthHeaders() }
        );
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            if (authStore.currentUsername !== ownerId) return;
            if (data.length > 0) {
              sessions.value = data.map((s) => ({
                id: s.session_id,
                title: s.title,
                createdAt: new Date(s.created_at).getTime(),
                updatedAt: new Date(s.updated_at).getTime(),
                messages: [],
              }));
              if (!sessions.value.some((s) => s.id === activeSessionId.value)) {
                activeSessionId.value = sessions.value[0].id;
              }
              saveToStorage();
              return;
            }
            // Authenticated user has no DB sessions yet -> initialize one clean session
            sessions.value = [];
            activeSessionId.value = '';
            await createSession('新对话');
            return;
          }
        } else if (res.status === 401) {
          authStore.handleUnauthorized();
          return;
        }
      } catch (e) {
        console.warn('[ChatStore] fetchSessions error, using per-user cached sessions:', e);
      }
      if (authStore.currentUsername === ownerId) {
        initSessions();
      }
    })().finally(() => {
      if (inFlightOwner === ownerId) {
        inFlightFetch = null;
      }
    });
    return inFlightFetch;
  };

  const handleIdentityChange = async () => {
    sessions.value = [];
    activeSessionId.value = '';
    if (authStore.isAuthenticated) {
      await fetchSessions();
    }
  };

  const addMessageToActiveSession = (msg) => {
    if (!activeSession.value) {
      createSession();
    }
    const session = activeSession.value;
    if (!session) return;
    session.messages.push(msg);
    session.updatedAt = Date.now();

    if (msg.sender === 'user' && (session.title === '新对话' || !session.title)) {
      const summary = msg.content.trim().slice(0, 18);
      session.title = summary ? (summary.length >= 18 ? summary + '...' : summary) : '新对话';
    }

    saveToStorage();
  };

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
    handleIdentityChange,
  };
});
