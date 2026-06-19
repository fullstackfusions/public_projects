from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class TaxFilingOut(BaseModel):
    id: str
    corp_id: str
    filing_type: str
    period_label: str
    due_date: str
    status: str
    scheduler_event_id: int | None = None


class FilingStatusUpdate(BaseModel):
    status: str


class FilingScheduleItem(BaseModel):
    filing_type: str
    period_label: str
    due_date: date


class UpcomingFiling(TaxFilingOut):
    corporation_name: str
    days_remaining: int
