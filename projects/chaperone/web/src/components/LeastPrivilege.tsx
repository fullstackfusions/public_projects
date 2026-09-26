import { Check, Copy } from 'lucide-react'
import { useState } from 'react'
import { useLeastPrivilege } from '../lib/api'

/* "Granted: AdministratorAccess. Used: N actions across M services." (screen 3), then the
   policy, and IAM Access Analyzer's policy beside it with what each one missed (D-027). */
export default function LeastPrivilege({ sessionId, granted }: { sessionId: string; granted: string }) {
  const q = useLeastPrivilege(sessionId)
  const [copied, setCopied] = useState(false)
  if (q.isLoading) return <p className="text-subtle">Working out the permissions this session used…</p>
  if (q.error || !q.data) return <p className="text-risk-destructive">{q.error?.message ?? 'No answer'}</p>

  const { preview, access_analyzer: aa, comparison: cmp } = q.data
  const services = Object.keys(preview.by_service).length
  const policy = JSON.stringify(preview.policy, null, 2)

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <div className="space-y-5">
        <p className="text-lg leading-snug">
          Granted <span className="font-semibold text-text-strong">{granted}</span>. Used{' '}
          <span className="num font-semibold text-text-strong">{preview.actions.length}</span> actions across{' '}
          <span className="num font-semibold text-text-strong">{services}</span> services.
        </p>
        <div className="grid grid-cols-2 gap-3" aria-hidden>
          <div className="rounded-xl bg-surface-1 p-4">
            <div className="text-xs text-subtle">Allowed</div>
            <div className="mt-1 font-mono text-2xl text-risk-escalation">"Action": "*"</div>
          </div>
          <div className="rounded-xl bg-surface-1 p-4">
            <div className="text-xs text-subtle">Needed</div>
            <div className="num mt-1 font-mono text-2xl text-ok">{preview.actions.length} actions</div>
          </div>
        </div>
        {preview.passed_roles.length > 0 && (
          <p className="text-sm text-muted">
            Also needs <span className="font-mono text-text">iam:PassRole</span> on {preview.passed_roles.length} role
            {preview.passed_roles.length > 1 ? 's' : ''}. CloudTrail doesn't record PassRole; Chaperone reads the role from the
            request.
          </p>
        )}
        {preview.by_aws_services.length > 0 && (
          <p className="text-sm text-muted">
            <span className="num">{preview.by_aws_services.length}</span> more calls were made by AWS services on the actor's
            behalf; they're listed apart, not granted.
          </p>
        )}

        <div className="rounded-xl border border-surface-3 p-4">
          <h3 className="font-semibold text-text">IAM Access Analyzer, side by side</h3>
          {aa.status === 'SUCCEEDED' && cmp ? (
            <dl className="mt-3 grid grid-cols-[1fr_auto] gap-y-1.5 text-sm">
              <dt className="text-muted">Both found</dt>
              <dd className="num text-text-strong">{cmp.shared}</dd>
              <dt className="text-muted">Only Chaperone saw (AWS's policy would deny)</dt>
              <dd className="num text-risk-escalation">{cmp.only_chaperone.length}</dd>
              <dt className="text-muted">Only Access Analyzer listed (no call recorded)</dt>
              <dd className="num text-text-strong">{cmp.only_access_analyzer.length}</dd>
              <dt className="text-muted">Recovered from requests</dt>
              <dd className="num text-ok">{cmp.missed_by_both_recovered.length}</dd>
              {cmp.only_chaperone.length > 0 && (
                <dd className="col-span-2 mt-2 font-mono text-xs text-muted">{cmp.only_chaperone.join(' · ')}</dd>
              )}
            </dl>
          ) : (
            <p className="mt-2 text-sm text-muted">
              {aa.status === 'IN_PROGRESS'
                ? 'Access Analyzer is generating its policy for this session (about 3 minutes).'
                : "Access Analyzer hasn't been run for this session. It's started from the MCP server, not from this public site."}
            </p>
          )}
        </div>
      </div>

      <div className="min-w-0">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-semibold text-text">Policy from what was actually used</h3>
          <button
            onClick={() => navigator.clipboard.writeText(policy).then(() => setCopied(true))}
            className="inline-flex items-center gap-1.5 rounded-md border border-surface-3 px-2.5 py-1 text-sm text-primary hover:bg-surface-2"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <pre className="max-h-96 overflow-auto rounded-xl bg-surface-1 p-4 font-mono text-xs leading-relaxed text-text">{policy}</pre>
      </div>
    </div>
  )
}
