import { createRouter, createWebHistory } from 'vue-router';
import ChatView from '../views/ChatView.vue';
import { useAuthStore } from '../stores/authStore';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: {
      title: '身份认证登录 - 企业数字员工',
      public: true,
      layout: 'blank',
    },
  },
  {
    path: '/',
    name: 'Chat',
    component: ChatView,
    meta: {
      title: '企业数字员工 - AI Copilot Studio',
      navLabel: '对话工作台',
      requiresAuth: true,
      roles: ['employee', 'manager', 'admin'],
    },
  },
  {
    path: '/approvals',
    name: 'Approvals',
    component: () => import('../views/ApprovalListView.vue'),
    meta: {
      title: '待我审批 - 企业数字员工',
      navLabel: '待我审批',
      requiresAuth: true,
      roles: ['manager', 'admin'],
    },
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('../views/KnowledgeView.vue'),
    meta: {
      title: '规章制度知识库 - 企业数字员工',
      navLabel: '规章制度知识库',
      requiresAuth: true,
      roles: ['employee', 'manager', 'admin'],
    },
  },
  {
    path: '/admin/settings',
    name: 'AdminSettings',
    component: () => import('../views/AdminSettingsView.vue'),
    meta: {
      title: '模型与参数配置 - 系统管理控制台',
      navLabel: '模型与参数配置',
      requiresAuth: true,
      roles: ['admin'],
      adminSlot: 'settings',
    },
  },
  {
    path: '/admin/tasks',
    name: 'AdminTasks',
    component: () => import('../views/AdminTasksView.vue'),
    meta: {
      title: '知识库运维与任务中心 - 系统管理控制台',
      navLabel: '知识库运维与任务中心',
      requiresAuth: true,
      roles: ['admin'],
      adminSlot: 'tasks',
    },
  },
  {
    path: '/admin/monitoring',
    name: 'AdminMonitoring',
    component: () => import('../views/AdminSlotPlaceholderView.vue'),
    meta: {
      title: '运行遥测监控 - 系统管理控制台',
      navLabel: '运行遥测监控',
      requiresAuth: true,
      roles: ['admin'],
      adminSlot: 'monitoring',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();
  await authStore.ensureSession();

  if (to.meta?.public) {
    next();
    return;
  }

  if (to.meta?.requiresAuth && !authStore.isAuthenticated) {
    next({
      path: '/login',
      query: { redirect: to.fullPath },
    });
    return;
  }

  const allowedRoles = to.meta?.roles;
  if (Array.isArray(allowedRoles) && !allowedRoles.includes(authStore.currentRole)) {
    const targetName = to.meta?.navLabel || to.path;
    let requiredText = '授权角色';
    if (allowedRoles.length === 1 && allowedRoles[0] === 'admin') {
      requiredText = '系统管理员';
    } else if (allowedRoles.includes('manager') && !allowedRoles.includes('employee')) {
      requiredText = '部门主管或系统管理员';
    }
    authStore.setPermissionNotice(
      `访问受限：当前身份为「${authStore.displayName} (${authStore.roleLabel})」，「${targetName}」仅限${requiredText}访问，已为您返回工作台。`
    );
    next('/');
    return;
  }

  next();
});

router.afterEach((to) => {
  if (to.meta && to.meta.title) {
    document.title = to.meta.title;
  }
});

export default router;
