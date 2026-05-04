/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        neon: {
          blue: '#00d4ff',
          purple: '#a855f7',
          pink: '#ec4899',
          cyan: '#22d3ee',
          green: '#10b981',
        },
        cyber: {
          black: '#0a0a0f',
          dark: '#0f0f1a',
          card: '#14141f',
          border: '#1e1e2e',
          lighter: '#1a1a2e',
          muted: '#6b7280',
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', 'ui-monospace', 'Consolas', 'monospace'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        display: ['"Space Grotesk"', '"Inter"', 'sans-serif'],
      },
      backgroundImage: {
        'neon-gradient': 'linear-gradient(135deg, #00d4ff, #a855f7, #ec4899)',
        'neon-glow': 'linear-gradient(135deg, rgba(0,212,255,0.15), rgba(168,85,247,0.15))',
        'cyber-card': 'linear-gradient(180deg, rgba(20,20,31,0.9), rgba(15,15,26,0.95))',
      },
      boxShadow: {
        'neon-blue': '0 0 15px rgba(0,212,255,0.3), 0 0 30px rgba(0,212,255,0.1)',
        'neon-purple': '0 0 15px rgba(168,85,247,0.3), 0 0 30px rgba(168,85,247,0.1)',
        'neon-pink': '0 0 15px rgba(236,72,153,0.3), 0 0 30px rgba(236,72,153,0.1)',
        'neon-card': '0 0 20px rgba(168,85,247,0.08), 0 0 40px rgba(0,212,255,0.04)',
      },
      animation: {
        'pulse-neon': 'pulse-neon 2s ease-in-out infinite',
        'glow': 'glow 3s ease-in-out infinite alternate',
        'slide-up': 'slide-up 0.3s ease-out',
        'fade-in': 'fade-in 0.4s ease-out',
      },
      keyframes: {
        'pulse-neon': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'glow': {
          '0%': { boxShadow: '0 0 5px rgba(0,212,255,0.2), 0 0 10px rgba(168,85,247,0.1)' },
          '100%': { boxShadow: '0 0 15px rgba(0,212,255,0.4), 0 0 30px rgba(168,85,247,0.2)' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
