/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        court: {
          dark: '#0a0d14',
          card: '#111726',
          border: '#1e293b',
          accent: '#6366f1',
          gold: '#f59e0b',
        }
      }
    },
  },
  plugins: [],
}
