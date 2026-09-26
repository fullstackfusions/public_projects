import { link } from '../lib/nav'

export default function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-[1440px] flex-col px-4 sm:px-8">
      <header className="flex items-center justify-between gap-4 py-5">
        <a {...link('/')} className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" width={32} height={32} />
          <span>
            <span className="block text-lg font-semibold tracking-tight text-text-strong">Chaperone</span>
            <span className="block text-xs text-subtle">flight recorder for AI agents on AWS</span>
          </span>
        </a>
        <span className="hidden text-right text-xs text-subtle sm:block">
          Real sessions from one AWS account, recorded by CloudTrail.
          <br />
          Identifiers masked.
        </span>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="mt-16 flex flex-wrap justify-between gap-2 border-t border-surface-2 py-6 text-xs text-subtle">
        <span>Built for the AWS Zero to Shipped hackathon, 2026 · FullStackFusions | Mihir Patel</span>
        <a className="text-primary hover:underline" href="https://github.com/fullstackfusions/public_projects/tree/master/projects/chaperone">
          Source (PolyForm Noncommercial)
        </a>
      </footer>
    </div>
  )
}
