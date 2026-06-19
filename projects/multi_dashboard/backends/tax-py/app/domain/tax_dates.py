from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date

ANNUAL_RETURN = "annual_return"
T2 = "t2"
GST_HST_PREFIX = "gst_hst_q"

REMINDER_OFFSETS_DAYS = {
    ANNUAL_RETURN: [90, 60, 30, 7],
    T2: [90, 60, 30, 14],
    "gst_hst": [30, 14, 7, 1],
}


@dataclass(frozen=True)
class FilingDeadline:
    filing_type: str
    period_label: str
    due_date: date


def _last_day_of_month(year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    last_day = monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def annual_return_due(incorporation_date: date, today: date) -> date:
    """Annual return is due on the anniversary of incorporation date."""
    year = today.year
    month = incorporation_date.month
    day = min(incorporation_date.day, monthrange(year, month)[1])
    candidate = date(year, month, day)
    if candidate < today:
        next_year = year + 1
        day = min(incorporation_date.day, monthrange(next_year, month)[1])
        candidate = date(next_year, month, day)
    return candidate


def gst_hst_quarters(fiscal_year_end_month: int, today: date) -> list[FilingDeadline]:
    """Return the next 4 upcoming GST/HST quarterly filing deadlines."""
    first_q_start_month = (fiscal_year_end_month % 12) + 1

    deadlines: list[FilingDeadline] = []
    base_year = today.year - 2
    for offset in range(16):
        q_idx_in_year = (offset % 4) + 1
        q_start_total_months = (first_q_start_month - 1) + (offset * 3)
        q_end_total_months = q_start_total_months + 2

        q_start_year = base_year + q_start_total_months // 12
        q_start_month = (q_start_total_months % 12) + 1
        q_end_year = base_year + q_end_total_months // 12
        q_end_month = (q_end_total_months % 12) + 1

        q_end_date = _last_day_of_month(q_end_year, q_end_month)
        due_month = _add_months(q_end_date, 1)
        due = _last_day_of_month(due_month.year, due_month.month)

        if due < today:
            continue

        start_label = date(q_start_year, q_start_month, 1).strftime("%b")
        end_label = q_end_date.strftime("%b %Y")
        period_label = f"Q{q_idx_in_year} ({start_label}-{end_label})"
        deadlines.append(
            FilingDeadline(
                filing_type=f"{GST_HST_PREFIX}{q_idx_in_year}",
                period_label=period_label,
                due_date=due,
            )
        )
        if len(deadlines) == 4:
            break
    return deadlines


def t2_due(fiscal_year_end_month: int, today: date) -> FilingDeadline:
    """T2 is due 6 months after fiscal year end. Returns the next upcoming T2."""
    candidate_year = today.year - 1
    while True:
        fy_end = _last_day_of_month(candidate_year, fiscal_year_end_month)
        due = _add_months(fy_end, 6)
        if due >= today:
            label = f"FY{fy_end.year} T2 (year end {fy_end.strftime('%b %d, %Y')})"
            return FilingDeadline(filing_type=T2, period_label=label, due_date=due)
        candidate_year += 1


def reminder_offsets(filing_type: str) -> list[int]:
    if filing_type == ANNUAL_RETURN:
        return REMINDER_OFFSETS_DAYS[ANNUAL_RETURN]
    if filing_type == T2:
        return REMINDER_OFFSETS_DAYS[T2]
    if filing_type.startswith(GST_HST_PREFIX):
        return REMINDER_OFFSETS_DAYS["gst_hst"]
    return []


def compute_full_schedule(
    incorporation_date: date, fiscal_year_end_month: int, today: date
) -> list[FilingDeadline]:
    schedule: list[FilingDeadline] = []
    schedule.append(
        FilingDeadline(
            filing_type=ANNUAL_RETURN,
            period_label=f"Annual Return {annual_return_due(incorporation_date, today).year}",
            due_date=annual_return_due(incorporation_date, today),
        )
    )
    schedule.extend(gst_hst_quarters(fiscal_year_end_month, today))
    schedule.append(t2_due(fiscal_year_end_month, today))
    schedule.sort(key=lambda d: d.due_date)
    return schedule
