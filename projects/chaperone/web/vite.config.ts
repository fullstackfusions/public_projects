import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// /api/* goes to CloudFront -> the API function URL in production; in dev, to dev_proxy.py,
// which signs the same way and asks for the same public (masked) view.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://127.0.0.1:8787' } },
})
