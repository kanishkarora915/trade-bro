/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        tb: {
          bg: '#050508',
          card: '#0c0c12',
          surface: '#12121a',
          border: '#1a1a2e',
          text: '#e8e8f0',
          muted: '#6b6b80',
          accent: '#00e5ff',
        },
        neon: {
          green: '#00ff88',
          red: '#ff2244',
          yellow: '#ffd700',
          orange: '#ff8c00',
          blue: '#3388ff',
          cyan: '#00e5ff',
          purple: '#aa66ff',
        },
      },
      fontFamily: {
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      animation: {
        'pulse-dot': 'pulseDot 1.5s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        pulseDot: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.4', transform: 'scale(0.8)' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 5px rgba(0,229,255,0.2)' },
          '50%': { boxShadow: '0 0 20px rgba(0,229,255,0.4)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
