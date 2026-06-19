import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const schedulerTarget = process.env.SCHEDULER_API_PROXY_TARGET ?? 'http://localhost:8000'
const todoTarget = process.env.TODO_API_PROXY_TARGET ?? 'http://localhost:8080'
const financeTarget = process.env.FINANCE_API_PROXY_TARGET ?? 'http://localhost:8001'
const taxTarget = process.env.TAX_API_PROXY_TARGET ?? 'http://localhost:8007'
const notificationTarget = process.env.NOTIFICATION_API_PROXY_TARGET ?? 'http://localhost:8008'

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    force: true,
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/scheduler-api': {
        target: schedulerTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/scheduler-api/, ''),
      },
      '/todo-api': {
        target: todoTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/todo-api/, ''),
      },
      '/finance-api': {
        target: financeTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/finance-api/, ''),
      },
      '/tax-api': {
        target: taxTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/tax-api/, ''),
      },
      '/notification-api': {
        target: notificationTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/notification-api/, ''),
      },
    },
  },
})
