import { ArrowLeft } from 'lucide-react'
import { useSessions } from '../lib/api'
import { link, sessionHref } from '../lib/nav'
import AgentReview from '../components/AgentReview'

const REPO = 'https://github.com/fullstackfusions/public_projects/tree/master/projects/chaperone'

/* A guided path for judges: what to click, what is real, how to check it. */
export default function Judges() {
  const q = useSessions()
  const agents = (q.data ?? []).filter((s) => s.agent)
  const start = [...agents].sort((a, b) => b.tool_calls - a.tool_calls)[0]
  const calls = agents.reduce((n, s) => n + s.api_calls, 0)
  const tools = agents.reduce((n, s) => n + s.tool_calls, 0)

  return (
    <article className="space-y-8 pb-4">
      <a {...link('/')} className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
        <ArrowLeft size={15} /> All sessions
      </a>

      <header className="max-w-4xl">
        <h1 className="text-3xl font-semibold tracking-tight text-text-strong">
          For judges: Chaperone in three minutes
        </h1>
        <p className="mt-3 text-lg text-muted">
          When an AI coding agent works in your AWS account, Chaperone shows what it did, which calls were risky, and
          the access it actually needed. The sessions on this site are the record of Claude Code building Chaperone
          itself, and of the person working beside it.
        </p>
        {q.data && (
          <p className="num mt-3 text-sm text-subtle">
            Right now: {agents.length} agent sessions, {calls.toLocaleString()} AWS calls, {tools} MCP tool calls.
          </p>
        )}
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="The tour">
          <ol className="list-decimal space-y-3 pl-5">
            <li>
              Open the{' '}
              {start ? (
                <a {...link(sessionHref(start.session_id))} className="text-primary underline underline-offset-2">
                  session marked "Start here"
                </a>
              ) : (
                'session marked "Start here"'
              )}
              . The top panel says in plain English what the agent did.
            </li>
            <li>
              <b className="text-text-strong">Flight path.</b> One lane per channel: the AWS MCP Server's tool calls,
              Terraform, the CLI, SDKs, and AWS services acting for the agent. People in the console at the same time
              have their own lane. Drag to zoom; press ← → to step through every call that wasn't a read.
            </li>
            <li>
              <b className="text-text-strong">Click a key icon</b> (an IAM change). The drawer shows the rule that
              flagged it, the channel, the MCP tool call it came from, and the raw CloudTrail event, masked.
            </li>
            <li>
              <b className="text-text-strong">The access it actually needed.</b> The agent was allowed{' '}
              <code className="font-mono">"Action": "*"</code>; Chaperone lists the actions it used and compares them
              with the policy IAM Access Analyzer generated for the same window.
            </li>
            <li>
              <b className="text-text-strong">Every change, riskiest first.</b> The whole session as a review list.
            </li>
          </ol>
        </Section>

        <Section title="What is new here">
          <p>
            CloudTrail records an AI agent's calls as the developer's own. It also records, separately, each tool call
            the agent makes through the AWS MCP Server. Chaperone joins the two on request IDs, which gives three levels
            no AWS console shows together: the agent session, each MCP tool call, and every AWS API call that tool call
            made.
          </p>
        </Section>

        <Section title="Proof of the coding agent connection">
          <p>
            Claude Code runs on a Linux VPS and reaches AWS through the AWS MCP Server, signed in as its own IAM
            Identity Center user, <code className="font-mono">chaperone-agent</code>. CloudTrail records each tool call
            as an event from <code className="font-mono">aws-mcp.amazonaws.com</code> whose user agent names Claude
            Code. Those events are the top lane of every agent session here; click one to see the AWS calls under it.
          </p>
        </Section>

        <Section title="The agent reviews itself" wide>
          <p>
            The main way to use Chaperone isn't this site: it's an MCP server in the developer's own agent. It has five
            tools: <code className="font-mono">list_sessions</code>,{' '}
            <code className="font-mono">what_did_the_agent_do</code>, <code className="font-mono">risky_calls</code>,{' '}
            <code className="font-mono">review_session</code> and <code className="font-mono">least_privilege</code>.
            Asked for session <code className="font-mono">"me"</code>, the agent reviews its own latest session before
            it reports back. The MCP server runs with the developer's own AWS credentials, so it can't be tried from
            this page; the repository has the setup steps. It works with any MCP-capable agent; we have run it with
            Claude Code.
          </p>
          <AgentReview />
        </Section>

        <Section title="How it's built" wide>
          <a href="/architecture.png" title="Open full size">
            <img
              src="/architecture.png"
              alt="Architecture: CloudTrail and EventBridge in every region feed an ingest Lambda and a poller; events are stored in DynamoDB; an API Lambda answers the MCP server (signed, unmasked) and the website through CloudFront (masked, cached), with Bedrock, Cloud Control and IAM Access Analyzer behind it."
              className="w-full rounded-xl border border-surface-2"
              width={1842}
              height={1010}
              loading="lazy"
            />
          </a>
          <p className="text-xs text-subtle">Click the diagram for full size.</p>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              Serverless: CloudTrail, EventBridge, Lambda, DynamoDB, CloudFront, S3, Bedrock, IAM Access Analyzer, Cloud Control.
            </li>
            <li>
              All infrastructure in Terraform. Risk classes come from fixed rules with tests on real recorded events,
              never from a model.
            </li>
            <li>
              The plain-English explanations are written once per session by a Bedrock model and stored. Nothing a
              visitor does calls a model.
            </li>
          </ul>
        </Section>

        <Section title="What this site can and can't do">
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              The site reads the same API the MCP server uses, through CloudFront, which marks every request as public.
              In that view the API masks account IDs, role suffixes, identity IDs and IP addresses, and refuses anything
              that starts work. Try <code className="font-mono break-all">/api/replay?id=me</code>: it answers 403.
            </li>
            <li>
              Chaperone records and explains; it never blocks, deletes or reverts. A recorder that acts would be one
              more agent to watch.
            </li>
            <li>
              Events appear a few minutes after the call, as fast as CloudTrail delivers them. AWS doesn't record the
              scripts an agent sends through MCP, so Chaperone shows what was called, not the code.
            </li>
          </ul>
        </Section>

        <Section title="Cost">
          <p>
            The whole account cost $0.07 in September up to the 27th, by Cost Explorer. Explanations cost a few cents
            per session, once.
          </p>
        </Section>
      </div>

      <p className="text-sm">
        <a className="text-primary underline underline-offset-2" href={REPO}>
          Source code (PolyForm Noncommercial)
        </a>
      </p>
    </article>
  )
}

function Section({ title, wide, children }: { title: string; wide?: boolean; children: React.ReactNode }) {
  return (
    <section
      className={`space-y-3 rounded-xl bg-surface-1 p-5 leading-relaxed text-text sm:p-6 ${wide ? 'lg:col-span-2' : ''}`}
    >
      <h2 className="text-lg font-semibold text-text-strong">{title}</h2>
      {children}
    </section>
  )
}
