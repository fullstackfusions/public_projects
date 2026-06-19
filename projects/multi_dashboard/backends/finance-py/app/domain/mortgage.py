from __future__ import annotations

from typing import List

from ..schemas.finance import MortgageParams


def compute_default_payment(principal: float, annual_rate: float, years: int) -> float:
    n = years * 12
    if n == 0:
        return 0.0
    monthly_rate = annual_rate / 100.0 / 12.0
    if monthly_rate == 0:
        return principal / n
    factor = (1 + monthly_rate) ** n
    return principal * (monthly_rate * factor) / (factor - 1)


def amortization_schedule(params: MortgageParams) -> List[dict]:
    monthly_rate = params.annual_rate / 100.0 / 12.0
    balance = float(params.principal)
    month = 0
    cumulative_interest = 0.0
    cumulative_principal = 0.0
    rows: List[dict] = []
    max_months = max(params.years * 12 * 2, 12)

    monthly_payment = (
        float(params.monthly_payment)
        if params.monthly_payment is not None
        else compute_default_payment(params.principal, params.annual_rate, params.years)
    )

    while balance > 0 and month < max_months:
        month += 1
        interest = balance * monthly_rate if monthly_rate else 0.0
        planned_extra_month = float(params.extra_monthly)
        planned_extra_annual = (
            float(params.extra_annual)
            if ((month - 1) % 12) + 1 == int(params.annual_lump_month)
            else 0.0
        )
        planned_total = monthly_payment + planned_extra_month + planned_extra_annual
        total_payment = min(planned_total, balance + interest)

        if total_payment + 1e-8 < interest:
            raise ValueError(
                "Monthly payment (including extras) is below accrued interest; balance will grow."
            )

        principal_payment = total_payment - interest
        balance = max(balance - principal_payment, 0.0)
        cumulative_interest += interest
        cumulative_principal += principal_payment

        actual_extra = max(0.0, total_payment - monthly_payment)
        actual_extra_month = min(planned_extra_month, actual_extra)
        actual_extra_annual = max(0.0, actual_extra - actual_extra_month)

        rows.append(
            {
                "month": month,
                "year": (month - 1) // 12 + 1,
                "scheduledPayment": min(monthly_payment, total_payment),
                "extraMonthlyPaid": actual_extra_month,
                "extraAnnualPaid": actual_extra_annual,
                "totalPayment": total_payment,
                "interest": interest,
                "principalPaid": principal_payment,
                "balance": balance,
                "cumulativeInterest": cumulative_interest,
                "cumulativePrincipal": cumulative_principal,
            }
        )

        if balance <= 1e-6:
            break

    if balance > 0:
        raise ValueError(
            "Loan did not amortize within the evaluated window. Increase payments or term."
        )

    return rows


def compute_mortgage(params: MortgageParams) -> dict:
    rows = amortization_schedule(params)
    payoff_months = int(rows[-1]["month"]) if rows else 0
    summary = {
        "scenario": "Scenario",
        "months": payoff_months,
        "years": payoff_months / 12.0,
        "totalInterest": sum(r["interest"] for r in rows),
        "totalPaid": sum(r["totalPayment"] for r in rows),
    }
    return {"schedule": rows, "summary": summary}
