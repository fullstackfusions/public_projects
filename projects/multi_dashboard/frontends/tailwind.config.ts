import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#2563eb',
          dark: '#1d4ed8',
        },
      },
      boxShadow: {
        sidebar: '20px 0 40px rgba(15, 23, 42, 0.35)',
        card: '0 15px 40px rgba(15, 23, 42, 0.08)',
        accent: '0 10px 25px rgba(29, 78, 216, 0.25)',
      },
    },
  },
  plugins: [],
}

export default config
