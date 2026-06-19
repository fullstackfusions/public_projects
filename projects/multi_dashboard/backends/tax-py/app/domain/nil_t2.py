from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any, Protocol


class _CorpLike(Protocol):
    """Duck-type protocol for corporation objects accepted by build_nil_t2_report."""

    name: str
    business_number: str | None
    corp_number: str | None
    province: str | None


def _fiscal_year_start(fiscal_year_end: date) -> date:
    """Fiscal year start is the day after the previous year's fiscal year end."""
    prev_year = fiscal_year_end.year - 1
    last_day = monthrange(prev_year, fiscal_year_end.month)[1]
    prev_end = date(prev_year, fiscal_year_end.month, min(fiscal_year_end.day, last_day))
    return prev_end + timedelta(days=1)


def build_nil_t2_report(corp: _CorpLike, fiscal_year_end: date) -> dict[str, Any]:
    """Build a structured nil T2 report dictionary.

    All monetary schedule values are zero, suitable for a corporation with no
    income and no expenses. Hand this summary to a licensed tax preparer or
    transcribe values into CRA-certified T2 software.
    """
    fy_start = _fiscal_year_start(fiscal_year_end)

    identification = {
        "corporation_name": corp.name,
        "business_number": corp.business_number,
        "corp_number": corp.corp_number,
        "province_of_jurisdiction": corp.province,
        "fiscal_year_start": fy_start.isoformat(),
        "fiscal_year_end": fiscal_year_end.isoformat(),
        "is_nil_return": True,
    }

    schedule_100_balance_sheet = {
        "total_assets": 0,
        "total_liabilities": 0,
        "total_shareholders_equity": 0,
        "cash": 0,
        "accounts_receivable": 0,
        "inventory": 0,
        "accounts_payable": 0,
        "retained_earnings": 0,
    }

    schedule_125_income_statement = {
        "total_revenue": 0,
        "cost_of_goods_sold": 0,
        "gross_profit": 0,
        "total_operating_expenses": 0,
        "net_income_before_tax": 0,
    }

    schedule_1_net_income_reconciliation = {
        "net_income_per_financial_statements": 0,
        "additions": 0,
        "deductions": 0,
        "net_income_for_tax_purposes": 0,
    }

    return {
        "identification": identification,
        "schedule_100": schedule_100_balance_sheet,
        "schedule_125": schedule_125_income_statement,
        "schedule_1": schedule_1_net_income_reconciliation,
        "notes": [
            "Nil return: corporation reports no income and no expenses for the fiscal period.",
            "Hand this summary to a licensed tax preparer or transcribe values into CRA-certified T2 software.",
        ],
    }
