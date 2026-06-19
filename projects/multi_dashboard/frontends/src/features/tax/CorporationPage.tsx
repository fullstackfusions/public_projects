import { FormEvent, useEffect, useRef, useState } from "react";

import { taxApi } from "../../api/tax";
import type {
  Corporation,
  CorporationPayload,
  FilingScheduleItem,
} from "./types";
import {
  CA_JURISDICTIONS,
  normalizeBusinessNumber,
  normalizeCorpNumber,
  normalizeCorporationName,
  normalizeEmail,
  normalizeGstHstNumber,
  normalizePhone,
} from "./validators";

type FieldKey =
  | "name"
  | "corp_number"
  | "business_number"
  | "gst_hst_number"
  | "contact_email"
  | "contact_phone";

type FieldMessages = Partial<
  Record<FieldKey, { error: string | null; warning?: string | null }>
>;

interface CorporationFormState {
  id: string | null;
  name: string;
  corp_number: string;
  business_number: string;
  gst_hst_number: string;
  province: string;
  fiscal_year_end_month: string;
  incorporation_date: string;
  contact_email: string;
  contact_phone: string;
}

function emptyForm(): CorporationFormState {
  return {
    id: null,
    name: "",
    corp_number: "",
    business_number: "",
    gst_hst_number: "",
    province: "",
    fiscal_year_end_month: "12",
    incorporation_date: "",
    contact_email: "",
    contact_phone: "",
  };
}

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

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

// ---------------------------------------------------------------------------
// Registry / CRA reference links
// ---------------------------------------------------------------------------

const REGISTRY_LINKS = [
  {
    label: "General Business Registry",
    url: "https://ised-isde.canada.ca/cbr-rec/",
    title: "Canada Business Registry — search any registered business",
  },
  {
    label: "Federal Registry",
    url: "https://ised-isde.canada.ca/cc/lgcy/fdrlCrpSrch.html",
    title: "Corporations Canada — search federal corporations",
  },
  {
    label: "Ontario Registry",
    url: "https://www.ontario.ca/page/ontario-business-registry",
    title: "Ontario Business Registry — search Ontario businesses",
  },
  {
    label: "CRA My Business Account",
    url: "https://www.canada.ca/en/revenue-agency/services/e-services/cra-login-services.html",
    title: "CRA login — view/update your BN, GST/HST, and corporate account",
  },
] as const;

function ExtLink({
  href,
  title,
  children,
}: {
  href: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      title={title}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-0.5 text-brand hover:underline text-xs font-semibold"
    >
      {children}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 12 12"
        className="h-3 w-3 flex-shrink-0"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M4.5 2H2a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V7.5M7 1h4m0 0v4m0-4L5 7"
        />
      </svg>
    </a>
  );
}

