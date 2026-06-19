from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from .filings import TaxFilingOut


class CorporationCreate(BaseModel):
    name: str
    corp_number: str | None = None
    business_number: str | None = None
    gst_hst_number: str | None = None
    province: str | None = None
    fiscal_year_end_month: int = Field(ge=1, le=12)
    incorporation_date: date
    contact_email: str | None = None
    contact_phone: str | None = None  # E.164 e.g. +14155552671


class CorporationUpdate(BaseModel):
    name: str | None = None
    corp_number: str | None = None
    business_number: str | None = None
    gst_hst_number: str | None = None
    province: str | None = None
    fiscal_year_end_month: int | None = Field(default=None, ge=1, le=12)
    incorporation_date: date | None = None
    contact_email: str | None = None
    contact_phone: str | None = None  # E.164 e.g. +14155552671


class CorporationOut(BaseModel):
    id: str
    name: str
    corp_number: str | None = None
    business_number: str | None = None
    gst_hst_number: str | None = None
    province: str | None = None
    fiscal_year_end_month: int
    incorporation_date: str
    contact_email: str | None = None
    contact_phone: str | None = None
    created_at: str


class CorporationWithFilings(CorporationOut):
    filings: list[TaxFilingOut] = []
