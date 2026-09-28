import { ArrowLeft, Bot, User } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import EventDrawer from '../components/EventDrawer'
import Explanation from '../components/Explanation'
import Findings from '../components/Findings'
import FlightPath, { place, type Placed } from '../components/FlightPath'
import LeastPrivilege from '../components/LeastPrivilege'
import { useReplay, useSessions, type Mark, type Replay } from '../lib/api'
import { actorName, duration, t, when } from '../lib/format'
import { cameFrom, link } from '../lib/nav'
import { RISK_ORDER, RiskBadge } from '../lib/risk'

export default function SessionPage({ id }: { id: string }) {
  const q = useReplay(id)
  const all = useSessions()
  const [selected, setSelected] = useState<Placed | undefined>()
  const [back] = useState(() => (cameFrom()?.replace(/\/$/, '') === '/judges' ? { to: '/judges', label: 'Back to the judges\' guide' } : { to: '/', label: 'All sessions' }))

  // People in the console while the agent worked: their own lane (chaperone.md, screen 2).
  const overlapping = useMemo(() => {
    const s = q.data?.session
    if (!s || !s.agent || !all.data) return []
    return all.data.filter((o) => !o.agent && t(o.start) <= t(s.end) && t(o.end) >= t(s.start))
  }, [q.data, all.data])
  const people = useQueries({
    queries: overlapping.map((o) => ({
      queryKey: ['replay', o.session_id],
      queryFn: () => fetch(`/api/replay?id=${encodeURIComponent(o.session_id)}`).then((r) => r.json() as Promise<Replay>),
      staleTime: 300_000,
    })),
  })
  const peopleMarks = useMemo(() => {
    const s = q.data?.session
    if (!s) return []
    return people
      .flatMap((p) => p.data?.marks ?? [])
      .filter((m: Mark) => t(m.time) >= t(s.start) && t(m.time) <= t(s.end))
  }, [people, q.data])

  const placed = useMemo(() => (q.data ? place(q.data.marks).placed : []), [q.data])

  if (q.isLoading) return <p className="py-20 text-center text-subtle">Loading the flight path…</p>
  if (q.error || !q.data) return <p className="py-20 text-center text-risk-destructive">{q.error?.message}</p>

  const s = q.data.session
  const who = actorName(s.actor)
  const Icon = s.agent ? Bot : User

  return (
    <div className="space-y-10">
      <a {...link(back.to)} className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
        <ArrowLeft size={15} /> {back.label}
      </a>

      <section className="flex flex-wrap items-start justify-between gap-6">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-2 text-primary">
            <Icon size={24} />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-text-strong">
              {who.name} <span className="font-normal text-muted">· {s.agent ? 'AI agent' : 'person'}</span>
            </h1>
            <p className="num mt-1 text-muted">
              {when(s.start)} · {duration(s.start, s.end)} · {who.detail}
            </p>
            <div className="mt-2">
              <RiskBadge risk={s.risk} />
              {s.reasons[0] && <span className="ml-2 text-sm text-muted">{s.reasons[0]}</span>}
            </div>
          </div>
        </div>
        <dl className="grid grid-cols-3 gap-x-6 gap-y-1 text-sm sm:grid-cols-5">
          <Num label="AWS calls" n={s.api_calls} />
          <Num label="MCP tool calls" n={s.tool_calls} />
          <Num label="Sign-ins" n={s.signins} hint="Identity Center credential fetches, folded into one session" />
          <Num label="Denied" n={s.denied} />
          <Num label="Failed" n={s.errors} />
        </dl>
      </section>

      <Explanation sessionId={id} />

      <section aria-labelledby="fp">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <h2 id="fp" className="text-lg font-semibold text-text-strong">
            Flight path
          </h2>
          <ul className="flex flex-wrap gap-x-4 gap-y-1">
            {RISK_ORDER.filter((r) => s.risk_counts[r]).map((r) => (
              <li key={r}>
                <RiskBadge risk={r} count={s.risk_counts[r]} />
              </li>
            ))}
          </ul>
        </div>
        <FlightPath marks={q.data.marks} people={peopleMarks} agent={s.agent} selected={selected} onSelect={setSelected} />
      </section>

      <section aria-labelledby="lp">
        <h2 id="lp" className="mb-3 text-lg font-semibold text-text-strong">
          The access it actually needed
        </h2>
        <LeastPrivilege sessionId={id} granted={s.actor.includes('AWSReservedSSO_') ? 'AdministratorAccess (Identity Center)' : 'its IAM policies'} />
      </section>

      <section aria-labelledby="fi">
        <h2 id="fi" className="mb-3 text-lg font-semibold text-text-strong">
          Every change, riskiest first
        </h2>
        <Findings placed={placed} onSelect={setSelected} />
      </section>

      {selected && <EventDrawer sessionId={id} p={selected} onClose={() => setSelected(undefined)} />}
    </div>
  )
}

function Num({ label, n, hint }: { label: string; n: number; hint?: string }) {
  return (
    <div title={hint}>
      <dt className="text-subtle">{label}</dt>
      <dd className="num text-xl font-semibold text-text-strong">{n.toLocaleString()}</dd>
    </div>
  )
}
