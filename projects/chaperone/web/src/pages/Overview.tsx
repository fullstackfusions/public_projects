import { ArrowRight, Bot, User } from 'lucide-react'
import { useSessions, type Session } from '../lib/api'
import { actorName, duration, when } from '../lib/format'
import { link, sessionHref } from '../lib/nav'
import AgentReview from '../components/AgentReview'
import { RISK_ORDER, RiskBadge, riskOf } from '../lib/risk'

export default function Overview() {
  const q = useSessions()
  if (q.isLoading) return <p className="py-20 text-center text-subtle">Loading recorded sessions…</p>
  if (q.error || !q.data) return <p className="py-20 text-center text-risk-destructive">{q.error?.message}</p>

  const sessions = q.data
  const agents = sessions.filter((s) => s.agent)
  const calls = sessions.reduce((n, s) => n + s.api_calls, 0)
  const agentCalls = agents.reduce((n, s) => n + s.api_calls, 0)
  const risky = sessions.reduce((n, s) => n + Object.entries(s.risk_counts).filter(([r]) => riskOf(r).severity >= 2).reduce((a, [, c]) => a + (c ?? 0), 0), 0)
  const worst = [...agents].sort((a, b) => riskOf(b.risk).severity - riskOf(a.risk).severity)[0]
  // Where a first-time visitor should start: the agent session with the most MCP tool calls.
  const start = [...agents].sort((a, b) => b.tool_calls - a.tool_calls)[0]

  return (
    <div className="space-y-10">
      <section className="max-w-3xl pt-4">
        <h1 className="text-3xl font-semibold tracking-tight text-text-strong sm:text-4xl">
          What did the agent do in your AWS account?
        </h1>
        <p className="mt-3 text-lg text-muted">
          Every AWS call an AI coding agent makes, from CloudTrail: grouped into sessions, split from what people did, checked
          against risk rules, and turned into the permissions it actually needed.
        </p>
        <p className="mt-3 text-sm text-subtle">
          Every session below is real, recorded by CloudTrail: Claude Code building Chaperone through the AWS MCP
          Server, and the person working beside it. Identifiers are masked, so the account shows as{' '}
          <span className="font-mono">111122223333</span>, AWS's documentation placeholder.
        </p>
        <a
          {...link('/judges')}
          className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-primary underline underline-offset-2"
        >
          Judging this entry? Start with the judges' guide <ArrowRight size={15} />
        </a>
      </section>

      <section aria-label="The agent reviews itself">
        <h2 className="mb-3 text-lg font-semibold text-text-strong">The agent asks Chaperone about its own work</h2>
        <AgentReview />
      </section>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Headline numbers">
        <Stat label="Sessions recorded" value={sessions.length} note={`${agents.length} by an AI agent`} />
        <Stat label="AWS calls" value={calls} note={`${agentCalls.toLocaleString()} by the agent`} />
        <Stat label="Risky calls" value={risky} note="destructive, identity, public or audit" />
        <div className="rounded-xl bg-surface-1 p-4">
          <div className="text-sm text-subtle">Riskiest agent session</div>
          <div className="mt-2">{worst && <RiskBadge risk={worst.risk} />}</div>
          <div className="mt-1 truncate text-sm text-muted">{worst?.reasons[0] ?? '—'}</div>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-text-strong">Sessions</h2>
        <ul className="space-y-2">
          {sessions.map((s) => (
            <SessionRow key={s.session_id} s={s} start={s === start} />
          ))}
        </ul>
      </section>
    </div>
  )
}

function Stat({ label, value, note }: { label: string; value: number; note: string }) {
  return (
    <div className="rounded-xl bg-surface-1 p-4">
      <div className="text-sm text-subtle">{label}</div>
      <div className="num mt-1 text-3xl font-semibold text-text-strong">{value.toLocaleString()}</div>
      <div className="mt-1 text-sm text-muted">{note}</div>
    </div>
  )
}

function SessionRow({ s, start }: { s: Session; start: boolean }) {
  const who = actorName(s.actor)
  const total = Object.values(s.risk_counts).reduce((a, b) => a + (b ?? 0), 0) || 1
  const Icon = s.agent ? Bot : User
  return (
    <li>
      <a
        {...link(sessionHref(s.session_id))}
        className="grid grid-cols-[2.25rem_1fr] gap-x-3 gap-y-2 rounded-xl bg-surface-1 p-4 hover:bg-surface-2 md:grid-cols-[2.25rem_minmax(0,14rem)_minmax(0,1fr)_12rem_11rem] md:items-center"
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-2 text-primary" aria-label={s.agent ? 'AI agent' : 'Person'}>
          <Icon size={18} />
        </span>
        <span className="min-w-0">
          <span className="block truncate font-medium text-text-strong">{who.name}</span>
          <span className="block truncate text-sm text-subtle">
            {s.agent ? 'AI agent' : 'Person'} · {who.detail}
          </span>
          {start && (
            <span className="mt-1 inline-block rounded-md bg-primary/15 px-1.5 py-0.5 text-xs font-medium text-primary">
              Start here
            </span>
          )}
        </span>
        {/* risk strip: share of calls in each class */}
        <span className="col-span-2 md:col-span-1">
          <span className="flex h-2.5 w-full overflow-hidden rounded-full bg-surface-2" aria-hidden>
            {RISK_ORDER.map((r) => {
              const n = s.risk_counts[r] ?? 0
              if (!n) return null
              return <span key={r} style={{ width: `${Math.max(1.5, (n / total) * 100)}%`, background: riskOf(r).color }} />
            })}
          </span>
          <span className="num mt-1.5 block text-sm text-muted">
            {s.api_calls.toLocaleString()} AWS calls
            {s.tool_calls > 0 && ` · ${s.tool_calls} MCP tool calls`}
          </span>
          {s.headline && <span className="mt-1 block text-sm text-text">{s.headline}</span>}
        </span>
        <span className="col-start-2 md:col-start-auto">
          <RiskBadge risk={s.risk} />
        </span>
        <span className="num col-start-2 text-sm text-subtle md:col-start-auto md:text-right">
          {when(s.start)}
          <br />
          {duration(s.start, s.end)}
        </span>
      </a>
    </li>
  )
}
