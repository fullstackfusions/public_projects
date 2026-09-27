import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

const client = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })

// Sessions baked into the page at deploy time (prerender.mjs): show them at once, refresh behind.
const seed = document.getElementById('seed')?.textContent
if (seed) client.setQueryData(['sessions'], JSON.parse(seed), { updatedAt: 0 })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
