export const CA_JURISDICTIONS = [
  { code: "FED", label: "Federal (Canada)" },
  { code: "AB", label: "Alberta" },
  { code: "BC", label: "British Columbia" },
  { code: "MB", label: "Manitoba" },
  { code: "NB", label: "New Brunswick" },
  { code: "NL", label: "Newfoundland and Labrador" },
  { code: "NS", label: "Nova Scotia" },
  { code: "NT", label: "Northwest Territories" },
  { code: "NU", label: "Nunavut" },
  { code: "ON", label: "Ontario" },
  { code: "PE", label: "Prince Edward Island" },
  { code: "QC", label: "Quebec" },
  { code: "SK", label: "Saskatchewan" },
  { code: "YT", label: "Yukon" },
] as const;

export const LEGAL_SUFFIX_PATTERN =
  /\b(inc\.?|incorporated|corp\.?|corporation|ltd\.?|limited|ltée|ltee|société par actions|s\.a\.|sarf)\b/i;

export interface FieldResult {
  value: string;
  error: string | null;
  warning?: string | null;
}

function collapseWhitespace(s: string): string {
  return s.replace(/\s+/g, " ").trim();
}

export function normalizeCorporationName(raw: string): FieldResult {
  const value = collapseWhitespace(raw);
  if (!value) return { value: "", error: "Name is required" };
  const warning = LEGAL_SUFFIX_PATTERN.test(value)
    ? null
    : 'Name typically ends with a legal suffix (e.g., "Inc.", "Corp.", "Ltd.")';
  return { value, error: null, warning };
}

export function normalizeCorpNumber(raw: string): FieldResult {
  // Strip everything except digits and hyphens, collapse spaces inside.
  const cleaned = raw.trim().replace(/\s+/g, "");
  if (!cleaned) return { value: "", error: null };

  // Allow 6-10 digit corp numbers with optional "-N" check digit suffix.
  const match = cleaned.match(/^([0-9]{6,10})(?:-([0-9]))?$/);
  if (!match) {
    return {
      value: cleaned,
      error: "Corporation number should be 6-10 digits, optionally with a check digit (e.g., 1422645-3)",
    };
  }
  const value = match[2] ? `${match[1]}-${match[2]}` : match[1];
  return { value, error: null };
}

export function normalizeBusinessNumber(raw: string): FieldResult {
  // Strip all non-digits.
  const digits = raw.replace(/\D/g, "");
  if (!digits) return { value: "", error: null };
  if (digits.length !== 9) {
    return {
      value: digits,
      error: `Business Number must be exactly 9 digits (got ${digits.length})`,
    };
  }
  // Format as "123456789" (CRA does not group BN root visually).
  return { value: digits, error: null };
}

export function normalizeGstHstNumber(raw: string): FieldResult {
  // Expected: 9 digits + "RT" + 4 digits (e.g., 123456789RT0001).
  const cleaned = raw.toUpperCase().replace(/[\s-]/g, "");
  if (!cleaned) return { value: "", error: null };

  // Allow user to type just 9 digits — auto-append RT0001.
  const digitsOnly = cleaned.replace(/\D/g, "");
  if (/^[0-9]{9}$/.test(cleaned)) {
    return { value: `${cleaned}RT0001`, error: null };
  }

  const match = cleaned.match(/^([0-9]{9})RT([0-9]{4})$/);
  if (!match) {
    if (digitsOnly.length < 9) {
      return {
        value: cleaned,
        error: "GST/HST number must start with a 9-digit Business Number",
      };
    }
    return {
      value: cleaned,
      error: 'GST/HST number must look like "123456789RT0001"',
    };
  }
  return { value: cleaned, error: null };
}

export function normalizeEmail(raw: string): FieldResult {
  const value = raw.trim().toLowerCase();
  if (!value) return { value: "", error: null };
  const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  return { value, error: ok ? null : "Invalid email address" };
}

export function normalizePhone(raw: string): FieldResult {
  // Strip all whitespace and dashes to get a compact form for validation.
  const cleaned = raw.trim().replace(/[\s\-().]/g, "");
  if (!cleaned) return { value: "", error: null };

  // Must be E.164: optional leading +, then 7–15 digits.
  const e164 = /^\+?[1-9]\d{6,14}$/.test(cleaned);
  if (!e164) {
    return {
      value: cleaned,
      error: "Enter a valid phone number with country code (e.g. +14155552671)",
    };
  }
  // Ensure the + prefix is present.
  const value = cleaned.startsWith("+") ? cleaned : `+${cleaned}`;
  return { value, error: null };
}
