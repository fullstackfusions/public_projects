export const t = (iso: string) => new Date(iso).getTime()

export function duration(start: string, end: string): string {
  const s = Math.max(0, Math.round((t(end) - t(start)) / 1000))
  if (s < 60) return `${s}s`
  const m = Math.round(s / 60)
  return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${m % 60} min`
}

export function when(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  }) + ' UTC'
}

export const clock = (iso: string) => iso.slice(11, 19)

/** role/AWSReservedSSO_ChaperoneAgent_…/chaperone-agent -> chaperone-agent (ChaperoneAgent) */
export function actorName(actor: string): { name: string; detail: string } {
  if (actor.startsWith('user/')) return { name: actor.slice(5), detail: 'IAM user' }
  const parts = actor.split('/')
  const role = parts[1] ?? actor
  const sso = role.match(/^AWSReservedSSO_(.+)_[0-9a-f]{16}$/)
  return { name: parts[2] ?? role, detail: sso ? `Identity Center · ${sso[1]}` : `role ${role}` }
}

export const VIA_LABEL: Record<string, string> = {
  mcp: 'AWS MCP server',
  terraform: 'Terraform',
  cli: 'AWS CLI',
  sdk: 'SDK',
  console: 'Console',
}

export const viaLabel = (via = '') =>
  VIA_LABEL[via] ?? (via.startsWith('service:') ? `${via.slice(8)} (AWS, for the agent)` : via || 'other')
