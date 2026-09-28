import { Sparkles } from 'lucide-react'
import { useExplanation } from '../lib/api'
import { clock, when } from '../lib/format'

const MODEL_LABEL: Record<string, string> = {
  'us.anthropic.claude-sonnet-4-6': 'Claude Sonnet 4.6',
  'openai.gpt-oss-120b-1:0': 'gpt-oss-120b',
}

/* The plain-English account of a session, written once by a Bedrock model from the recorded
   facts and stored (D-029). Nothing here calls a model: visitors read the stored text. */
export default function Explanation({ sessionId }: { sessionId: string }) {
  const q = useExplanation(sessionId)
  const e = q.data
  if (!e || e.status === 'NOT_GENERATED') return null

  return (
    <section aria-labelledby="ex" className="rounded-xl bg-surface-1 p-5 sm:p-6">
      <h2 id="ex" className="flex items-center gap-2 text-sm font-medium text-subtle">
        <Sparkles size={15} className="text-primary" /> What happened, in plain English
      </h2>
      <p className="mt-2 text-xl font-semibold leading-snug text-text-strong">{e.headline}</p>
      <p className="mt-3 max-w-4xl leading-relaxed text-text">{e.summary}</p>

      <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        {e.moments && e.moments.length > 0 && (
          <ol className="space-y-2">
            {e.moments.map((m, i) => (
              <li key={i} className="grid grid-cols-[4.5rem_1fr] gap-3 text-sm">
                <span className="num pt-0.5 text-subtle">{clock(m.time)}</span>
                <span className="text-text">{m.text}</span>
              </li>
            ))}
          </ol>
        )}
        <div className="space-y-4 text-sm">
          <div>
            <h3 className="font-medium text-text-strong">Risk</h3>
            <p className="mt-1 text-muted">{e.risk}</p>
          </div>
          <div>
            <h3 className="font-medium text-text-strong">Access</h3>
            <p className="mt-1 text-muted">{e.access}</p>
          </div>
        </div>
      </div>

      <p className="mt-5 border-t border-surface-2 pt-3 text-xs text-subtle">
        Written by {MODEL_LABEL[e.model ?? ''] ?? e.model} on Amazon Bedrock from Chaperone's record of this session
        {e.generated_at && `, ${when(e.generated_at)}`}. Risk classes come from fixed rules, not from the model.
        {e.status === 'STALE' && ' The session has more activity since this was written.'}
      </p>
    </section>
  )
}
