/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Neutral Monochrome Dual-Theme Semantic Tokens
        'bg-sidebar': 'var(--bg-sidebar)',
        'bg-main': 'var(--bg-main)',
        'bg-card': 'var(--bg-card)',
        'bg-surface': 'var(--bg-surface)',
        'bg-input': 'var(--bg-input)',
        'bg-hover': 'var(--bg-hover)',
        'border-subtle': 'var(--border-subtle)',
        'border-card': 'var(--border-card)',
        'border-strong': 'var(--border-strong)',
        'border-focus': 'var(--border-focus)',
        'text-main': 'var(--text-main)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'action-primary': 'var(--action-primary-bg)',
        'action-primary-hover': 'var(--action-primary-bg-hover)',
        'action-primary-fg': 'var(--action-primary-fg)',
        'brand-primary': 'var(--brand-primary)',
        'brand-primary-hover': 'var(--brand-primary-hover)',
        'status-approval': 'var(--status-approval)',
        'status-success': 'var(--status-success)',
        'status-danger': 'var(--status-danger)',

        // Neutral Zinc / Stone Compat Scale
        paper: {
          50: '#ffffff',
          100: '#fafaf9',
          200: '#f4f4f2',
          300: '#ececea',
          400: '#e4e4e7',
        },
        dark: {
          bg: '#0a0a0b',
          sidebar: '#111113',
          card: '#141416',
          border: '#27272a',
        }
      },
      spacing: {
        tight: 'var(--space-tight)',
        intra: 'var(--space-intra)',
        card: 'var(--space-card)',
        group: 'var(--space-group)',
        section: 'var(--space-section)',
      },
      fontFamily: {
        sans: ['Inter', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        mono: ['Fira Code', 'JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      transitionDuration: {
        140: '140ms',
        150: '150ms',
        180: '180ms',
        200: '200ms',
        220: '220ms',
        280: '280ms',
      },
      transitionTimingFunction: {
        snappy: 'var(--ease-out)',
        drawer: 'var(--ease-drawer)',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
      animation: {
        shimmer: 'shimmer 2.4s linear infinite',
      },
    },
  },
  plugins: [],
}
