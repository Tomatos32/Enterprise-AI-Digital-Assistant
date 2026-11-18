import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

const AUTH_STORAGE_KEY = 'enterprise_ai_auth_v1';
const EXPLICIT_LOGOUT_KEY = 'enterprise_ai_logged_out_v1';

const ROLE_LABEL_MAP = {
  employee: '普通员工',
  manager: '部门主管',
  admin: '系统管理员',
};

const FALLBACK_DEMO_IDENTITIES = [
  {
    username: 'employee',
    display_name: '林小晴',
    role: 'employee',
    role_label: '普通员工',
    department: '人力资源部',
  },
  {
    username: 'manager',
    display_name: '陈志远',
    role: 'manager',
    role_label: '部门主管',
    department: '采购管理部',
  },
  {
    username: 'admin',
    display_name: '周明辉',
    role: 'admin',
    role_label: '系统管理员',
    department: 'IT 系统管理部',
  },
];

export const useAuthStore = defineStore('auth', () => {
  const token = ref('');
  const user = ref(null);
  const demoIdentities = ref([...FALLBACK_DEMO_IDENTITIES]);
  const isLoading = ref(false);
  const authError = ref('');
  const permissionNotice = ref('');
  const initialized = ref(false);
  let bootstrapPromise = null;

  const persistAuth = () => {
    try {
      if (token.value && user.value) {
        localStorage.setItem(
          AUTH_STORAGE_KEY,
          JSON.stringify({
            token: token.value,
            user: user.value,
          })
        );
      } else {
        localStorage.removeItem(AUTH_STORAGE_KEY);
      }
    } catch (err) {
      console.warn('[AuthStore] persistAuth failed:', err);
    }
  };

  const restoreFromStorage = () => {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      if (!raw) return false;
      const parsed = JSON.parse(raw);
      if (parsed && parsed.token && parsed.user && parsed.user.username) {
        token.value = parsed.token;
        user.value = parsed.user;
        return true;
      }
    } catch (err) {
      console.warn('[AuthStore] restoreFromStorage failed:', err);
    }
    return false;
  };

  const isAuthenticated = computed(() => Boolean(token.value && user.value?.username));
  const currentRole = computed(() => user.value?.role || 'employee');
  const currentUsername = computed(() => user.value?.username || '');
  const displayName = computed(() => user.value?.display_name || user.value?.username || '未登录访客');
  const department = computed(() => user.value?.department || '综合事务部');
  const roleLabel = computed(
    () => user.value?.role_label || ROLE_LABEL_MAP[currentRole.value] || '普通员工'
  );
  const avatarInitial = computed(() => {
    const name = displayName.value.trim();
    return name ? name.slice(0, 1) : '用';
  });
  const canApprove = computed(() => ['manager', 'admin'].includes(currentRole.value));
  const isAdmin = computed(() => currentRole.value === 'admin');
  const approverSignature = computed(
    () => `${displayName.value} (${department.value} · ${roleLabel.value})`
  );

  const getAuthHeaders = (extra = {}) => {
    if (!token.value) return { ...extra };
    return {
      ...extra,
      Authorization: `Bearer ${token.value}`,
    };
  };

  const setPermissionNotice = (message) => {
    permissionNotice.value = message || '';
  };

  const clearPermissionNotice = () => {
    permissionNotice.value = '';
  };

  const applyTokenPayload = (payload) => {
    if (!payload || !payload.access_token) {
      throw new Error('认证响应缺少有效访问令牌');
    }
    token.value = payload.access_token;
    user.value = {
      username: payload.username,
      display_name: payload.display_name || payload.username,
      role: payload.role,
      role_label: payload.role_label || ROLE_LABEL_MAP[payload.role] || payload.role,
      department: payload.department || '综合事务部',
    };
    try {
      localStorage.removeItem(EXPLICIT_LOGOUT_KEY);
    } catch {
      // ignore storage errors
    }
    persistAuth();
  };

  const fetchDemoIdentities = async () => {
    try {
      const resp = await fetch('/api/v1/auth/identities');
      if (resp.ok) {
        const json = await resp.json();
        if (Array.isArray(json.data) && json.data.length > 0) {
          demoIdentities.value = json.data;
          return demoIdentities.value;
        }
      }
    } catch (err) {
      console.warn('[AuthStore] fetchDemoIdentities fallback:', err);
    }
    return demoIdentities.value;
  };

  const login = async (username, password) => {
    isLoading.value = true;
    authError.value = '';
    try {
      const resp = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const json = await resp.json();
      if (!resp.ok || json.code >= 400) {
        const msg =
          resp.status === 401
            ? '账号或密码校验未通过，请检查输入信息'
            : json.message || '登录请求失败';
        authError.value = msg;
        return { success: false, error: msg };
      }
      applyTokenPayload(json.data);
      clearPermissionNotice();
      return { success: true, user: user.value };
    } catch (err) {
      const msg = err.message || '无法连接认证服务，请确认后端运行正常';
      authError.value = msg;
      return { success: false, error: msg };
    } finally {
      isLoading.value = false;
    }
  };

  const switchRole = async (targetRoleOrUsername) => {
    isLoading.value = true;
    authError.value = '';
    try {
      const isRole = ['employee', 'manager', 'admin'].includes(targetRoleOrUsername);
      const body = isRole
        ? { role: targetRoleOrUsername }
        : { username: targetRoleOrUsername };

      const resp = await fetch('/api/v1/auth/switch-role', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const json = await resp.json();
      if (!resp.ok || json.code >= 400) {
        const msg = json.message || '角色身份切换失败';
        authError.value = msg;
        return { success: false, error: msg };
      }
      applyTokenPayload(json.data);
      clearPermissionNotice();
      return { success: true, user: user.value };
    } catch (err) {
      const msg = err.message || '身份切换请求异常，请检查网络与服务状态';
      authError.value = msg;
      return { success: false, error: msg };
    } finally {
      isLoading.value = false;
    }
  };

  const fetchMe = async () => {
    if (!token.value) return false;
    try {
      const resp = await fetch('/api/v1/auth/me', {
        headers: getAuthHeaders(),
      });
      if (!resp.ok) {
        if (resp.status === 401) {
          logout(false);
        }
        return false;
      }
      const json = await resp.json();
      if (json.data && json.data.username) {
        user.value = {
          username: json.data.username,
          display_name: json.data.display_name || json.data.username,
          role: json.data.role,
          role_label:
            json.data.role_label || ROLE_LABEL_MAP[json.data.role] || json.data.role,
          department: json.data.department || '综合事务部',
        };
        persistAuth();
        return true;
      }
      return false;
    } catch (err) {
      console.warn('[AuthStore] fetchMe check skipped:', err);
      return Boolean(user.value);
    }
  };

  const logout = (markExplicit = true) => {
    token.value = '';
    user.value = null;
    authError.value = '';
    if (markExplicit) {
      try {
        localStorage.setItem(EXPLICIT_LOGOUT_KEY, '1');
      } catch {
        // ignore storage errors
      }
    }
    persistAuth();
  };

  const handleUnauthorized = () => {
    logout(false);
    setPermissionNotice('当前会话凭证已过期或失效，请重新登录。');
  };

  const ensureSession = async () => {
    if (initialized.value && isAuthenticated.value) {
      return true;
    }
    if (bootstrapPromise) {
      return bootstrapPromise;
    }
    bootstrapPromise = (async () => {
      try {
        restoreFromStorage();
        if (token.value) {
          const ok = await fetchMe();
          if (ok) {
            initialized.value = true;
            fetchDemoIdentities();
            return true;
          }
        }
        let explicitlyLoggedOut = false;
        try {
          explicitlyLoggedOut = localStorage.getItem(EXPLICIT_LOGOUT_KEY) === '1';
        } catch {
          explicitlyLoggedOut = false;
        }
        await fetchDemoIdentities();
        if (!explicitlyLoggedOut) {
          const res = await switchRole('employee');
          initialized.value = true;
          return res.success;
        }
        initialized.value = true;
        return false;
      } finally {
        bootstrapPromise = null;
      }
    })();
    return bootstrapPromise;
  };

  restoreFromStorage();

  return {
    token,
    user,
    demoIdentities,
    isLoading,
    authError,
    permissionNotice,
    initialized,
    isAuthenticated,
    currentRole,
    currentUsername,
    displayName,
    department,
    roleLabel,
    avatarInitial,
    canApprove,
    isAdmin,
    approverSignature,
    getAuthHeaders,
    setPermissionNotice,
    clearPermissionNotice,
    fetchDemoIdentities,
    login,
    switchRole,
    fetchMe,
    logout,
    handleUnauthorized,
    ensureSession,
  };
});
