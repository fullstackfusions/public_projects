import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToString } from 'react-dom/server'
import Shell from './components/Shell'
import type { Session } from './lib/api'
import Judges from './pages/Judges'
import Overview from './pages/Overview'

/* Build-time render of the pages that must read without JavaScript (crawlers, the hackathon's
   AI scorer): the overview and /judges, with the session list as it was at deploy time.
   The browser replaces this markup when the app starts (main.tsx seeds the same data). */
export function render(sessions: Session[]): { home: string; judges: string } {
  const page = (node: React.ReactNode) => {
    const client = new QueryClient()
    client.setQueryData(['sessions'], sessions)
    return renderToString(
      <QueryClientProvider client={client}>
        <Shell>{node}</Shell>
      </QueryClientProvider>,
    )
  }
  return { home: page(<Overview />), judges: page(<Judges />) }
}
