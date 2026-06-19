from __future__ import annotations

from typing import List

from ..schemas.finance import SalaryProjectionParams


def compute_salary_projection(params: SalaryProjectionParams) -> dict:
    monthly_salary = float(params.monthly_salary)
    monthly_expense = float(params.monthly_expense)
    r_increment = params.yearly_increment_percent / 100.0
    r_inflation = params.yearly_inflation_percent / 100.0
    r_return_monthly = (1.0 + params.annual_return_percent / 100.0) ** (1.0 / 12.0) - 1.0

    yearly_rows: List[dict] = []
    cumulative_savings = 0.0
    investment_balance = 0.0

    for y in range(params.years):
        year_num = y + 1
        if y > 0:
            monthly_salary *= 1.0 + r_increment
            monthly_expense *= 1.0 + r_inflation

        annual_salary = monthly_salary * 12.0
        annual_expense = monthly_expense * 12.0
        annual_saving = annual_salary - annual_expense

        monthly_saving = monthly_salary - monthly_expense
        for _ in range(12):
            investment_balance *= 1.0 + r_return_monthly
            investment_balance += max(monthly_saving, 0.0)

        cumulative_savings += max(annual_saving, 0.0)

        yearly_rows.append(
            {
                "year": year_num,
                "annualSalary": round(annual_salary, 2),
                "annualExpense": round(annual_expense, 2),
                "annualSaving": round(annual_saving, 2),
                "cumulativeSavings": round(cumulative_savings, 2),
                "investmentValue": round(investment_balance, 2),
            }
        )

    return {"yearly": yearly_rows}
