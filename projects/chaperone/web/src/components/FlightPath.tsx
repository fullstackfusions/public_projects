import { useEffect, useMemo, useRef, useState } from 'react'
import type { Mark } from '../lib/api'
import { clock, t, viaLabel } from '../lib/format'
import { riskOf } from '../lib/risk'

/* The flight path (chaperone.md, screen 2): time left to right, one lane per channel the
   actor used, each AWS call a mark whose height and colour are its risk class. MCP tool
   calls are bands, with the calls they made inside. People working at the same time get
   their own lane below. Drag to zoom; arrow keys step through the calls that aren't reads. */

export interface Placed {
  uid: number // unique per placed mark (UNSEEN calls have no event ID)
  mark: Mark
  lane: string
  tool?: Mark // the MCP tool call this API call was made through
}

interface Lane {
  key: string
  label: string
  sub?: string
}

const LANE_H = 58
const LABEL_W = 168
const AXIS_H = 28
const HEIGHT = [0.26, 0.5, 0.74, 1] // by severity

function laneOf(m: Mark): string {
  if (m.via?.startsWith('service:')) return 'service'
  return m.via ?? 'other'
}

export function place(marks: Mark[], people: Mark[] = []): { placed: Placed[]; tools: Mark[] } {
  const placed: Placed[] = []
  const tools: Mark[] = []
  for (const m of marks) {
    if (m.kind === 'TOOL') {
      tools.push(m)
      for (const c of m.calls ?? []) placed.push({ uid: placed.length, mark: { ...c, time: c.time ?? m.time }, lane: 'mcp', tool: m })
    } else placed.push({ uid: placed.length, mark: m, lane: laneOf(m) })
  }
  for (const m of people) placed.push({ uid: placed.length, mark: m, lane: 'people' })
  placed.sort((a, b) => t(a.mark.time) - t(b.mark.time))
  return { placed, tools }
}

const LANE_ORDER = ['mcp', 'terraform', 'cli', 'sdk', 'console', 'service', 'other', 'people']

function lanesFor(placed: Placed[], tools: Mark[], agent: boolean): Lane[] {
  const seen = new Set(placed.map((p) => p.lane))
  if (tools.length) seen.add('mcp')
  return LANE_ORDER.filter((k) => seen.has(k)).map((key) => {
    if (key === 'mcp') return { key, label: 'AWS MCP server', sub: `${tools.length} tool calls` }
    if (key === 'service') return { key, label: 'AWS services', sub: agent ? 'acting for the agent' : 'acting for the actor' }
    if (key === 'people') return { key, label: 'People', sub: 'console, same time' }
    return { key, label: viaLabel(key), sub: agent ? 'run by the agent' : undefined }
  })
}

function ticks(from: number, to: number, px: number): number[] {
  const span = to - from
  const steps = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200].map((s) => s * 1000)
  const step = steps.find((s) => (span / s) * 90 <= px) ?? steps[steps.length - 1]
  const out = []
  for (let x = Math.ceil(from / step) * step; x <= to; x += step) out.push(x)
  return out
}

