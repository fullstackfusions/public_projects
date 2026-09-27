// Write readable HTML into the built pages (see src/prerender.tsx):
//   dist/index.html          the overview
//   dist/judges/index.html   the judges' tour (CloudFront serves it for /judges)
// Sessions come from the live site's public API, so they are already masked.
//   node prerender.mjs [site URL]
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'

const site = (process.argv[2] ?? 'https://chaperone.fullstackfusions.com').replace(/\/$/, '')
const r = await fetch(`${site}/api/sessions`)
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
