import { useEffect, useState } from 'react'

// Three routes don't need a router: /, /judges and /session/<id>.
export function usePath(): string {
  const [path, setPath] = useState(window.location.pathname)
  useEffect(() => {
    const on = () => setPath(window.location.pathname)
    window.addEventListener('popstate', on)
    return () => window.removeEventListener('popstate', on)
  }, [])
  return path
}

export function go(to: string) {
  // Remember where the visitor came from, so a page can offer "back" to it (e.g. the judges' tour).
  window.history.pushState({ from: window.location.pathname }, '', to + window.location.search)
  window.dispatchEvent(new PopStateEvent('popstate'))
  window.scrollTo(0, 0)
}

export const sessionHref = (id: string) => `/session/${encodeURIComponent(id)}`

export function link(to: string) {
  return {
    href: to,
    onClick: (e: React.MouseEvent) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return
      e.preventDefault()
      go(to)
    },
  }
}

/* The in-app page this one was opened from, if any (read once, when the page mounts). */
export const cameFrom = (): string | undefined => (window.history.state as { from?: string } | null)?.from
