import { useEffect, useState } from 'react'

// Two routes don't need a router: / and /session/<id>.
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
  window.history.pushState(null, '', to + window.location.search)
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
