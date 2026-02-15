/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./static/js/**/*.js"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'primary': '#d4af6a',
        'primary-dark': '#c2ae7f',
        'secondary': '#207487',
        'accent': '#294c5d',
        'zfa-gray': '#77726d',
        't2-purple': '#d4af6a',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'gradient': 'gradient 15s ease infinite',
        'float': 'float 6s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(212,175,106,0.3)' },
          '50%': { boxShadow: '0 0 40px rgba(212,175,106,0.6)' },
        },
      },
    },
  },
  safelist: [
    // Alpine.js :class bindings (dynamic, not detectable by content scan)
    'bg-primary', 'bg-primary/20', 'text-primary',
    'text-white', 'text-white/60', 'text-white/70', 'text-white/80', 'text-white/90',
    'bg-white/5', 'bg-white/10', 'bg-white/20',
    'hover:text-white', 'hover:bg-white/5', 'hover:bg-white/10', 'hover:bg-white/20',
    // Status colors
    'text-success', 'text-warning', 'text-error', 'text-info',
    'bg-success', 'bg-success/20', 'bg-warning', 'bg-warning/20',
    'bg-error', 'bg-error/20', 'bg-info', 'bg-info/20',
    'border-success', 'border-success/40', 'border-warning', 'border-warning/40',
    'border-error', 'border-error/40',
    // DaisyUI badges (dynamically assigned via JS)
    'badge-warning', 'badge-info', 'badge-primary', 'badge-ghost',
    'badge-success', 'badge-error', 'badge-lg', 'badge-sm', 'badge-xs',
    // DaisyUI buttons (dynamic states)
    'btn-primary', 'btn-outline', 'btn-success', 'btn-ghost',
    'btn-disabled', 'btn-active', 'btn-circle', 'btn-sm',
    // Tabs
    'tab-active',
    // Dynamic color variants
    'bg-blue-600', 'bg-pink-600',
    'from-blue-500/20', 'to-cyan-500/20', 'from-pink-500/20', 'to-purple-500/20',
    // Ring utilities
    'ring-2', 'ring-primary', 'ring-success',
    // Layout (sidebar toggle)
    'md:ml-80', '-translate-x-full', 'pointer-events-none',
    // Visual states
    'opacity-50', 'grayscale',
  ],
  plugins: [require('daisyui')],
  daisyui: {
    themes: ["dark", "light"],
  },
}
