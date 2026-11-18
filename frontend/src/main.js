import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import './index.css';

// 按本地偏好初始化日夜双主题模式（默认夜间模式）
if (typeof localStorage !== 'undefined' && localStorage.getItem('theme') === 'light') {
  document.documentElement.classList.remove('dark');
} else {
  document.documentElement.classList.add('dark');
}

const app = createApp(App);
const pinia = createPinia();

// 注册全局常用指令：自动聚焦 (v-focus)
app.directive('focus', {
  mounted(el) {
    el.focus();
  }
});

app.use(pinia);
app.use(router);

app.mount('#app');
