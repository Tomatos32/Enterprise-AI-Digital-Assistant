import { createRouter, createWebHistory } from 'vue-router';
import ChatContainer from '../components/ChatContainer.vue';

const routes = [
  {
    path: '/',
    name: 'Chat',
    component: ChatContainer,
    meta: { title: '企业数字员工 - AI Copilot Studio' },
  },
  {
    path: '/approvals',
    name: 'Approvals',
    component: () => import('../views/ApprovalListView.vue'),
    meta: { title: '待我审批 - 企业数字员工' },
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('../views/KnowledgeView.vue'),
    meta: { title: '规章制度知识库 - 企业数字员工' },
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

router.afterEach((to) => {
  if (to.meta && to.meta.title) {
    document.title = to.meta.title;
  }
});

export default router;
