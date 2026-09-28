import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Bot, Database, Globe, Server, Terminal } from 'lucide-react'
import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { prefetchSession, useSessions } from '../lib/api'
import { link, sessionHref } from '../lib/nav'
import AgentReview from '../components/AgentReview'

const REPO = 'https://github.com/fullstackfusions/public_projects/tree/master/projects/chaperone'
const ARCHITECTURE = 'https://github.com/fullstackfusions/public_projects/blob/master/projects/chaperone/ARCHITECTURE.md'

const TOOLS: [string, string][] = [
  ['list_sessions', 'recent sessions in the account, newest first, each with its riskiest call.'],
  ['what_did_the_agent_do', 'one session: each MCP tool call with the AWS calls it made, and what it created and deleted.'],
  ['risky_calls', 'the calls above plain writes, grouped by risk class, with the rule that flagged each one.'],
  ['review_session', 'what the session left running and its monthly cost, plus IAM deny guardrails checked by Access Analyzer.'],
  ['least_privilege', 'the permissions the session actually used, as a policy, compared with IAM Access Analyzer\'s.'],
]

// The architecture diagram as text, stage by stage, for readers that can't see the image.
const FLOW: [string, string][] = [
  ['Capture', 'CloudTrail records every AWS call in all regions. EventBridge forwards each one to us-east-1 within seconds; a poller Lambda fetches MCP tool calls and sign-ins every minute.'],
  ['Process', 'An ingest Lambda files each call under who made it (agent or person), notes the channel (MCP, Terraform, CLI, SDK, console) and classes its risk with fixed rules.'],
  ['Store', 'One DynamoDB table, events kept per actor for 90 days. Sessions are built when read, and each MCP tool call is joined to its AWS calls by request ID.'],
  ['Answer', 'One API Lambda answers every question, with Cloud Control (what was left running), IAM Access Analyzer (least privilege) and Bedrock (a summary written once per session).'],
  ['Serve', 'The MCP server calls it signed and unmasked. This site calls it through CloudFront, masked and read-only. Scripts and CI can call it signed too.'],
]

const WAYS_IN = [
  {
    icon: Bot,
    name: 'MCP server',
    who: 'for the agent',
    how: 'Claude Code or any MCP-capable agent asks about its own session ("me") before it reports back.',
  },
  {
    icon: Globe,
    name: 'Web console',
    who: 'for people',
    how: 'This site: the flight path, every change riskiest first, and a plain-English summary per session.',
  },
  {
    icon: Terminal,
    name: 'HTTP API',
    who: 'for scripts and CI',
    how: 'The same JSON over a function URL with IAM auth: anything that can sign an AWS request can ask.',
  },
]