export function CorporationPage() {
  const [corps, setCorps] = useState<Corporation[]>([]);
  const [form, setForm] = useState<CorporationFormState>(emptyForm());
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [schedule, setSchedule] = useState<FilingScheduleItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [fieldMessages, setFieldMessages] = useState<FieldMessages>({});
  const [toast, setToast] = useState<{ kind: "success" | "warn"; message: string } | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function showToast(kind: "success" | "warn", message: string) {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ kind, message });
    toastTimer.current = setTimeout(() => setToast(null), 5000);
  }

  const NORMALIZERS = {
    name: normalizeCorporationName,
    corp_number: normalizeCorpNumber,
    business_number: normalizeBusinessNumber,
    gst_hst_number: normalizeGstHstNumber,
    contact_email: normalizeEmail,
    contact_phone: normalizePhone,
  } as const;

  function handleFieldBlur(key: FieldKey) {
    const result = NORMALIZERS[key](form[key]);
    setForm((p) => ({ ...p, [key]: result.value }));
    setFieldMessages((m) => ({
      ...m,
      [key]: { error: result.error, warning: result.warning ?? null },
    }));
  }

  function validateAll(): boolean {
    const messages: FieldMessages = {};
    const next = { ...form };
    let hasError = false;
    (Object.keys(NORMALIZERS) as FieldKey[]).forEach((key) => {
      const result = NORMALIZERS[key](form[key]);
      next[key] = result.value;
      messages[key] = { error: result.error, warning: result.warning ?? null };
      if (result.error) hasError = true;
    });
    setForm(next);
    setFieldMessages(messages);
    return !hasError;
  }

  function fieldNote(key: FieldKey) {
    const msg = fieldMessages[key];
    if (!msg) return null;
    if (msg.error)
      return <span className="text-xs text-rose-600">{msg.error}</span>;
    if (msg.warning)
      return <span className="text-xs text-amber-600">{msg.warning}</span>;
    return null;
  }

  const inputClass =
    "rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm shadow-sm transition focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/40";
  const primaryBtn =
    "inline-flex items-center justify-center rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand/40 disabled:cursor-not-allowed disabled:opacity-70";
  const secondaryBtn =
    "inline-flex items-center justify-center rounded-xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-300";
  const dangerBtn =
    "inline-flex items-center justify-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-500 focus:outline-none focus:ring-2 focus:ring-rose-300";

  useEffect(() => {
    void loadCorps();
  }, []);

  async function loadCorps() {
    const data = await safeExecute(() => taxApi.listCorporations(), setError);
    if (data) {
      setCorps(data);
      setError(null);
    }
  }

  async function loadSchedule(corpId: string) {
    const data = await safeExecute(
      () => taxApi.getFilingSchedule(corpId),
      setError,
    );
    if (data) {
      setSchedule(data);
      setSelectedId(corpId);
    }
  }

  function handleEdit(c: Corporation) {
    setForm({
      id: c.id,
      name: c.name,
      corp_number: c.corp_number ?? "",
      business_number: c.business_number ?? "",
      gst_hst_number: c.gst_hst_number ?? "",
      province: c.province ?? "",
      fiscal_year_end_month: String(c.fiscal_year_end_month),
      incorporation_date: c.incorporation_date,
      contact_email: c.contact_email ?? "",
      contact_phone: c.contact_phone ?? "",
    });
    void loadSchedule(c.id);
  }

  async function handleDelete(c: Corporation) {
    if (!window.confirm(`Delete corporation "${c.name}"?`)) return;
    await safeExecute(() => taxApi.deleteCorporation(c.id), setError);
    if (selectedId === c.id) {
      setSelectedId(null);
      setSchedule([]);
    }
    if (form.id === c.id) setForm(emptyForm());
    await loadCorps();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!validateAll()) {
      setError("Please fix the highlighted fields");
      return;
    }
    if (!form.incorporation_date) {
      setError("Incorporation date is required");
      return;
    }

    const payload: CorporationPayload = {
      name: form.name.trim(),
      corp_number: form.corp_number.trim() || null,
      business_number: form.business_number.trim() || null,
      gst_hst_number: form.gst_hst_number.trim() || null,
      province: form.province.trim() || null,
      fiscal_year_end_month: Number(form.fiscal_year_end_month),
      incorporation_date: form.incorporation_date,
      contact_email: form.contact_email.trim() || null,
      contact_phone: form.contact_phone.trim() || null,
    };

    setSubmitting(true);
    const isNew = !form.id;
    let savedId: number | undefined;
    if (form.id) {
      const updated = await safeExecute(
        () => taxApi.updateCorporation(form.id!, payload),
        setError,
      );
      savedId = updated?.id;
    } else {
      const created = await safeExecute(
        () => taxApi.createCorporation(payload),
        setError,
      );
      savedId = created?.id;
    }

    if (savedId && isNew) {
      // Auto-setup reminders only on first create — updates never duplicate
      try {
        await taxApi.setupReminders(savedId);
        showToast(
          "success",
          "Corporation added and filing reminders scheduled in the Scheduler.",
        );
      } catch {
        showToast(
          "warn",
          "Corporation saved, but reminders could not be created right now (is the scheduler running?). You can retry from the Tax Dashboard.",
        );
      }
    } else if (savedId && !isNew) {
      showToast("success", "Corporation updated.");
    }

    setSubmitting(false);
    await loadCorps();
    if (savedId) {
      await loadSchedule(savedId);
    }
    setForm(emptyForm());
  }

  return (
    <div className="flex flex-col gap-6 h-full">
      {/* Toast notification */}
      {toast && (
        <div
          className={`rounded-xl border px-4 py-3 text-sm shadow-sm flex items-start justify-between gap-3 ${
            toast.kind === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-amber-200 bg-amber-50 text-amber-800"
          }`}
        >
          <span>
            {toast.kind === "success" ? "✓ " : "⚠ "}
            {toast.message}
          </span>
          <button
            type="button"
            onClick={() => setToast(null)}
            className="shrink-0 text-current opacity-50 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-100 px-4 py-3 text-sm text-rose-700 shadow-sm">
          {error}
        </div>
      )}

      <div className="grid gap-7 xl:grid-cols-[minmax(360px,420px)_1fr] flex-1">
        <section className="space-y-5 rounded-2xl bg-white p-6 shadow-card">
          <h2 className="text-xl font-semibold text-slate-900">
            {form.id ? "Edit Corporation" : "Add Corporation"}
          </h2>

          {/* Registry Lookup Banner */}
          <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 space-y-1.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">
              Look up your corporation details
            </p>
            <div className="flex flex-wrap gap-x-4 gap-y-1.5">
              {REGISTRY_LINKS.map((r) => (
                <ExtLink key={r.url} href={r.url} title={r.title}>
                  {r.label}
                </ExtLink>
              ))}
            </div>
            <p className="text-xs text-sky-600">
              You can update your business details directly in the federal and
              Ontario registries using your login credentials.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
              Name
              <input
                type="text"
                value={form.name}
                onChange={(e) =>
                  setForm((p) => ({ ...p, name: e.target.value }))
                }
                onBlur={() => handleFieldBlur("name")}
                className={inputClass}
                placeholder="e.g., 12345678 Canada Inc."
                required
              />
              {fieldNote("name")}
            </label>
            <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
              <span className="flex items-center justify-between">
                Corporation Number
                <span className="flex gap-3 font-normal">
                  <ExtLink
                    href="https://ised-isde.canada.ca/cc/lgcy/fdrlCrpSrch.html"
                    title="Look up federal corporation number"
                  >
                    Federal lookup
                  </ExtLink>
                  <ExtLink
                    href="https://www.ontario.ca/page/ontario-business-registry"
                    title="Look up Ontario corporation number"
                  >
                    Ontario lookup
                  </ExtLink>
                </span>
              </span>
              <input
                type="text"
                value={form.corp_number}
                onChange={(e) =>
                  setForm((p) => ({ ...p, corp_number: e.target.value }))
                }
                onBlur={() => handleFieldBlur("corp_number")}
                className={inputClass}
                placeholder="e.g., 1234567-8"
              />
              {fieldNote("corp_number")}
            </label>
            {/* BN + GST/HST with CRA link */}
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  CRA Numbers
                </span>
                <ExtLink
                  href="https://www.canada.ca/en/revenue-agency/services/e-services/cra-login-services.html"
                  title="Log in to CRA My Business Account to view your BN and GST/HST details"
                >
                  CRA My Business Account
                </ExtLink>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                  Business Number
                  <input
                    type="text"
                    value={form.business_number}
                    onChange={(e) =>
                      setForm((p) => ({
                        ...p,
                        business_number: e.target.value,
                      }))
                    }
                    onBlur={() => handleFieldBlur("business_number")}
                    className={inputClass}
                    placeholder="9 digits, e.g., 123456789"
                  />
                  {fieldNote("business_number")}
                </label>
                <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                  GST/HST Number
                  <input
                    type="text"
                    value={form.gst_hst_number}
                    onChange={(e) =>
                      setForm((p) => ({
                        ...p,
                        gst_hst_number: e.target.value,
                      }))
                    }
                    onBlur={() => handleFieldBlur("gst_hst_number")}
                    className={inputClass}
                    placeholder="e.g., 123456789RT0001"
                  />
                  {fieldNote("gst_hst_number")}
                  <span className="text-xs font-normal text-slate-400">
                    Type just your 9-digit BN — RT0001 is added automatically
                  </span>
                </label>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                Jurisdiction
                <select
                  value={form.province}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, province: e.target.value }))
                  }
                  className={inputClass}
                >
                  <option value="">Select jurisdiction</option>
                  {CA_JURISDICTIONS.map((j) => (
                    <option key={j.code} value={j.label}>
                      {j.label}
                    </option>
                  ))}
                </select>
                {form.province === "Ontario" && (
                  <ExtLink
                    href="https://www.ontario.ca/page/ontario-business-registry"
                    title="Ontario Business Registry — update your Ontario corporation details"
                  >
                    Ontario Business Registry
                  </ExtLink>
                )}
                {form.province === "Federal (Canada)" && (
                  <ExtLink
                    href="https://ised-isde.canada.ca/cc/lgcy/fdrlCrpSrch.html"
                    title="Corporations Canada — update your federal corporation details"
                  >
                    Corporations Canada Registry
                  </ExtLink>
                )}
              </label>
              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                Fiscal Year End Month
                <select
                  value={form.fiscal_year_end_month}
                  onChange={(e) =>
                    setForm((p) => ({
                      ...p,
                      fiscal_year_end_month: e.target.value,
                    }))
                  }
                  className={inputClass}
                >
                  {MONTHS.map((m, i) => (
                    <option key={m} value={i + 1}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                Incorporation Date
                <input
                  type="date"
                  value={form.incorporation_date}
                  onChange={(e) =>
                    setForm((p) => ({
                      ...p,
                      incorporation_date: e.target.value,
                    }))
                  }
                  className={inputClass}
                  required
                />
              </label>
              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                Reminder Email
                <input
                  type="email"
                  value={form.contact_email}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, contact_email: e.target.value }))
                  }
                  onBlur={() => handleFieldBlur("contact_email")}
                  className={inputClass}
                  placeholder="contact@example.com"
                />
                <span className="text-xs font-normal text-slate-400">
                  Used for tax deadline notifications — not stored with CRA
                </span>
                {fieldNote("contact_email")}
              </label>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                WhatsApp / SMS Phone
                <input
                  type="tel"
                  value={form.contact_phone}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, contact_phone: e.target.value }))
                  }
                  onBlur={() => handleFieldBlur("contact_phone")}
                  className={inputClass}
                  placeholder="+14155552671"
                />
                <span className="text-xs font-normal text-slate-400">
                  E.164 format with country code — used for WhatsApp reminders
                </span>
                {fieldNote("contact_phone")}
              </label>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                className={primaryBtn}
                disabled={submitting}
              >
                {form.id ? "Update" : "Add Corporation"}
              </button>
              {form.id && (
                <button
                  type="button"
                  className={secondaryBtn}
                  onClick={() => setForm(emptyForm())}
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </section>

        <section className="space-y-4 rounded-2xl bg-white p-6 shadow-card">
          <h2 className="text-xl font-semibold text-slate-900">Corporations</h2>
          {corps.length === 0 ? (
            <p className="text-sm text-slate-500">
              No corporations yet. Add one using the form on the left.
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {corps.map((c) => (
                <li
                  key={c.id}
                  className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1 text-sm text-slate-600">
                      <strong className="block text-base font-semibold text-slate-900">
                        {c.name}
                      </strong>
                      <div className="text-xs uppercase tracking-wide text-slate-500">
                        Incorporated: {c.incorporation_date} · FY end:{" "}
                        {MONTHS[c.fiscal_year_end_month - 1]}
                      </div>
                      {c.business_number && (
                        <div className="text-xs uppercase tracking-wide text-slate-500">
                          BN: {c.business_number}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-2">
                      <button
                        type="button"
                        className={secondaryBtn}
                        onClick={() => handleEdit(c)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className={dangerBtn}
                        onClick={() => handleDelete(c)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  {selectedId === c.id && schedule.length > 0 && (
                    <div className="mt-2 space-y-2">
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 px-1">
                        Upcoming Filings
                      </div>
                      <ul className="flex flex-col gap-1.5">
                        {[...schedule]
                          .sort(
                            (a, b) =>
                              new Date(a.due_date).getTime() -
                              new Date(b.due_date).getTime(),
                          )
                          .map((s) => {
                            const today = new Date();
                            today.setHours(0, 0, 0, 0);
                            const due = new Date(s.due_date);
                            const daysLeft = Math.ceil(
                              (due.getTime() - today.getTime()) /
                                (1000 * 60 * 60 * 24),
                            );
                            const overdue = daysLeft < 0;
                            const urgent = !overdue && daysLeft <= 30;
                            const soon = !overdue && !urgent && daysLeft <= 90;

                            const cardStyle = overdue
                              ? "border-rose-300 bg-rose-50"
                              : urgent
                                ? "border-orange-300 bg-orange-50"
                                : soon
                                  ? "border-amber-200 bg-amber-50"
                                  : "border-slate-200 bg-slate-50";

                            const badgeStyle = overdue
                              ? "bg-rose-100 text-rose-700"
                              : urgent
                                ? "bg-orange-100 text-orange-700"
                                : soon
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-slate-200 text-slate-500";

                            const dotStyle = overdue
                              ? "bg-rose-500"
                              : urgent
                                ? "bg-orange-500"
                                : soon
                                  ? "bg-amber-400"
                                  : "bg-slate-400";

                            const statusLabel = overdue
                              ? `${Math.abs(daysLeft)}d overdue`
                              : daysLeft === 0
                                ? "Due today"
                                : `${daysLeft}d left`;

                            const filingLabel = (() => {
                              if (s.filing_type === "annual_return")
                                return "Annual Return";
                              if (s.filing_type === "t2") return "T2";
                              if (s.filing_type.startsWith("gst_hst_q"))
                                return `GST/HST ${s.filing_type.slice(-2).toUpperCase()}`;
                              return s.filing_type;
                            })();

                            return (
                              <li
                                key={`${s.filing_type}-${s.due_date}`}
                                className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 ${cardStyle}`}
                              >
                                <span
                                  className={`h-2 w-2 flex-shrink-0 rounded-full ${dotStyle}`}
                                />
                                <span className="text-xs font-bold uppercase tracking-wide text-slate-600 w-20 flex-shrink-0">
                                  {filingLabel}
                                </span>
                                <span className="truncate text-xs text-slate-700 flex-1">
                                  {s.period_label}
                                </span>
                                <span
                                  className={`flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${badgeStyle}`}
                                >
                                  {statusLabel}
                                </span>
                              </li>
                            );
                          })}
                      </ul>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
