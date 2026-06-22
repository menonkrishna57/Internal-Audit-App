/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'vault-navy':   '#14202B',
        'ledger-slate': '#1E2C3A',
        'aged-paper':   '#DCD3B8',
        'ink':          '#211C16',
        'stamp-red':    '#A23B2C',
        'brass':        '#B08F4F',
      },
      fontFamily: {
        newsreader: ['Newsreader', 'Georgia', 'serif'],
        inter:      ['Inter', 'system-ui', 'sans-serif'],
        mono:       ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