/* A guided path for judges: the idea, the proof, then one session to verify it on. */
export default function Judges() {
  const q = useSessions()
  const agents = (q.data ?? []).filter((s) => s.agent)
  const start = [...agents].sort((a, b) => b.tool_calls - a.tool_calls)[0]
  const client = useQueryClient()
  const startId = start?.session_id
  // Most judges open this session next: load it while they read.
  useEffect(() => {
    if (startId) prefetchSession(client, startId)
  }, [client, startId])
  const calls = agents.reduce((n, s) => n + s.api_calls, 0)
  const tools = agents.reduce((n, s) => n + s.tool_calls, 0)

  return (
    <article className="space-y-10 pb-4">
      <a {...link('/')} className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
        <ArrowLeft size={15} /> All sessions
      </a>

      <header className="space-y-4">
        <h1 className="text-3xl font-semibold tracking-tight text-text-strong">
          For judges: how Chaperone works, and how to check it
        </h1>
        <p className="text-lg text-muted">
          CloudTrail records an AI agent's AWS calls as the developer's own. Chaperone pulls them apart: the agent
          session, each MCP tool call, and every AWS call that tool made.
        </p>
        <figure className="space-y-2">
          <a href="/architecture.png" title="Open full size" className="block">
            <img
              src="/architecture.png"
              alt="Architecture: CloudTrail and EventBridge in every region feed an ingest Lambda and a poller; events are stored in DynamoDB; an API Lambda answers the MCP server (signed, unmasked) and the website through CloudFront (masked, cached), with Bedrock, Cloud Control and IAM Access Analyzer behind it."
              className="w-full rounded-xl border border-surface-2"
              width={1842}
              height={1010}
            />
          </a>
          <figcaption className="text-xs text-subtle">Click the diagram for full size.</figcaption>
        </figure>
        <div className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-subtle">The diagram, in words</h2>
          <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {FLOW.map(([stage, what], i) => (
              <li key={stage} className="rounded-xl border border-line/70 bg-surface-1 p-4">
                <span className="num text-xs text-subtle">{i + 1}</span>
                <h3 className="font-semibold text-text-strong">{stage}</h3>
                <p className="mt-1 text-sm leading-relaxed text-muted">{what}</p>
              </li>
            ))}
          </ol>
        </div>
      </header>

      <Divider />

      <section className="space-y-5">
        <div className="space-y-1">
          <SectionTitle>One API, three ways in</SectionTitle>
          <p className="text-muted">MCP is one door. The same answers reach people and pipelines too.</p>
        </div>
        <figure className="space-y-2">
          <a href="/one-api-three-ways-in.png" title="Open full size" className="block">
            <img
              src="/one-api-three-ways-in.png"
              alt="One API, three ways in: the MCP server (for the agent, SigV4, unmasked), the web console (for people, through CloudFront, masked and read-only) and scripts or CI (SigV4, same JSON) all call one Chaperone API Lambda. It reads sessions from DynamoDB and calls Cloud Control (what was left running), IAM Access Analyzer (least privilege) and Bedrock (a summary once per session). DynamoDB is filled from CloudTrail in all regions, through EventBridge within seconds and a poller every minute, into an ingest Lambda that records who acted, the channel and the risk."
              className="w-full rounded-xl border border-surface-2"
              width={2468}
              height={988}
              loading="lazy"
            />
          </a>
          <figcaption className="text-xs text-subtle">Click the diagram for full size.</figcaption>
        </figure>
        <div className="space-y-3">
          <div className="grid gap-3 md:grid-cols-3">
            {WAYS_IN.map(({ icon: Icon, name, who, how }) => (
              <div key={name} className="space-y-2 rounded-xl border border-line/70 bg-surface-1 p-4">
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-2 text-primary">
                    <Icon size={17} />
                  </span>
                  <span className="min-w-0">
                    <span className="block font-semibold text-text-strong">{name}</span>
                    <span className="block text-xs text-subtle">{who}</span>
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-muted">{how}</p>
              </div>
            ))}
          </div>
          <div className="grid justify-items-center md:grid-cols-3" aria-hidden>
            {WAYS_IN.map(({ name }) => (
              <ArrowDown key={name} size={20} className="hidden text-line md:block" />
            ))}
            <ArrowDown size={20} className="text-line md:hidden" />
          </div>
          <div className="rounded-xl border border-primary/60 bg-surface-2 p-4 text-center">
            <div className="flex items-center justify-center gap-2 font-semibold text-text-strong">
              <Server size={17} className="text-primary" /> Chaperone API
            </div>
            <p className="mt-1 text-sm text-muted">
              sessions · what happened · risky calls · review · least privilege · explanations
            </p>
          </div>
          <div className="flex justify-center" aria-hidden>
            <ArrowUp size={20} className="text-line" />
          </div>
          <div className="rounded-xl border border-line/70 bg-surface-1 p-4 text-center">
            <div className="flex items-center justify-center gap-2 font-semibold text-text-strong">
              <Database size={17} className="text-primary" /> Every AWS call in the account
            </div>
            <p className="mt-1 text-sm text-muted">
              CloudTrail in every region, attributed to agent or person, classed by fixed rules
            </p>
          </div>
        </div>
        <ul className="grid gap-3 md:grid-cols-3">
          <KeyPoint title="Same answer everywhere">
            The MCP tool, this site and the API read one query layer. Only the masking differs.
          </KeyPoint>
          <KeyPoint title="Not tied to one agent or channel">
            It records MCP, Terraform, the CLI, SDKs and the console, and flags an agent working on a person's identity.
          </KeyPoint>
          <KeyPoint title="Safe by construction">
            Signed callers get the full record. This public site gets a masked, read-only view that can't start work.
          </KeyPoint>
        </ul>
      </section>

      <Divider />

      <section className="space-y-3">
        <SectionTitle>The agent checks its own work</SectionTitle>
        <p className="text-muted">
          Chaperone is also an MCP server in the agent. Here Claude Code asks it "was anything I did risky?"
        </p>
        <AgentReview />
      </section>

      <Divider />

      <section className="space-y-4">
        <SectionTitle>Verify it on a session</SectionTitle>
        <p className="text-muted">Look at three things in this session:</p>
        <ol className="grid gap-4 md:grid-cols-3">
          <Step n={1} title="The summary">
            The top panel says in plain English what the agent did.
          </Step>
          <Step n={2} title="The flight path">
            One lane per channel. Click a key icon to see why an IAM change was flagged.
          </Step>
          <Step n={3} title="The access it needed">
            It was allowed <code className="font-mono">"Action": "*"</code>. See what it actually used.
          </Step>
        </ol>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
          <a
            {...link(start ? sessionHref(start.session_id) : '/')}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 font-semibold text-bg hover:bg-text-strong"
          >
            Open the start-here session <ArrowRight size={18} />
          </a>
          {q.data && (
            <span className="num text-sm text-subtle">
              {agents.length} agent sessions · {calls.toLocaleString()} AWS calls · {tools} MCP tool calls
            </span>
          )}
        </div>
      </section>

      <Divider />

      <section className="space-y-4">
        <SectionTitle>Other details</SectionTitle>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="A real agent with its own identity">
            <p>
              Claude Code runs on a Linux VPS and reaches AWS through the AWS MCP Server, signed in as its own IAM
              Identity Center user, <code className="font-mono">chaperone-agent</code>. CloudTrail records each tool call
              as an event from <code className="font-mono">aws-mcp.amazonaws.com</code> whose user agent names Claude
              Code. Those events are the top lane of every agent session here; click one to see the AWS calls under it.
            </p>
          </Card>
          <Card title="Five MCP tools, for any MCP-capable agent">
            <ul className="space-y-2">
              {TOOLS.map(([name, what]) => (
                <li key={name}>
                  <code className="font-mono text-text-strong">{name}</code>
                  <span className="text-muted"> — {what}</span>
                </li>
              ))}
            </ul>
            <p>
              Asked for session <code className="font-mono">"me"</code>, the agent reviews its own latest session
              before it reports back. The server runs with the developer's own AWS credentials, so it can't be tried
              from this page; the repository has the setup steps.
            </p>
          </Card>
          <Card title="Rules decide risk, not a model">
            <ul className="list-disc space-y-1.5 pl-5">
              <li>Serverless: CloudTrail, EventBridge, Lambda, DynamoDB, CloudFront, S3, Bedrock, IAM Access Analyzer, Cloud Control.</li>
              <li>All infrastructure in Terraform. Risk classes come from fixed rules, tested on real recorded events.</li>
              <li>The plain-English explanations are written once per session by a Bedrock model and stored.</li>
            </ul>
            <p>
              <a className="text-primary underline underline-offset-2" href={ARCHITECTURE}>
                ARCHITECTURE.md
              </a>{' '}
              has the decisions behind it.
            </p>
          </Card>
          <Card title="This site is masked and read-only">
            <ul className="list-disc space-y-1.5 pl-5">
              <li>
                CloudFront marks every request from this site as public. In that view the API masks account IDs, role
                suffixes, identity IDs and IP addresses, and refuses anything that starts work. Try{' '}
                <code className="font-mono break-all">/api/replay?id=me</code>: it answers 403. Nothing a visitor does
                calls a model.
              </li>
              <li>Chaperone records and explains; it never blocks, deletes or reverts. A recorder that acts would be one more agent to watch.</li>
              <li>
                Events appear a few minutes after the call, as fast as CloudTrail delivers them. AWS doesn't record the
                scripts an agent sends through MCP, so Chaperone shows what was called, not the code.
              </li>
            </ul>
          </Card>
          <Card title="$0.07 for the whole account in September">
            <p>By Cost Explorer, up to the 27th. Explanations cost a few cents per session, once.</p>
          </Card>
        </div>
      </section>

      <Divider />

      <p className="text-sm">
        <a className="text-primary underline underline-offset-2" href={REPO}>
          Source code (PolyForm Noncommercial)
        </a>
      </p>
    </article>
  )
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="space-y-2 rounded-xl border border-line/70 bg-surface-1 p-5">
      <span className="num flex h-7 w-7 items-center justify-center rounded-full bg-surface-3 text-sm font-semibold text-text-strong">
        {n}
      </span>
      <h3 className="font-semibold text-text-strong">{title}</h3>
      <p className="text-sm leading-relaxed text-muted">{children}</p>
    </li>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="flex items-center gap-3 text-2xl font-semibold tracking-tight text-text-strong">
      <span className="h-7 w-1.5 shrink-0 rounded-full bg-risk-write" aria-hidden />
      {children}
    </h2>
  )
}

function Divider() {
  return <hr className="border-line/40" />
}

function KeyPoint({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <li className="rounded-r-xl border-l-4 border-risk-write bg-risk-write/10 px-4 py-3">
      <h3 className="font-semibold text-risk-write">{title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-text">{children}</p>
    </li>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3 rounded-xl border border-line/70 bg-surface-1 p-5 leading-relaxed text-text sm:p-6">
      <h3 className="text-lg font-semibold text-text-strong">{title}</h3>
      {children}
    </section>
  )
}
