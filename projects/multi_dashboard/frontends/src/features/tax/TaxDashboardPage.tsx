import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { taxApi } from "../../api/tax";
import type { Corporation, UpcomingFiling } from "./types";

async function safeExecute<T>(
  action: () => Promise<T>,
  onError: (message: string) => void,
): Promise<T | undefined> {
  try {
    return await action();
  } catch (error) {
    onError(error instanceof Error ? error.message : "Something went wrong");
    return undefined;
  }
}

function urgencyClass(daysRemaining: number): string {
  if (daysRemaining < 14) return "bg-rose-100 text-rose-800";
  if (daysRemaining < 30) return "bg-amber-100 text-amber-800";
  return "bg-emerald-100 text-emerald-800";
}

function prettyFilingType(t: string): string {
  if (t === "annual_return") return "Annual Return";
  if (t === "t2") return "T2 Corporate Income Tax";
  if (t.startsWith("gst_hst_q")) return `GST/HST ${t.slice(-2).toUpperCase()}`;
  return t;
}

export function TaxDashboardPage() {
  const [filings, setFilings] = useState<UpcomingFiling[]>([]);
  const [corps, setCorps] = useState<Corporation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyCorpId, setBusyCorpId] = useState<string | null>(null);

  const corpsById = useMemo(() => {
    const map = new Map<string, Corporation>();
    corps.forEach((c) => map.set(c.id, c));
    return map;
  }, [corps]);

  const primaryBtn =
    "inline-flex items-center justify-center rounded-xl bg-brand px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-70";
  const secondaryBtn =
    "inline-flex items-center justify-center rounded-xl bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-200";

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    const [f, c] = await Promise.all([
      safeExecute(() => taxApi.listUpcomingFilings(), setError),
      safeExecute(() => taxApi.listCorporations(), setError),
    ]);
    if (f) setFilings(f);
    if (c) setCorps(c);
  }

  async function handleSetupReminders(corpId: string) {
    setBusyCorpId(corpId);
    await safeExecute(() => taxApi.setupReminders(corpId), setError);
    setBusyCorpId(null);
    await loadAll();
  }

  async function handleMarkFiled(filing: UpcomingFiling) {
    if (!window.confirm(`Mark "${filing.period_label}" as filed?`)) return;
    await safeExecute(
      () => taxApi.updateFilingStatus(filing.corp_id, filing.id, "filed"),
      setError,
    );
    await loadAll();
  }

  return (
    <div className="flex flex-col gap-6 h-full">
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-100 px-4 py-3 text-sm text-rose-700 shadow-sm">
          {error}
        </div>
      )}

      <section className="space-y-4 rounded-2xl bg-white p-6 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold text-slate-900">Corporations</h2>
          <Link
            to="/tax/corporations"
            className="text-sm font-semibold text-brand hover:underline"
          >
            Manage corporations →
          </Link>
        </div>
        {corps.length === 0 ? (
          <p className="text-sm text-slate-500">
            No corporations yet. Add one to generate filing reminders.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {corps.map((c) => (
              <li
                key={c.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-3"
              >
                <span className="text-sm font-semibold text-slate-800">{c.name}</span>
                <button
                  type="button"
                  className={primaryBtn}
                  disabled={busyCorpId === c.id}
                  onClick={() => handleSetupReminders(c.id)}
                >
                  {busyCorpId === c.id ? "Setting up…" : "Setup Reminders"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-4 rounded-2xl bg-white p-6 shadow-card">
        <h2 className="text-xl font-semibold text-slate-900">Upcoming Filings</h2>
        {filings.length === 0 ? (
          <p className="text-sm text-slate-500">
            No upcoming filings. Add a corporation and click "Setup Reminders".
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">Corporation</th>
                  <th className="px-3 py-2">Filing</th>
                  <th className="px-3 py-2">Period</th>
                  <th className="px-3 py-2">Due Date</th>
                  <th className="px-3 py-2">Days Left</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filings.map((f) => (
                  <tr key={f.id}>
                    <td className="px-3 py-2 font-semibold text-slate-800">
                      {f.corporation_name}
                    </td>
                    <td className="px-3 py-2 text-slate-700">
                      {prettyFilingType(f.filing_type)}
                    </td>
                    <td className="px-3 py-2 text-slate-600">{f.period_label}</td>
                    <td className="px-3 py-2 text-slate-700">{f.due_date}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${urgencyClass(f.days_remaining)}`}
                      >
                        {f.days_remaining}d
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-600 capitalize">{f.status}</td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className={secondaryBtn}
                          onClick={() => handleMarkFiled(f)}
                        >
                          Mark Filed
                        </button>
                        {f.filing_type === "t2" && (
                          <Link
                            to={`/tax/nil-t2?corp=${f.corp_id}`}
                            className={secondaryBtn}
                          >
                            Prepare Nil T2
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
