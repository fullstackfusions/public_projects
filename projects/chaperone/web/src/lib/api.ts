import { useQuery, type QueryClient } from '@tanstack/react-query'

export type Risk = 'read' | 'write' | 'destructive' | 'public_exposure' | 'identity_escalation' | 'audit_tampering'

export interface Session {
  session_id: string
  actor: string
  actor_type: 'agent' | 'human' | 'service' | null
  agent: boolean
  operated_by: Record<string, number>
  flags: string[]
  start: string
  end: string
  tool_calls: number
  api_calls: number
  signins: number
  denied: number
  errors: number
  risk: Risk
  reasons: string[]
  risk_counts: Partial<Record<Risk, number>>
  headline?: string
}

export interface Explanation {
  session_id: string
  status: 'READY' | 'STALE' | 'NOT_GENERATED'
  model?: string
  generated_at?: string
  headline?: string
  summary?: string
  moments?: { time: string; text: string }[]
  risk?: string
  access?: string
}

export interface Mark {
  time: string
  kind: 'API' | 'TOOL' | 'UNSEEN'
  api: string | null
  risk: Risk
  via?: string
  region?: string
  event_id?: string
  reasons?: string[]
  error?: 'denied' | 'not_found' | 'other'
  error_code?: string
  target?: string
  creates?: string[]
  deletes?: string[]
  operated_by?: string
  tool?: string
  calls?: Mark[]
}

export interface Replay {
  session: Session
  marks: Mark[]
}

export interface LeastPrivilege {
  session_id: string
  preview: {
    actions: string[]
    by_service: Record<string, string[]>
    passed_roles: string[]
    by_aws_services: string[]
    denied_attempts: string[]
    policy: unknown
  }
  access_analyzer: { status: string; started_at?: string; policies?: string[] }
  comparison?: {
    shared: number
    only_chaperone: string[]
    only_access_analyzer: string[]
    service_level_only: string[]
    missed_by_both_recovered: string[]
  }
}

async function get<T>(path: string, params: Record<string, string> = {}): Promise<T> {
  const qs = new URLSearchParams(params).toString()
  const r = await fetch(`/api/${path}${qs ? `?${qs}` : ''}`)
  if (!r.ok) {
    const body = await r.json().catch(() => ({}))
    throw new Error(body.error ?? `${r.status} ${r.statusText}`)
  }
  return r.json() as Promise<T>
}

const minutes = 60_000

export const useSessions = () =>
  useQuery({ queryKey: ['sessions'], queryFn: () => get<Session[]>('sessions'), staleTime: minutes })

const replayQuery = (id: string) =>
  ({ queryKey: ['replay', id], queryFn: () => get<Replay>('replay', { id }), staleTime: 5 * minutes })

export const useReplay = (id: string) => useQuery(replayQuery(id))

export const useEvent = (id: string, event: string | undefined) =>
  useQuery({
    queryKey: ['event', id, event],
    queryFn: () => get<Record<string, unknown>>('event', { id, event: event! }),
    enabled: !!event,
    staleTime: Infinity,
  })

const leastPrivilegeQuery = (id: string) => ({
  queryKey: ['least-privilege', id],
  queryFn: () => get<LeastPrivilege>('least-privilege', { id }),
  staleTime: 5 * minutes,
})

export const useLeastPrivilege = (id: string) => useQuery(leastPrivilegeQuery(id))

const explanationQuery = (id: string) => ({
  queryKey: ['explain', id],
  queryFn: () => get<Explanation>('explain', { id }),
  staleTime: 5 * minutes,
})

export const useExplanation = (id: string) => useQuery(explanationQuery(id))

/* Start loading a session page's data before the visitor opens it. */
export function prefetchSession(client: QueryClient, id: string) {
  void client.prefetchQuery(replayQuery(id))
  void client.prefetchQuery(explanationQuery(id))
  void client.prefetchQuery(leastPrivilegeQuery(id))
}
