// Write readable HTML into the built pages (see src/prerender.tsx):
//   dist/index.html          the overview
//   dist/judges/index.html   the judges' tour (CloudFront serves it for /judges)
// Sessions come from the live site's public API, so they are already masked.
//   node prerender.mjs [site URL]
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'

const site = (process.argv[2] ?? 'https://chaperone.fullstackfusions.com').replace(/\/$/, '')
// A fresh query string skips CloudFront's cache, so the build sees answers written since it was filled.
const fresh = `fresh=${Date.now()}`
const r = await fetch(`${site}/api/sessions?${fresh}`)
if (!r.ok) throw new Error(`${site}/api/sessions: ${r.status}`)
const sessions = await r.json()
const { render } = await import('./dist-ssr/prerender.js')
const { home, judges } = render(sessions)

const shell = readFileSync('dist/index.html', 'utf8')
if (!shell.includes('<div id="root"></div>')) throw new Error('dist/index.html has no empty #root')
// Data for main.tsx, so the first client render matches this markup instead of "Loading…".
// "<" escaped: session text must not be able to close the script element.
const seed = `<script type="application/json" id="seed">${JSON.stringify(sessions).replace(/</g, '\\u003c')}</script>`
const fill = (html) => shell.replace('<div id="root"></div>', `<div id="root">${html}</div>${seed}`)

writeFileSync('dist/index.html', fill(home))
mkdirSync('dist/judges', { recursive: true })
writeFileSync(
  'dist/judges/index.html',
  fill(judges).replace(/<title>[^<]*<\/title>/, '<title>For judges · Chaperone</title>'),
)
console.log(`prerendered ${sessions.length} sessions: dist/index.html, dist/judges/index.html`)

// dist/sessions.md: every session and its stored explanation as plain text, for AI readers.
// Session pages are client-rendered, so without this a crawler sees the list but no session.
// Four at a time: the API function has a concurrency limit of 10 and throttles past it.
const explanations = new Array(sessions.length)
let next = 0
const worker = async () => {
  while (next < sessions.length) {
    const i = next++
    const url = `${site}/api/explain?id=${encodeURIComponent(sessions[i].session_id)}&${fresh}`
    const res = await fetch(url).catch(() => undefined)
    if (!res?.ok) throw new Error(`${url}: ${res?.status ?? 'network error'}`)
    explanations[i] = await res.json()
  }
}
await Promise.all([worker(), worker(), worker(), worker()])
const minutes = (s) => Math.max(0, Math.round((Date.parse(s.end) - Date.parse(s.start)) / 60000))
const who = (s) => s.actor.split('/').pop()
const md = [
  '# Chaperone: every recorded session',
  '',
  `Real sessions from one AWS account, recorded by CloudTrail, newest first. Identifiers are masked (the account shows as 111122223333). Generated ${new Date().toISOString().slice(0, 16)}Z from ${site}/api/sessions; each summary was written once per session by Amazon Bedrock from the recorded calls. Risk classes come from fixed rules, not a model.`,
  '',
  `${sessions.length} sessions, ${sessions.filter((s) => s.agent).length} by an AI agent (Claude Code through the AWS MCP Server), ${sessions.reduce((n, s) => n + s.api_calls, 0).toLocaleString('en-US')} AWS calls.`,
  '',
]
sessions.forEach((s, i) => {
  const e = explanations[i]
  const counts = Object.entries(s.risk_counts).map(([k, v]) => `${k} ${v}`).join(', ')
  md.push(
    `## ${who(s)} (${s.agent ? 'AI agent' : 'person'}), ${s.start}, ${minutes(s)} min`,
    '',
    `- Page: ${site}/session/${encodeURIComponent(s.session_id)}`,
    `- ${s.api_calls} AWS calls, ${s.tool_calls} MCP tool calls; by risk: ${counts || 'none'}`,
    `- Riskiest: ${s.risk}${s.reasons?.length ? ` (${s.reasons.join('; ')})` : ''}`,
  )
  if (e.headline) {
    md.push('', `**${e.headline}**`, '', e.summary ?? '')
    if (e.moments?.length) md.push('', 'Key moments:', ...e.moments.map((m) => `- ${m.time.slice(11, 19)} ${m.text}`))
    if (e.risk) md.push('', `Risk: ${e.risk}`)
    if (e.access) md.push('', `Access: ${e.access}`)
  }
  md.push('')
})
writeFileSync('dist/sessions.md', md.join('\n'))
console.log(`wrote dist/sessions.md (${explanations.filter((e) => e.headline).length} of ${sessions.length} explained)`)