export default function FlightPath({
  marks,
  people,
  agent,
  selected,
  onSelect,
}: {
  marks: Mark[]
  people?: Mark[]
  agent: boolean
  selected?: Placed
  onSelect: (p: Placed | undefined) => void
}) {
  const wrap = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(1100)
  const [zoom, setZoom] = useState<[number, number] | null>(null)
  const [drag, setDrag] = useState<[number, number] | null>(null)
  const [hover, setHover] = useState<Placed | null>(null)

  useEffect(() => {
    const el = wrap.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(560, e.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const { placed, tools } = useMemo(() => place(marks, people), [marks, people])
  const lanes = useMemo(() => lanesFor(placed, tools, agent), [placed, tools, agent])
  const notable = useMemo(() => placed.filter((p) => riskOf(p.mark.risk).severity > 0 || p.mark.error === 'denied'), [placed])

  const agentPlaced = placed.filter((p) => p.lane !== 'people')
  const full: [number, number] = agentPlaced.length
    ? [t(agentPlaced[0].mark.time), t(agentPlaced[agentPlaced.length - 1].mark.time)]
    : [0, 1]
  const pad = Math.max(1000, (full[1] - full[0]) * 0.015)
  const [from, to] = zoom ?? [full[0] - pad, full[1] + pad]
  const plotW = width - LABEL_W - 16
  const x = (ms: number) => LABEL_W + ((ms - from) / (to - from)) * plotW
  const msAt = (px: number) => from + ((px - LABEL_W) / plotW) * (to - from)
  const laneY = (key: string) => AXIS_H + lanes.findIndex((l) => l.key === key) * LANE_H
  const height = AXIS_H + lanes.length * LANE_H + 8
  const visible = placed.filter((p) => {
    const ms = t(p.mark.time)
    return ms >= from && ms <= to
  })
  const barW = Math.max(1.5, Math.min(6, plotW / Math.max(1, visible.length) / 1.6))

  // Icons over marks above plain writes, thinned so they never overlap within a lane.
  const icons: Placed[] = []
  const lastIcon: Record<string, number> = {}
  for (const p of visible) {
    if (riskOf(p.mark.risk).severity < 2) continue
    const px = x(t(p.mark.time))
    if (lastIcon[p.lane] !== undefined && px - lastIcon[p.lane] < 18) continue
    lastIcon[p.lane] = px
    icons.push(p)
  }

  const nearest = (clientX: number, clientY: number): Placed | null => {
    const box = wrap.current!.getBoundingClientRect()
    const px = clientX - box.left
    const py = clientY - box.top
    const lane = lanes[Math.floor((py - AXIS_H) / LANE_H)]
    if (!lane || px < LABEL_W) return null
    let best: Placed | null = null
    let dist = 10
    for (const p of visible) {
      if (p.lane !== lane.key) continue
      const d = Math.abs(x(t(p.mark.time)) - px) - riskOf(p.mark.risk).severity // prefer riskier on ties
      if (d < dist) {
        dist = d
        best = p
      }
    }
    return best
  }

  const step = (dir: 1 | -1) => {
    const list = notable.length ? notable : placed
    const i = selected ? list.findIndex((p) => p.uid === selected.uid && p.lane === selected.lane) : -1
    const next = list[Math.min(list.length - 1, Math.max(0, i + dir))]
    if (!next) return
    onSelect(next)
    const ms = t(next.mark.time)
    if (zoom && (ms < zoom[0] || ms > zoom[1])) {
      const half = (zoom[1] - zoom[0]) / 2
      setZoom([ms - half, ms + half])
    }
  }

  return (
    <div className="relative overflow-x-auto">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm text-subtle">
        <span>
          Drag across the chart to zoom. <kbd className="font-mono text-muted">←</kbd>{' '}
          <kbd className="font-mono text-muted">→</kbd> step through the {notable.length.toLocaleString()} calls that
          aren't reads.
        </span>
        {zoom && (
          <button className="rounded-md border border-surface-3 px-2.5 py-1 text-primary hover:bg-surface-2" onClick={() => setZoom(null)}>
            Show the whole session
          </button>
        )}
      </div>
      <div
        ref={wrap}
        tabIndex={0}
        role="application"
        aria-label={`Flight path: ${placed.length} AWS calls across ${lanes.length} channels. Arrow keys step through calls that aren't reads.`}
        className="relative w-full cursor-crosshair select-none rounded-xl bg-surface-1"
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight') step(1)
          else if (e.key === 'ArrowLeft') step(-1)
          else if (e.key === 'Escape') onSelect(undefined)
          else return
          e.preventDefault()
        }}
        onPointerDown={(e) => {
          const px = e.clientX - wrap.current!.getBoundingClientRect().left
          if (px >= LABEL_W) setDrag([px, px])
        }}
        onPointerMove={(e) => {
          const px = e.clientX - wrap.current!.getBoundingClientRect().left
          if (drag) setDrag([drag[0], px])
          setHover(nearest(e.clientX, e.clientY))
        }}
        onPointerLeave={() => {
          setHover(null)
          setDrag(null)
        }}
        onPointerUp={(e) => {
          if (drag && Math.abs(drag[1] - drag[0]) > 8) {
            const [a, b] = [Math.min(...drag), Math.max(...drag)].map(msAt)
            setZoom([a, Math.max(b, a + 2000)])
          } else {
            const hit = nearest(e.clientX, e.clientY)
            onSelect(hit ?? undefined)
          }
          setDrag(null)
        }}
      >
        <svg width={width} height={height} className="block" aria-hidden>
          {/* time axis */}
          {ticks(from, to, plotW).map((ms) => (
            <g key={ms}>
              <line x1={x(ms)} x2={x(ms)} y1={AXIS_H - 6} y2={height - 8} stroke="var(--color-surface-3)" strokeWidth={1} />
              <text x={x(ms)} y={AXIS_H - 11} textAnchor="middle" className="num" fontSize={11} fill="var(--color-subtle)">
                {clock(new Date(ms).toISOString()).slice(0, (to - from) < 180_000 ? 8 : 5)}
              </text>
            </g>
          ))}

          {lanes.map((l, i) => (
            <g key={l.key}>
              {i > 0 && <line x1={0} x2={width} y1={laneY(l.key)} y2={laneY(l.key)} stroke="var(--color-surface-2)" />}
              <text x={16} y={laneY(l.key) + 24} fontSize={13} fontWeight={600} fill="var(--color-text)">
                {l.label}
              </text>
              {l.sub && (
                <text x={16} y={laneY(l.key) + 41} fontSize={11} fill="var(--color-subtle)">
                  {l.sub}
                </text>
              )}
            </g>
          ))}

          {/* MCP tool calls: a band from the first to the last call it made */}
          {tools.map((tool, i) => {
            const times = [tool.time, ...(tool.calls ?? []).map((c) => c.time)].filter(Boolean).map(t)
            const a = x(Math.min(...times))
            const b = x(Math.max(...times))
            if (b < LABEL_W || a > width) return null
            const y = laneY('mcp')
            return (
              <rect
                key={tool.event_id ?? i}
                x={Math.max(LABEL_W, a - 3)}
                y={y + 6}
                width={Math.max(6, b - a + 6)}
                height={LANE_H - 12}
                rx={4}
                fill="var(--color-surface-2)"
                stroke={selected?.tool === tool ? 'var(--color-primary)' : 'var(--color-surface-3)'}
              />
            )
          })}

          {/* marks: reads first, riskier on top */}
          {[...visible]
            .sort((a, b) => riskOf(a.mark.risk).severity - riskOf(b.mark.risk).severity)
            .map((p) => {
              const m = riskOf(p.mark.risk)
              const h = (LANE_H - 18) * HEIGHT[m.severity]
              const base = laneY(p.lane) + LANE_H - 9
              return (
                <rect
                  key={p.uid}
                  x={x(t(p.mark.time)) - barW / 2}
                  y={base - h}
                  width={barW}
                  height={h}
                  fill={m.color}
                  opacity={m.severity === 0 ? 0.45 : 0.95}
                />
              )
            })}

          {icons.map((p) => {
            const m = riskOf(p.mark.risk)
            return (
              <m.Icon
                key={`i-${p.uid}`}
                x={x(t(p.mark.time)) - 7}
                y={laneY(p.lane) + 1}
                width={14}
                height={14}
                color={m.color}
                strokeWidth={2.4}
              />
            )
          })}

          {selected && t(selected.mark.time) >= from && t(selected.mark.time) <= to && (
            <rect
              x={x(t(selected.mark.time)) - 5}
              y={laneY(selected.lane) + 3}
              width={10}
              height={LANE_H - 6}
              rx={3}
              fill="none"
              stroke="var(--color-primary)"
              strokeWidth={2}
            />
          )}

          {drag && (
            <rect
              x={Math.min(...drag)}
              y={AXIS_H}
              width={Math.abs(drag[1] - drag[0])}
              height={height - AXIS_H - 8}
              fill="var(--color-primary)"
              opacity={0.12}
            />
          )}
        </svg>

        {hover && !drag && <Tip p={hover} left={x(t(hover.mark.time))} top={laneY(hover.lane)} width={width} />}
      </div>
    </div>
  )
}

function Tip({ p, left, top, width }: { p: Placed; left: number; top: number; width: number }) {
  const m = riskOf(p.mark.risk)
  const flip = left > width - 280
  return (
    <div
      className="pointer-events-none absolute z-10 w-64 rounded-lg border border-surface-3 bg-surface-2 p-2.5 text-sm shadow-xl"
      style={{ left: flip ? left - 272 : left + 12, top: top + 4 }}
    >
      <div className="font-mono text-text-strong break-all">{p.mark.api}</div>
      <div className="mt-1 flex items-center gap-1.5" style={{ color: m.color }}>
        <m.Icon size={14} aria-hidden /> {m.label}
        {p.mark.error && <span className="text-subtle">· {p.mark.error === 'not_found' ? 'not found' : p.mark.error}</span>}
      </div>
      {p.mark.target && <div className="mt-1 truncate text-muted">{p.mark.target}</div>}
      <div className="num mt-1 text-subtle">
        {clock(p.mark.time)} · {p.mark.region} {p.tool ? `· via ${p.tool.tool}` : ''}
      </div>
    </div>
  )
}
