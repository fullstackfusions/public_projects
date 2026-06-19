from __future__ import annotations

from typing import Annotated, Literal, Optional, Sequence

from pydantic import BaseModel, Field


class Lump(BaseModel):
    month: Annotated[int, Field(ge=0)]
    amount: Annotated[float, Field(ge=0)]


class InvestmentParams(BaseModel):
    current_balance: Annotated[float, Field(ge=0)] = 0.0
    monthly_payment: Annotated[float, Field(ge=0)] = 0.0
    cagr_percent: Annotated[float, Field(ge=0)] = 0.0
    years: Annotated[int, Field(ge=0)] = 0
    contribution_timing: Literal["start", "end"] = "end"
    lumpsums: Optional[Sequence[Lump]] = None


class MortgageParams(BaseModel):
    principal: Annotated[float, Field(gt=0)]
    annual_rate: Annotated[float, Field(ge=0)]
    years: Annotated[int, Field(gt=0)]
    monthly_payment: Optional[Annotated[float, Field(ge=0)]] = None
    extra_monthly: Annotated[float, Field(ge=0)] = 0.0
    extra_annual: Annotated[float, Field(ge=0)] = 0.0
    annual_lump_month: Annotated[int, Field(ge=1, le=12)] = 12


class SalaryProjectionParams(BaseModel):
    monthly_salary: Annotated[float, Field(gt=0)]
    yearly_increment_percent: Annotated[float, Field(ge=0)] = 3.0
    monthly_expense: Annotated[float, Field(ge=0)]
    yearly_inflation_percent: Annotated[float, Field(ge=0)] = 3.0
    years: Annotated[int, Field(ge=1, le=100)]
    annual_return_percent: Annotated[float, Field(ge=0)] = 18.0


Kind = Literal["investment", "mortgage", "salary_projection"]


class ComputeRequest(BaseModel):
    kind: Kind
    params: dict


class ComputeResponse(BaseModel):
    ok: bool
    result: dict
