import { Eye, Globe, KeyRound, Pencil, ShieldOff, Trash2, type LucideIcon } from 'lucide-react'
import type { Risk } from './api'

// State is never colour alone: colour + icon + label (chaperone.md, UX rules).
export interface RiskMeta {
  label: string
  short: string
  color: string // CSS variable, for SVG fills and text on bg / surface-1 / surface-2
  Icon: LucideIcon
  severity: number
}

export const RISK: Record<Risk, RiskMeta> = {
  read: { label: 'Read', short: 'read', color: 'var(--color-risk-read)', Icon: Eye, severity: 0 },
  write: { label: 'Write', short: 'write', color: 'var(--color-risk-write)', Icon: Pencil, severity: 1 },
  destructive: { label: 'Destructive', short: 'delete', color: 'var(--color-risk-destructive)', Icon: Trash2, severity: 2 },
  public_exposure: { label: 'Public exposure', short: 'public', color: 'var(--color-risk-public)', Icon: Globe, severity: 3 },
  identity_escalation: {
    label: 'Identity escalation',
    short: 'identity',
    color: 'var(--color-risk-escalation)',
    Icon: KeyRound,
    severity: 3,
  },
  audit_tampering: { label: 'Audit tampering', short: 'audit', color: 'var(--color-risk-tamper)', Icon: ShieldOff, severity: 3 },
}

// Same ranking as the backend's rules.SEVERITY; the top three classes rank equally.
export const RISK_ORDER = Object.keys(RISK) as Risk[]

export const riskOf = (r: string | undefined): RiskMeta => RISK[(r as Risk) ?? 'read'] ?? RISK.read

export function RiskBadge({ risk, count }: { risk: Risk; count?: number }) {
  const m = riskOf(risk)
  return (
    <span className="inline-flex items-center gap-1.5 text-sm font-medium whitespace-nowrap" style={{ color: m.color }}>
      <m.Icon size={15} aria-hidden />
      {m.label}
      {count !== undefined && <span className="num">{count.toLocaleString()}</span>}
    </span>
  )
}
