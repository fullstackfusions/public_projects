from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel


class NilT2GenerateRequest(BaseModel):
    fiscal_year_end: date
    has_income: bool = False
    has_expenses: bool = False


class NilT2Out(BaseModel):
    id: str
    corp_id: str
    fiscal_year_end: str
    generated_at: str
    has_income: bool
    has_expenses: bool
    report: dict[str, Any]
