import { useState } from 'react'
import type { Risk } from '../lib/api'
import { clock, t, viaLabel } from '../lib/format'
import { RISK, RISK_ORDER, riskOf } from '../lib/risk'
import type { Placed } from './FlightPath'

/* Every call that isn't a read, riskiest first; filterable by class (screen 4). */
export default function Findings({ placed, onSelect }: { placed: Placed[]; onSelect: (p: Placed) => void }) {
  const rows = placed.filter((p) => p.lane !== 'people' && riskOf(p.mark.risk).severity > 0)
  const classes = RISK_ORDER.filter((r) => r !== 'read' && rows.some((p) => p.mark.risk === r)).reverse()
  const [only, setOnly] = useState<Risk | null>(null)
  const shown = collapse(
    rows
      .filter((p) => !only || p.mark.risk === only)
      .sort((a, b) => riskOf(b.mark.risk).severity - riskOf(a.mark.risk).severity || a.mark.time.localeCompare(b.mark.time)),
  )

  if (!rows.length) return <p className="text-muted">Only reads in this session: nothing changed.</p>

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2" role="group" aria-label="Filter by risk class">
        <Chip on={!only} onClick={() => setOnly(null)}>
          All <span className="num">{rows.length}</span>
        </Chip>
        {classes.map((r) => {
          const m = RISK[r]
          return (
            <Chip key={r} on={only === r} onClick={() => setOnly(only === r ? null : r)} color={m.color}>
              <m.Icon size={14} aria-hidden /> {m.label} <span className="num">{rows.filter((p) => p.mark.risk === r).length}</span>
            </Chip>
          )
        })}
      </div>
      <div className="overflow-hidden rounded-xl bg-surface-1">
        <div
          className="hidden grid-cols-[5rem_10.5rem_minmax(12rem,1.1fr)_minmax(0,1.4fr)_minmax(9rem,0.8fr)] gap-x-4 border-b border-surface-2 px-4 py-2 text-xs font-medium tracking-wide text-subtle uppercase lg:grid"
          aria-hidden
        >
          <span>Time</span>
          <span>Risk</span>
          <span>Call</span>
          <span>Acts on</span>
          <span>Channel</span>
        </div>
        <ul className="divide-y divide-surface-2">
          {shown.slice(0, 200).map(({ p, count, last }) => {
            const m = riskOf(p.mark.risk)
            return (
              <li key={p.uid}>
                <button
                  onClick={() => onSelect(p)}
                  className="grid w-full grid-cols-[4.5rem_minmax(0,1fr)] gap-x-3 gap-y-1 px-4 py-3 text-left text-sm hover:bg-surface-2 lg:grid-cols-[5rem_10.5rem_minmax(12rem,1.1fr)_minmax(0,1.4fr)_minmax(9rem,0.8fr)] lg:items-baseline lg:gap-x-4"
                >
                  <span className="num text-subtle" title={count > 1 ? `${clock(p.mark.time)} to ${clock(last)}` : undefined}>
                    {clock(p.mark.time)}
                  </span>
                  <span className="inline-flex items-center gap-1.5 font-medium" style={{ color: m.color }}>
                    <m.Icon size={15} aria-hidden className="shrink-0" /> {m.label}
                  </span>
                  <span className="col-start-2 font-mono break-all text-text-strong lg:col-start-auto">
                    {p.mark.api}
                    {count > 1 && <span className="num ml-2 font-sans text-muted">×{count}</span>}
                  </span>
                  <span className="col-start-2 break-words text-muted lg:col-start-auto [overflow-wrap:anywhere]">
                    {p.mark.target ?? p.mark.reasons?.[0] ?? '—'}
                  </span>
                  <span className="col-start-2 break-words text-subtle lg:col-start-auto">
                    {p.tool ? (
                      <>
                        MCP · <span className="font-mono">{p.tool.tool}</span>
                      </>
                    ) : (
                      viaLabel(p.mark.via)
                    )}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      </div>
      {shown.length > 200 && <p className="mt-2 text-sm text-subtle">Showing the first 200 of {shown.length}.</p>}
    </div>
  )
}

/* Terraform applies one resource in many regions within seconds: the same call on the
   same target becomes one row with a count (the flight path still shows every call). */
function collapse(rows: Placed[]): { p: Placed; count: number; last: string }[] {
  const out: { p: Placed; count: number; last: string }[] = []
  const open = new Map<string, (typeof out)[number]>()
  for (const p of rows) {
    const key = [p.mark.risk, p.mark.api, p.mark.target, p.tool ? 'mcp' : p.mark.via, p.mark.error].join('|')
    const g = open.get(key)
    if (g && t(p.mark.time) - t(g.last) <= 120_000) {
      g.count += 1
      g.last = p.mark.time
    } else {
      const row = { p, count: 1, last: p.mark.time }
      open.set(key, row)
      out.push(row)
    }
  }
  return out
}

function Chip({ on, onClick, color, children }: { on: boolean; onClick: () => void; color?: string; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={on}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm ${
        on ? 'border-primary bg-surface-2' : 'border-surface-3 hover:bg-surface-2'
      }`}
      style={{ color: color ?? 'var(--color-text)' }}
    >
      {children}
    </button>
  )
}
