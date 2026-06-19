import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { taxApi } from "../../api/tax";
import type { Corporation, NilT2Report } from "./types";

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

function formatScheduleRow(key: string, value: number): JSX.Element {
  return (
    <tr key={key}>
      <td className="px-3 py-1.5 text-slate-700 capitalize">
        {key.replace(/_/g, " ")}
      </td>
      <td className="px-3 py-1.5 text-right font-mono text-slate-900">
        {value.toFixed(2)}
      </td>
    </tr>
  );
}

export function NilT2Page() {
  const [searchParams] = useSearchParams();
  const [corps, setCorps] = useState<Corporation[]>([]);
  const [selectedCorpId, setSelectedCorpId] = useState<string>(
    searchParams.get("corp") ?? "",
  );
  const [fiscalYearEnd, setFiscalYearEnd] = useState<string>("");
  const [hasIncome, setHasIncome] = useState(false);
  const [hasExpenses, setHasExpenses] = useState(false);
  const [report, setReport] = useState<NilT2Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const selectedCorp = useMemo(
    () => corps.find((c) => c.id === selectedCorpId),
    [corps, selectedCorpId],
  );

  const inputClass =
    "rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm shadow-sm transition focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/40";
  const primaryBtn =
    "inline-flex items-center justify-center rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand/40 disabled:cursor-not-allowed disabled:opacity-70";
  const secondaryBtn =
    "inline-flex items-center justify-center rounded-xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-300";

  useEffect(() => {
    void (async () => {
      const data = await safeExecute(() => taxApi.listCorporations(), setError);
      if (data) setCorps(data);
    })();
  }, []);

  useEffect(() => {
    if (selectedCorp && !fiscalYearEnd) {
      // Suggest most recent fiscal year end based on corp's fiscal_year_end_month
      const today = new Date();
      const month = selectedCorp.fiscal_year_end_month;
      const year =
        today.getMonth() + 1 >= month ? today.getFullYear() : today.getFullYear() - 1;
      const lastDay = new Date(year, month, 0).getDate();
      const iso = `${year}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
      setFiscalYearEnd(iso);
    }
  }, [selectedCorp, fiscalYearEnd]);

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!selectedCorpId) {
      setError("Select a corporation");
      return;
    }
    if (!fiscalYearEnd) {
      setError("Fiscal year end is required");
      return;
    }
    if (hasIncome || hasExpenses) {
      setError("Nil T2 requires no income and no expenses");
      return;
    }

    setSubmitting(true);
    const result = await safeExecute(
      () =>
        taxApi.generateNilT2(
          selectedCorpId,
          fiscalYearEnd,
          hasIncome,
          hasExpenses,
        ),
      setError,
    );
    setSubmitting(false);
    if (result) setReport(result);
  }

  function handlePrint() {
    window.print();
  }

  return (
    <div className="flex flex-col gap-6 h-full">
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-100 px-4 py-3 text-sm text-rose-700 shadow-sm">
          {error}
        </div>
      )}

      <section className="space-y-5 rounded-2xl bg-white p-6 shadow-card print:hidden">
        <h2 className="text-xl font-semibold text-slate-900">Generate Nil T2 Report</h2>
        <form onSubmit={handleGenerate} className="flex flex-col gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
              Corporation
              <select
                value={selectedCorpId}
                onChange={(e) => setSelectedCorpId(e.target.value)}
                className={inputClass}
              >
                <option value="">Select corporation</option>
                {corps.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
              Fiscal Year End
              <input
                type="date"
                value={fiscalYearEnd}
                onChange={(e) => setFiscalYearEnd(e.target.value)}
                className={inputClass}
                required
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-6">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={hasIncome}
                onChange={(e) => setHasIncome(e.target.checked)}
              />
              Had any income this fiscal year
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={hasExpenses}
                onChange={(e) => setHasExpenses(e.target.checked)}
              />
              Had any expenses this fiscal year
            </label>
          </div>
          {(hasIncome || hasExpenses) && (
            <p className="text-sm text-amber-700">
              A nil T2 is only valid with zero income and zero expenses. For other
              corporations, please work with an accountant.
            </p>
          )}
          <div>
            <button
              type="submit"
              className={primaryBtn}
              disabled={submitting || hasIncome || hasExpenses}
            >
              {submitting ? "Generating…" : "Generate Nil T2"}
            </button>
          </div>
        </form>
      </section>

      {report && (
        <section className="space-y-5 rounded-2xl bg-white p-6 shadow-card print:shadow-none">
          <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
            <h2 className="text-xl font-semibold text-slate-900">
              Nil T2 — Generated {new Date(report.generated_at).toLocaleString()}
            </h2>
            <button type="button" className={secondaryBtn} onClick={handlePrint}>
              Print / Save as PDF
            </button>
          </div>

          <div>
            <h3 className="mb-2 text-base font-semibold text-slate-800">Identification</h3>
            <dl className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
              {Object.entries(report.report.identification).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-3 border-b border-slate-100 py-1">
                  <dt className="capitalize text-slate-600">{k.replace(/_/g, " ")}</dt>
                  <dd className="font-mono text-slate-900">{String(v ?? "—")}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div>
            <h3 className="mb-2 text-base font-semibold text-slate-800">
              Schedule 100 — Balance Sheet Information
            </h3>
            <table className="min-w-full border-t border-slate-200 text-sm">
              <tbody>
                {Object.entries(report.report.schedule_100).map(([k, v]) =>
                  formatScheduleRow(k, v),
                )}
              </tbody>
            </table>
          </div>

          <div>
            <h3 className="mb-2 text-base font-semibold text-slate-800">
              Schedule 125 — Income Statement Information
            </h3>
            <table className="min-w-full border-t border-slate-200 text-sm">
              <tbody>
                {Object.entries(report.report.schedule_125).map(([k, v]) =>
                  formatScheduleRow(k, v),
                )}
              </tbody>
            </table>
          </div>

          <div>
            <h3 className="mb-2 text-base font-semibold text-slate-800">
              Schedule 1 — Net Income for Tax Purposes
            </h3>
            <table className="min-w-full border-t border-slate-200 text-sm">
              <tbody>
                {Object.entries(report.report.schedule_1).map(([k, v]) =>
                  formatScheduleRow(k, v),
                )}
              </tbody>
            </table>
          </div>

          <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
            {report.report.notes.map((n, i) => (
              <p key={i}>• {n}</p>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
