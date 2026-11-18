import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

const PREFS_STORAGE_KEY = 'enterprise_ai_user_prefs_v1';

const applyThemeToDom = (themeValue) => {
  if (typeof document === 'undefined') return;
  if (themeValue === 'light') {
    document.documentElement.classList.remove('dark');
  } else {
    document.documentElement.classList.add('dark');
  }
};

export const usePreferencesStore = defineStore('preferences', () => {
  const initialTheme =
    typeof localStorage !== 'undefined' && localStorage.getItem('theme') === 'light'
      ? 'light'
      : 'dark';

  const loadSavedPrefs = () => {
    try {
      if (typeof localStorage === 'undefined') return {};
      const raw = localStorage.getItem(PREFS_STORAGE_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  };

  const saved = loadSavedPrefs();
  const theme = ref(saved.theme === 'light' || saved.theme === 'dark' ? saved.theme : initialTheme);
  const chatDensity = ref(saved.chatDensity === 'compact' ? 'compact' : 'comfortable');
  const autoCollapseThought = ref(
    typeof saved.autoCollapseThought === 'boolean' ? saved.autoCollapseThought : true
  );
  const isPreferencesOpen = ref(false);

  const isDark = computed(() => theme.value === 'dark');

  const persist = () => {
    try {
      if (typeof localStorage === 'undefined') return;
      localStorage.setItem('theme', theme.value);
      localStorage.setItem(
        PREFS_STORAGE_KEY,
        JSON.stringify({
          theme: theme.value,
          chatDensity: chatDensity.value,
          autoCollapseThought: autoCollapseThought.value,
        })
      );
    } catch {
      // ignore storage errors
    }
  };

  const setTheme = (nextTheme) => {
    theme.value = nextTheme === 'light' ? 'light' : 'dark';
    applyThemeToDom(theme.value);
    persist();
  };

  const toggleTheme = () => {
    setTheme(theme.value === 'dark' ? 'light' : 'dark');
  };

  const setChatDensity = (density) => {
    chatDensity.value = density === 'compact' ? 'compact' : 'comfortable';
    persist();
  };

  const setAutoCollapseThought = (value) => {
    autoCollapseThought.value = Boolean(value);
    persist();
  };

  const openPreferencesModal = () => {
    isPreferencesOpen.value = true;
  };

  const closePreferencesModal = () => {
    isPreferencesOpen.value = false;
  };

  applyThemeToDom(theme.value);

  return {
    theme,
    isDark,
    chatDensity,
    autoCollapseThought,
    isPreferencesOpen,
    setTheme,
    toggleTheme,
    setChatDensity,
    setAutoCollapseThought,
    openPreferencesModal,
    closePreferencesModal,
  };
});
