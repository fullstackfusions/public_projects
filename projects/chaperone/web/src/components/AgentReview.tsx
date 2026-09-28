import { link, sessionHref } from '../lib/nav'

// The loop clip's run (loop-clip-script.md): the agent created and deleted a queue, then asked Chaperone.
const DEMO_SESSION = 'role/AWSReservedSSO_ChaperoneAgent_0000000000000000/chaperone-agent@2026-09-27T21:43:30Z'

// What risky_calls("me") returned in that run, trimmed to the finding (masked, as on this site).
const ANSWER = `risky_calls("me") →
{
  "risky": {
    "destructive": {
      "calls": [{
        "time": "2026-09-27T22:30:13Z",
        "action": "sqs:DeleteQueue",
        "target": "https://sqs.us-east-1.amazonaws.com/111122223333/chaperone-demo-queue",
        "via": "mcp",
        "tool": "aws___run_script",
        "reasons": ["sqs:DeleteQueue removes or stops a resource"],
        "on_resource_created_this_session": true
      }]
    }
  },
  "summary": { "destructive": 1 }
}`

/* MCP seen from the agent: the one moment this site can't show live (D-029). A muted loop of Claude Code
   asking Chaperone about its own work, beside the answer it got. */
export default function AgentReview({ compact = false }: { compact?: boolean }) {
  return (
    <div className={compact ? 'space-y-3' : 'grid grid-cols-1 gap-4 lg:grid-cols-[3fr_2fr]'}>
      <figure className="min-w-0 space-y-2">
        <video
          className="w-full rounded-xl border border-surface-2 bg-surface-1"
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          poster="/media/agent-review.jpg"
          width={1600}
          height={900}
          aria-label="Screen recording: Claude Code creates and deletes an SQS queue through the AWS MCP Server, then asks Chaperone what it did; Chaperone reports one destructive call, on a queue the same session created."
        >
          <source src="/media/agent-review.webm" type="video/webm" />
          <source src="/media/agent-review.mp4" type="video/mp4" />
        </video>
        <figcaption className="text-xs text-subtle">
          A real run, sped up, identifiers masked. The same run on this site:{' '}
          <a {...link(sessionHref(DEMO_SESSION))} className="text-primary underline underline-offset-2">
            the session with the demo queue
          </a>
          .
        </figcaption>
      </figure>
      {!compact && (
        <div className="min-w-0 space-y-2 text-sm text-muted">
          <p>
            Claude Code created and deleted a queue through the AWS MCP Server, then asked Chaperone "was anything I did
            risky?" The answer comes from CloudTrail, which the agent didn't write and can't edit: one destructive call,
            on a queue the same session created.
          </p>
          <pre className="overflow-x-auto rounded-xl border border-surface-2 bg-surface-1 p-3 font-mono text-xs leading-relaxed text-muted">
            {ANSWER}
          </pre>
        </div>
      )}
    </div>
  )
}
