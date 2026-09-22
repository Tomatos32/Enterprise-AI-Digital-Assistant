/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // UI/UX Pro Max 语义色彩映射
        'bg-sidebar': 'var(--bg-sidebar)',
        'bg-main': 'var(--bg-main)',
        'bg-card': 'var(--bg-card)',
        'bg-input': 'var(--bg-input)',
        'border-subtle': 'var(--border-subtle)',
        'border-card': 'var(--border-card)',
        'border-focus': 'var(--border-focus)',
        'text-main': 'var(--text-main)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'brand-primary': 'var(--brand-primary)',
        'brand-primary-hover': 'var(--brand-primary-hover)',
        'status-approval': 'var(--status-approval)',
        'status-success': 'var(--status-success)',
        'status-danger': 'var(--status-danger)',

        // 品牌与灰阶兼容
        brand: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          900: '#1e3a8a',
        },
        dark: {
          bg: '#0f172a',
          card: '#1e293b',
          border: '#334155',
        }
      },
      fontFamily: {
        sans: ['Inter', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        mono: ['Fira Code', 'JetBrains Mono', 'monospace'],
      },
      transitionDuration: {
        150: '150ms',
      }
    },
  },
  plugins: [],
}
