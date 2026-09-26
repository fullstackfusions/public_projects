import { X } from 'lucide-react'
import { useEffect } from 'react'
import { useEvent } from '../lib/api'
import { clock, viaLabel } from '../lib/format'
import { RiskBadge } from '../lib/risk'
import type { Placed } from './FlightPath'

/* One call: the rule that fired, why, and the raw event (masked by the API). */
export default function EventDrawer({ sessionId, p, onClose }: { sessionId: string; p: Placed; onClose: () => void }) {
  const raw = useEvent(sessionId, p.mark.event_id)
  const m = p.mark
  // Focus stays on the flight path so the arrow keys keep stepping; Escape closes from anywhere.
  useEffect(() => {
    const on = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', on)
    return () => window.removeEventListener('keydown', on)
  }, [onClose])

  let params: unknown = null
  const text = raw.data?.params
  if (typeof text === 'string') {
    try {
      params = JSON.parse(text)
    } catch {
      params = text
    }
  }

  return (
    <aside
      aria-label="Call details"
      className="fixed inset-y-0 right-0 z-30 flex w-full max-w-md flex-col border-l border-surface-3 bg-surface-2 shadow-2xl"
    >
      <div className="flex items-start justify-between gap-3 border-b border-surface-3 p-5">
        <div className="min-w-0">
          <div className="num text-sm text-subtle">
            {clock(m.time)} UTC · {m.region}
          </div>
          <h2 className="mt-1 font-mono text-lg break-all text-text-strong">{m.api}</h2>
          <div className="mt-2">
            <RiskBadge risk={m.risk} />
          </div>
        </div>
        <button onClick={onClose} className="rounded-md p-1.5 text-muted hover:bg-surface-3" aria-label="Close">
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto p-5 text-sm">
        <dl className="grid grid-cols-[7rem_1fr] gap-x-3 gap-y-2">
          <dt className="text-subtle">Why</dt>
          <dd>{m.reasons?.length ? m.reasons.join('; ') : m.risk === 'read' ? 'Reads only: no rule fired.' : 'Changes something: a plain write.'}</dd>
          <dt className="text-subtle">Channel</dt>
          <dd>{p.lane === 'people' ? 'A person, in the console' : viaLabel(m.via)}</dd>
          {p.tool && (
            <>
              <dt className="text-subtle">MCP tool call</dt>
              <dd>
                <span className="font-mono">{p.tool.tool}</span> at {clock(p.tool.time)}, {p.tool.calls?.length} AWS calls
              </dd>
            </>
          )}
          {m.target && (
            <>
              <dt className="text-subtle">Acts on</dt>
              <dd className="break-all">{m.target}</dd>
            </>
          )}
          {m.creates && (
            <>
              <dt className="text-subtle">Creates</dt>
              <dd className="break-all">{m.creates.join(', ')}</dd>
            </>
          )}
          {m.deletes && (
            <>
              <dt className="text-subtle">Deletes</dt>
              <dd className="break-all">{m.deletes.join(', ')}</dd>
            </>
          )}
          {m.error && (
            <>
              <dt className="text-subtle">Result</dt>
              <dd>
                {m.error === 'denied' ? 'Denied' : m.error === 'not_found' ? 'Not found (still allowed)' : 'Failed'}
                {m.error_code && <span className="font-mono text-muted"> · {m.error_code}</span>}
              </dd>
            </>
          )}
          {m.kind === 'UNSEEN' && (
            <>
              <dt className="text-subtle">Note</dt>
              <dd>Reported by the MCP server but not in the trail (a data event, like s3:PutObject).</dd>
            </>
          )}
        </dl>

        {m.event_id && m.kind !== 'UNSEEN' && (
          <section>
            <h3 className="mb-2 font-semibold text-text">Recorded event</h3>
            {raw.isLoading && <p className="text-subtle">Loading…</p>}
            {raw.error && <p className="text-risk-destructive">{String(raw.error.message)}</p>}
            {raw.data && (
              <>
                {params !== null && (
                  <>
                    <div className="mb-1 text-subtle">Request parameters</div>
                    <pre className="mb-3 max-h-72 overflow-auto rounded-lg bg-bg p-3 font-mono text-xs leading-relaxed text-text">
                      {JSON.stringify(params, null, 2)}
                    </pre>
                  </>
                )}
                <div className="mb-1 text-subtle">User agent</div>
                <p className="mb-3 font-mono text-xs break-all text-muted">{String(raw.data.user_agent ?? '—')}</p>
                <p className="text-xs text-subtle">
                  Account, IP addresses, identity IDs, keys and request IDs are masked on this public site.
                </p>
              </>
            )}
          </section>
        )}
      </div>
    </aside>
  )
}
