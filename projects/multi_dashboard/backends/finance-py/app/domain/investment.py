from __future__ import annotations

from typing import Dict, List

from ..schemas.finance import InvestmentParams


def compute_investment(params: InvestmentParams) -> dict:
    months = int(params.years) * 12
    r_month = (1.0 + params.cagr_percent / 100.0) ** (1.0 / 12.0) - 1.0

    lump_map: Dict[int, float] = {}
    if params.lumpsums:
        for lump in params.lumpsums:
            lump_map[lump.month] = lump_map.get(lump.month, 0.0) + float(lump.amount)

    principal = float(params.current_balance) + float(lump_map.get(0, 0.0))
    balance = float(params.current_balance) + float(lump_map.get(0, 0.0))

    monthly_rows: List[dict] = [
        {"month": 0, "principal": principal, "growth": balance - principal, "total": balance}
    ]

    for m in range(1, months + 1):
        monthly_lump = float(lump_map.get(m, 0.0))
        if params.contribution_timing == "start":
            balance += params.monthly_payment + monthly_lump
            principal += params.monthly_payment + monthly_lump
            balance *= 1.0 + r_month
        else:
            balance *= 1.0 + r_month
            balance += params.monthly_payment + monthly_lump
            principal += params.monthly_payment + monthly_lump

        monthly_rows.append(
            {"month": m, "principal": principal, "growth": balance - principal, "total": balance}
        )

    yearly_rows: List[dict] = []
    for y in range(0, params.years + 1):
        idx = y * 12
        if idx <= months:
            row = monthly_rows[idx]
            yearly_rows.append(
                {"year": y, "principal": row["principal"], "growth": row["growth"], "total": row["total"]}
            )

    return {"monthly": monthly_rows, "yearly": yearly_rows, "final": monthly_rows[-1]}
